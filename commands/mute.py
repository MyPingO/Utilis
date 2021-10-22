from bot_cmd import Bot_Command, bot_commands, Bot_Command_Category
from utils import find, std_embed
from commands.unmute import unmute
from typing import Optional, Union
from utils.parse import re_duration, str_to_timedelta
from datetime import datetime, timezone

import discord
import asyncio
import re
import db

class Mute_Command(Bot_Command):
    name = "mute"

    default_time = "10m"

    short_help = "Mutes user for specified time"

    long_help = f"""Mutes the specified user for specified duration. Default duration is {default_time}.
    __Usage:__
    **mute** *member*|**all** [duration]
    Format duration as: [XXwXXdXXhXXm]
    """

    category = Bot_Command_Category.TOOLS

    #ensures log file exists and self.muted contains its contents
    def __init__(self):
        db.execute("""CREATE TABLE IF NOT EXISTS mute (
                Server bigint,
                Member bigint,
                UnmuteDT datetime,
                Moderator bigint,
                PRIMARY KEY (Server, Member)
            );"""
        )





    def can_run(self, location, member):
        # only admins are able to use this command
        return member is not None and member.guild_permissions.administrator





    async def run(self, msg: discord.Message, args: str):
        #gets current channel
        channel = msg.channel
        #checks that user entered arguments for the command
        if args:
            #get the mute info for a specified member
            if args.lower().startswith("info "):
                #get server mute info
                if args[5:].lower().strip() == "all":
                    await self.get_info(channel, channel.guild)
                    return
                #get the member whose info is being requested
                member = await find.member(channel, args[5:].strip(), msg.author)
                if member is None:
                    await std_embed.send_error(
                        channel,
                        title="Member Not Found",
                        description=f"**{args[5:]}** could not be found"
                    )
                else:
                    await self.get_info(channel, channel.guild, member)
                return

            #split the mute duration from the member
            parsed_args = self.split_args(args)

            #for server mutes
            if parsed_args[0].lower() == "all":
                await self.mute(channel, parsed_args[1], msg.author, None)

            #muting a single member
            else:
                #get the member to be muted
                member = await find.member(channel, m=parsed_args[0], responder=msg.author)
                if member is None:
                    print(f"{parsed_args[0]} could not be found")
                    await std_embed.send_error(
                        channel,
                        title="Member Not Found",
                        description=f"**{parsed_args[0]}** could not be found"
                    )
                    return

                #cannot mute moderators
                if member.guild_permissions.administrator:
                    embed = discord.Embed(
                        title="[ERROR] Cannot Mute Moderators",
                        color=discord.Color.red()
                    )
                    await channel.send(embed=embed)
                    return

                #mute the member
                await self.mute(channel, parsed_args[1], msg.author, member)
        #if user didnt enter any arguments
        else:
            print("A user (and optional duration) must be provided")
            await std_embed.send_error(
                channel,
                title="Input Error",
                description=f"**A user (and optional duration) must be provided.**"
            )





    #gets the mute information regarding the specified member
    async def get_info(self, channel: discord.TextChannel, guild: discord.Guild, member: Optional[discord.Member] = None):
        if member is None:
            params = (guild.id, guild.id)
        else:
            params = (guild.id, member.id)
        operation = "SELECT * FROM mute WHERE Server = %s AND Member = %s;"
        info = db.read_execute(operation, params)

        #send the mute info to the channel
        if info:
            info = info[0]
            dt = info[2]
            mod = guild.get_member(info[3])
            await std_embed.send_info(
                channel,
                title="MUTE INFO",
                description=f"""
                {'**ACTIVE SERVER MUTE**' if member is None else f'**Member:** {member.mention}'}
                **Until:** <t:{int(dt.timestamp())}>
                **By:** {mod.mention}""",
                author=member if not None else mod
            )
        else:
            #if member is muted via server-mute and not individually
            if member is not None:
                operation = "SELECT * FROM mute WHERE Server = %s AND Member = %s;"
                params = (guild.id, guild.id)
                if db.read_execute(operation, params):
                    await self.get_info(channel, guild)
                    return

            await std_embed.send_info(
                channel,
                title="MUTE INFO",
                description="A server mute is not active" if member is None else f"{member.mention} is not muted.",
                author=member
            )





    #gets the mute role for this server
    async def get_role(self, guild: discord.Guild):
        #disables chat permissions
        perms = discord.PermissionOverwrite(
            send_messages=False,
            send_tts_messages=False,
            add_reactions=False,
            connect=False,
            speak=False,
            stream=False
        )
        #creates 'mute' role if it doesn't already exist in this server
        if discord.utils.get(guild.roles, name="mute") is None:
            await guild.create_role(
                name="mute",
                hoist=True,
                permissions=discord.Permissions.none(),
                color=discord.Color.dark_theme()
            )
        self.role = discord.utils.get(guild.roles, name="mute")
        #add voice and text channel overwrites for this role
        for channel in guild.channels:
            await channel.set_permissions(self.role, overwrite=perms)





    #separate the mute duration from the user being muted
    def split_args(self, args: str) -> list:
        parsed_args = []

        #try to get the mute duration from the full string (case insensitive)
        duration = re_duration.search(args)

        #append the user being muted to the list
        parsed_args.append(args[:duration.start()].strip())

        #if there is no match, time wasn't specified or formatted incorrectly and the default time is used
        if not duration.group(0):
            return self.split_args(f"{parsed_args[0]} {self.default_time}")
        duration_td = str_to_timedelta(duration.group(0))

        parsed_args.append((datetime.now() + duration_td).replace(microsecond=0))
        return parsed_args





    #mutes the passed member given a datetime object
    async def mute(
            self,
            channel: discord.TextChannel,
            unmute_at: datetime,
            author: discord.Member,
            m: Optional[Union[discord.Member, str]] = None,
        ):
        """
        Parameters
        ------------

        channel: discord.TextChannel
        The channel to send the mute information to.

        unmute_at: datetime
        A datetime object specifying when the
        member or server should be unmuted.

        author: discord.Member
        The moderator responsible for the mute.

        m: Optional[Union[discord.Member, str]]
        The member to be muted.
        Mutes the entire server if None.
        """
        #get the mute role
        await self.get_role(channel.guild)

        #server-wide mute
        if m is None:
            print(f"Muted server [#{channel.guild.id}: {channel.guild.name}] until: {unmute_at}")
            #assign the mute role to all members
            for m in channel.guild.members:
                await m.add_roles(self.role)
            #log a server mute
            operation = "REPLACE INTO mute VALUES (%s, %s, %s, %s);"
            params = (channel.guild.id, channel.guild.id, unmute_at, author.id)
            db.execute(operation, params)

            await std_embed.send_info(
                channel,
                title="SERVER MUTE",
                description=f"Muted all members until <t:{int(unmute_at.timestamp())}>",
                author=author
            )
            #wait until the time to unmute the server
            await discord.utils.sleep_until(unmute_at.astimezone())
            if self.compare_time(channel.guild):
                await unmute.unmute(channel, channel.guild, author)
                print(f"Server [#{channel.guild.id}: {channel.guild.name}] is unmuted")
        #if trying to mute a single member, but could not be found
        else:
            #if m is a string try to get the Member object
            if isinstance(m, str):
                member = await find.member(channel, m, responder=author)
                if member is None:
                    print(f"{m} could not be found")
                    await std_embed.send_error(
                        channel,
                        title=f"{m} Not Found"
                    )
                    return
                m = member

            #assign member the mute role
            await m.add_roles(self.role)

            #log a member mute
            operation = "REPLACE INTO mute VALUES (%s, %s, %s, %s);"
            params = (channel.guild.id, m.id, unmute_at, author.id)
            db.execute(operation, params)

            print(f"Muted @{m} until {unmute_at}")
            await std_embed.send_info(
                channel,
                title="MUTE",
                description=f"**Member:** {m.mention}\n**Until:** <t:{int(unmute_at.timestamp())}>",
                author=m
            )

            #wait until the time to unmute the member
            await discord.utils.sleep_until(unmute_at.astimezone())
            #check if member is logged and due to be unmuted
            if self.compare_time(channel.guild, m):
                operation = "SELECT * FROM mute WHERE Server = %s AND Member = %s;"
                params = (channel.guild.id, channel.guild.id)
                x = db.read_execute(operation, params)
                print(x)
                #if active server-mute, delete member from database but don't unmute them
                #if db.read_execute(operation, params):
                if x:
                    print(f"Server mute active. {m} was not unmuted.")
                    operation = "DELETE FROM mute WHERE Server = %s AND Member = %s;"
                    params = (channel.guild.id, m.id)
                    db.execute(operation, params)
                    return
                #calls unmute command from unmute.py
                await unmute.unmute(channel, channel.guild, author, m)
                print(f"{m} was unmuted.")





    #check if the member is due to be unmuted
    def compare_time(self, guild: discord.Guild, member: Optional[discord.Member] = None) -> bool:
        if member is None:
            params = (guild.id, guild.id)
        else:
            params = (guild.id, member.id)

        operation = "SELECT UnmuteDT FROM mute WHERE Server = %s AND Member = %s;"
        dt = db.read_execute(operation, params)
        print(f"dt fetch: {dt}")
        if dt:
            dt = dt[0][0]
            print(f"dt: {dt}")
            #parse the string to a datetime object and compare it to the current time
            return dt.astimezone(timezone.utc) < datetime.now().astimezone(timezone.utc)
        return False





mute = Mute_Command()
bot_commands.add_command(mute)
