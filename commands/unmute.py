from bot_cmd import Bot_Command, bot_commands, Bot_Command_Category
from utils import find, std_embed
from typing import Optional, Union

import discord
import datetime
import db

class Unmute_Command(Bot_Command):
    name = "unmute"

    short_help = "Unmutes user"

    long_help = f"""Unmutes the specified user.
    __Usage:__
    **unmute** *member*|**all**
    """

    category = Bot_Command_Category.MODERATION

    def can_run(self, location, member):
        #only admins are able to use this command
        return member is not None and member.guild_permissions.administrator

    async def run(self, msg: discord.Message, args: str):
        #checks that user entered arguments for the command
        if args:
            #for server unmutes
            if args.lower() == "all":
                #server unmute
                await self.unmute(msg.channel, msg.guild, msg.author)
            else:
                #try to unmute the member
                await self.unmute(msg.channel, msg.guild, msg.author, args)

        #if user didnt enter any arguments
        else:
            print("Please specify a user.")
            await std_embed.send_error(
                msg.channel,
                title="ERROR",
                description="**A user was not specified**"
            )





    #unmutes the passed member and removes them from the log file
    async def unmute(
            self,
            channel: discord.channel.TextChannel,
            guild: discord.Guild,
            author: discord.Member,
            m: Optional[Union[discord.Member, str]] = None,
        ):
        """
        Parameters
        ------------
        channel: discord.channel.TextChannel
        The channel to send the unmute information to.

        guild: discord.Guild
        The guild where the unmute is occurring.

        author: discord.Member
        The moderator responsible for the unmute.

        m: Optional[Union[discord.Member, str]]
        The member to be unmuted.
        Unmutes the server if None.
        """

        #get the mute role from this guild
        #TODO get role by id from server-attributes table
        mute = discord.utils.get(channel.guild.roles, name="mute")

        #server unmute
        if m is None:
            operation = "SELECT * FROM mute WHERE Server = %s AND Member = %s;"
            params = (guild.id, guild.id)
            if not db.read_execute(operation, params):
                await std_embed.send_info(
                    channel,
                    title="SERVER UNMUTE",
                    description="A server mute is not active."
                )
                return
            for mem in mute.members:
                #skip any members that have been muted outside of the server mute
                operation = "SELECT * FROM mute WHERE Server = %s AND Member = %s;"
                params = (guild.id, mem.id)
                if db.read_execute(operation, params):
                    continue
                #remove the mute role
                await mem.remove_roles(mute)
            #remove the server mute from the log file
            operation = "DELETE FROM mute WHERE Server = %s AND Member = %s;"
            params = (guild.id, guild.id)
            db.execute(operation, params)
            print(f"Server unmute in [#{channel.guild.id}: {channel.guild.name}]")
            await std_embed.send_success(
                channel,
                title="SERVER UNMUTE",
                author=author
            )
        #member unmute
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

            #if member isn't muted
            if mute not in m.roles:
                print(f"User @{m} is not muted")
                await std_embed.send_error(
                    channel,
                    title="UNMUTE",
                    description=f"{m.mention} is not muted",
                    author=m
                )

            #unmute the member
            else:
                #delete the member from the table
                operation = "DELETE FROM mute WHERE Server = %s AND Member = %s;"
                params = (guild.id, m.id)
                db.execute(operation, params)

                #check if a server-mute is active, then don't remove the role
                operation = "SELECT * FROM mute WHERE Server = %s AND Member = %s;"
                params = (guild.id, guild.id)
                #delete the member from the table but don't remove the role
                if db.read_execute(operation, params):
                    await std_embed.send_error(
                        channel,
                        title="Active Server-Mute",
                        author=m
                    )
                else:
                    await m.remove_roles(mute)
                    embed = std_embed.get_success(
                        title=f"UNMUTE {m}",
                        author=m
                    )
                    await channel.send(m.mention, embed=embed)


unmute = Unmute_Command()
bot_commands.add_command(unmute)
