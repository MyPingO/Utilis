from bot_cmd import Bot_Command, bot_commands, Bot_Command_Category
from pathlib import Path
from utils import find
from commands.unmute import unmute
from main import bot_prefix
from typing import Optional, Union

import datetime
import json
import discord
import asyncio
import re

class Mute_Command(Bot_Command):
    name = "mute"

    default_time = "10m"

    mute_log = Path("data/mute/muted.json")

    short_help = "Mutes user for specified time"

    long_help = f"""Mutes the specified user for specified duration. Default duration is {default_time}.
    Arguments:
    `User`
    `Duration: [XXwXXdXXhXXm] (optional)`

    Empty time units may be omitted.
    Replace `User` with `all` to server mute.

    Examples: `{bot_prefix}mute @user 2h` `{bot_prefix}mute nickname 2h` `{bot_prefix}mute @user`
    """

    category = Bot_Command_Category.TOOLS

    #ensures log file exists and self.muted contains its contents
    def __init__(self):
        #if the log file does not exist, create it
        if not self.mute_log.exists():
            self.mute_log.parent.mkdir(parents=True, exist_ok=True)
            self.muted = {}
            self.save()
        self.update()





    def can_run(self, location, member):
        # only admins are able to use this command
        return member is not None and member.guild_permissions.administrator





    async def run(self, msg: discord.Message, args: str):
        #gets current channel
        channel = msg.channel
        #checks that user entered arguments for the command
        if args:
            #split the mute duration from the member
            parsed_args = self.split_args(args)

            #convert the mute duration into a datetime object
            unmute_at = self.date_conversion(parsed_args[1:])

            #for server mutes
            if parsed_args[0].lower() == "all":
                await self.mute(None, unmute_at, channel, msg.author, server_mute=True)

            #get the mute info for a specified member
            elif args.lower().startswith("info "):
                #get server mute info
                if args[5:].lower().strip() == "all":
                    await self.get_info(None, channel, True)
                    return
                #get the member whose info is being requested
                member = await find.member(channel, args[5:].strip(), msg.author)
                if member is None:
                    embed = discord.Embed(
                        title="[ERROR] Not Found",
                        color=discord.Color.blue(),
                        description=f"**[{args[5:].strip()}]** could not be found"
                    )
                    await channel.send(embed=embed)
                else:
                    await self.get_info(member, channel)

            #muting a single member
            else:
                #get the member to be muted
                member = await find.member(channel, m=parsed_args[0], responder=msg.author)
                if member is None:
                    print(f"{parsed_args[0]} could not be found")
                    embed = discord.Embed(
                        title=f"[{parsed_args[0]}] Not Found",
                        color=discord.Color.blue()
                    )
                    await channel.send(embed=embed)
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
                await self.mute(member, unmute_at, channel, msg.author)
        #if user didnt enter any arguments
        else:
            print("A user (and optional duration) must be provided")
            embed = discord.Embed(
                title="[INPUT ERROR]",
                color=discord.Color.orange(),
                description="**A user (and optional duration) must be provided.**"
            )
            await channel.send(embed=embed)





    #gets the mute information regarding the specified member
    async def get_info(self, member: Optional[discord.Member], channel: discord.TextChannel, server_log: bool = False):
        guild_id = str(channel.guild.id)
        embed = discord.Embed(color=discord.Color.blue())
        self.update()
        try:
            if server_log:
                #get the date and time when the server will be unmuted
                date = self.muted[guild_id]['server']['unmute_at']
                #get the moderator responsible for the mute
                mod = await find.member(channel, str(self.muted[guild_id]['server']['by']))
                embed.set_author(
                    name="[MUTE INFO]",
                    icon_url=mod.avatar_url_as(format='png')
                )
            else:
                #get the date and time when this member will be unmuted
                date = self.muted[guild_id][str(member.id)]['unmute_at']
                #get the moderator responsible for the mute
                mod = await find.member(channel, (self.muted[guild_id][str(member.id)]['by']))
                embed.set_author(
                    name="[MUTE INFO]",
                    icon_url=member.avatar_url_as(format='png')
                )
        #catch KeyError if no logged mute is found
        except KeyError as ke:
            print(f"Key Error: {ke}")
            embed.description = f"{'A server mute is not active' if server_log else f'{member.mention} is not muted'}"
            if server_log:
                embed.title = "[MUTE INFO]"
            else:
                embed.set_author(
                    name="[MUTE INFO]",
                    icon_url=member.avatar_url_as(format='png')
                )
            await channel.send(embed=embed)
            return
        embed.description = f"""
        {'**SERVER MUTE**' if server_log else f'**Member:** {member.mention}'}
        **Until:** {date} EST
        **By:** {mod.mention}
        """
        await channel.send(embed=embed)





    #gets the mute role for this server
    async def get_role(self, guild: discord.Guild):
        #disables chat permissions
        text_perms = discord.PermissionOverwrite(
            send_messages=False,
            send_tts_messages=False,
            add_reactions=False,
        )
        #disable voice permissions
        voice_perms = discord.PermissionOverwrite(
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
        for text_channel in guild.text_channels:
            await text_channel.set_permissions(self.role, overwrite=text_perms)
        for voice_channel in guild.voice_channels:
            await voice_channel.set_permissions(self.role, overwrite=voice_perms)





    #separate the mute duration from the user being muted
    def split_args(self, args: str) -> list:
        parsed_args = []

        #get the mute duration from the full string (case insensitive)
        duration = re.search(r"((?:(?P<weeks>\d+)\s*w)?\s*(?:(?P<days>\d+)\s*d)?\s*(?:(?P<hours>\d+)\s*h)?\s*(?:(?P<minutes>\d+)\s*m)?$)", args, re.I)

        #append the user being muted to the list
        parsed_args.append(args[:duration.start()].strip())

        #separate the units into a dictionary
        units_dict = duration.groupdict()

        #standardize the unit values
        for group in units_dict:
            if not units_dict[group]:
                parsed_args.append(0)
            else:
                parsed_args.append(int(units_dict[group]))

        #if all time units are zeroed out, time wasn't specified or formatted incorrectly and the default time is used
        if (0 in parsed_args[1:]) and (len(set(parsed_args[1:])) == 1):
            parsed_args = self.split_args(f"{parsed_args[0]} {self.default_time}")
        return parsed_args





    #adds the mute duration onto the current datetime
    def date_conversion(self, time: list) -> datetime.datetime:
        return datetime.datetime.now(tz=datetime.timezone(datetime.timedelta(hours=-4))) + datetime.timedelta(weeks=time[0], days=time[1], hours=time[2], minutes=time[3])





    #mutes the passed member given a datetime object
    async def mute(
            self,
            m: Optional[Union[discord.Member, str]],
            unmute_at: datetime.datetime,
            channel: discord.TextChannel,
            author: discord.Member,
            server_mute: bool = False
        ):
        """
        Parameters
        ------------

        m: Optional[Union[discord.Member, str]]
        The member to be muted.
        Required if server_mute is `False`, otherwise should be 'None'.

        unmute_at: datetime.datetime
        A datetime object specifying when the
        member or server should be unmuted.

        channel: discord.TextChannel
        The channel to send the mute information to.

        author: discord.Member
        The moderator responsible for the mute.

        server_mute: bool
        Specifies whether or not to mute all members in the server.
        Default value is False
        """

        #initialize the embed containing the mute information
        embed = discord.Embed()
        #the footer explains who is responsible for the mute and today's date
        embed.set_footer(text=f"By: {author} | {datetime.date.today().strftime('%m/%d/%Y')}")

        self.update()
        if str(channel.guild.id) not in self.muted:
            self.muted[str(channel.guild.id)] = {}
            self.save()

        #get the mute role
        await self.get_role(channel.guild)

        #server-wide mute
        if server_mute:
            embed.color = discord.Color.green()
            embed.set_author(
                name="[SERVER MUTE]",
                icon_url=author.avatar_url_as(format='png')
            )

            print(f"Muted server [#{channel.guild.id}: {channel.guild.name}] until: {unmute_at}")
            embed.description = f"Muted all members until **{unmute_at.strftime('%m/%d/%Y %I:%M %p')}**"
            #assign the mute role to all members
            for m in channel.guild.members:
                await m.add_roles(self.role)
            #log a server mute
            self.muted[str(channel.guild.id)]['server'] = {'unmute_at': unmute_at.strftime('%m/%d/%Y %I:%M %p'), 'by': author.id}
            self.save()
            await channel.send(embed=embed)
            #wait until the time to unmute the server
            await discord.utils.sleep_until(unmute_at)
            #check if server-mute is logged and due to be unmuted
            if self.compare_time(author, True):
                await unmute.unmute(None, channel, author, True)
                print(f"Server [#{channel.guild.id}: {channel.guild.name}] is unmuted")
        #if trying to mute a single member, but could not be found
        else:
            #if m is a string try to get the Member object
            if isinstance(m, str):
                if await find.member(channel, m, responder=author) is None:
                    print(f"{m} could not be found")
                    embed.title = "[{m}] Not Found"
                    embed.color = discord.Color.blue()
                    await channel.send(embed=embed)
                    return
                else:
                    m = await find.member(channel, m, responder=author)

            #assign member the mute role
            await m.add_roles(self.role)
            #log the mute to the file
            self.muted[str(m.guild.id)][str(m.id)] = {'unmute_at': unmute_at.strftime('%m/%d/%Y %I:%M %p'), 'by': str(author.id)}
            self.save()

            print(f"Muted @{m} until {unmute_at}")
            embed.description = f"""
            **Member:** {m.mention}
            **Until:** {unmute_at.strftime('%m/%d/%Y %I:%M %p')}
            """
            embed.color = discord.Color.green()
            embed.set_author(
                name="[MUTE]",
                icon_url=m.avatar_url_as(format='png')
            )
            await channel.send(embed=embed)

            #wait until the time to unmute the member
            await discord.utils.sleep_until(unmute_at)
            #check if member is logged and due to be unmuted
            if self.compare_time(m):
                #if active server-mute, remove member from log file but don't unmute them
                if 'server' in self.muted[str(m.guild.id)]:
                    print(f"Server mute active. {m} was not unmuted.")
                    self.muted[str(m.guild.id)].pop(str(m.id))
                    self.save()
                    return
                #calls unmute command from unmute.py
                await unmute.unmute(m, channel, author)
                print(f"{m} was unmuted.")





    #check if the member is due to be unmuted
    def compare_time(self, member: discord.Member, server_log: bool = False) -> bool:
        try:
            self.update()
            if server_log:
                #get the datetime of when the server should be unmuted
                unmute_datetime = self.muted[str(member.guild.id)]['server']['unmute_at']
            elif member:
                #get the datetime of when the member should be unmuted
                unmute_datetime = self.muted[str(member.guild.id)][str(member.id)]['unmute_at']
            #parse the string to a datetime object and compare it to the current time
            return datetime.datetime.strptime(unmute_datetime, '%m/%d/%Y %I:%M %p') < datetime.datetime.now()
        except json.JSONDecodeError as jde:
            print(f"JSONDecodeError: {jde}")
            return False
        except KeyError as ke:
            print(f"Key Error {ke}")
            return False





    #updates self.muted with the file content
    def update(self):
        #if file is empty, initialize it
        if not self.mute_log.read_text().strip():
            self.muted = {}
            self.save()
        try:
            #update self.muted with the log file contents
            with self.mute_log.open("r") as file:
                self.muted = json.load(file)
        except json.JSONDecodeError as jde:
            print(f"JSONDecodeError: {jde}")





    #save any writes to the log file
    def save(self):
        with self.mute_log.open("w") as file:
            json.dump(self.muted, file, indent=4)

mute = Mute_Command()
bot_commands.add_command(mute)
