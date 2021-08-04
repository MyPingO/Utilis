from cmd import Bot_Command, bot_commands
from utils import get_member
from pathlib import Path
from typing import Optional, Union

import discord
import json
import datetime

class Unmute_Command(Bot_Command):
    name = "unmute"

    mute_log = Path("data/mute_log.json")

    short_help = "Unmutes user"

    long_help = f"""Unmutes the specified user.
    Arguments:
    `User`

    Replace `User` with `all` to server unmute.
    """

    def can_run(self, location, member):
        #only admins are able to use this command
        return member is not None and member.guild_permissions.administrator

    async def run(self, msg: discord.Message, args: str):
        #checks that user entered arguments for the command
        if args:
            #for server unmutes
            if args.lower() == "all":
                #server unmute
                await self.unmute(None, msg.channel, msg.author, True)
            else:
                #try to unmute the member
                await self.unmute(args, msg.channel, msg.author)

        #if user didnt enter any arguments
        else:
            print("Please specify a user.")
            embed = discord.Embed(
                title="[INPUT ERROR]",
                color=discord.Color.orange(),
                description="**A user was not specified**"
            )
            await msg.channel.send(embed=embed)





    #unmutes the passed member and removes them from the log file
    async def unmute(
            self,
            m: Optional[Union[discord.Member, str]],
            channel: discord.channel.TextChannel,
            author: discord.Member,
            server_unmute: bool = False
        ):
        """
        Parameters
        ------------

        m: Optional[Union[discord.Member, str]]
        The member to be unmuted.
        Required if server_unmute is `False`, otherwise should be `None`.

        channel: discord.channel.TextChannel
        The channel to send the unmute information to.

        author: discord.Member
        The moderator responsible for the unmute.

        server_unmute: bool
        Specifies whether or not to unmute all members in the server.
        Default value is False
        """

        #initialize the embed containing the unmute information
        embed = discord.Embed()
        #set the footer to the moderator responsible for the unmute
        embed.set_footer(text=f"By: {author} | {datetime.date.today().strftime('%m/%d/%Y')}")
        #get the mute role from this guild
        mute = discord.utils.get(channel.guild.roles, name="mute")

        with self.mute_log.open("r") as file:
            log = json.load(file)

        #check if server-wide unmute
        if server_unmute:
            #unmute all muted members
            try:
                #loop through muted members
                for mem in mute.members:
                    #skip any members that have been muted outside of the server mute
                    if str(mem.id) in log[str(author.guild.id)]:
                        continue
                    #remove the mute role
                    await mem.remove_roles(mute)
                #remove the server mute from the log file
                log[str(author.guild.id)].pop('server')
            except KeyError as ke:
                print(f"KeyError: {ke}")
                return
            except Exception as e:
                print(f"Error with server unmute\nException: {e}")
                embed.color = discord.Color.red()
                embed.set_author(
                    name="[ERROR] Server Unmute Failed",
                    icon_url=author.avatar_url_as(format='png')
                )
                await channel.send(embed=embed)
                return
            with self.mute_log.open("w") as file:
                json.dump(log, file, indent=4)
            print(f"Server unmute in [#{channel.guild.id}: {channel.guild.name}]")
            embed.color = discord.Color.green()
            embed.description = "**UNMUTED ALL MEMBERS**"
            embed.set_author(
                name=f"[SERVER UNMUTE]",
                icon_url=author.avatar_url_as(format='png')
            )
            await channel.send(embed=embed)
        #try to unmute the member
        else:
            #if m is a string try to get the Member object
            if isinstance(m, str):
                if await get_member(channel, m, responder=author) is None:
                    print(f"{m} could not be found")
                    embed.title = f"[{m}] Not Found"
                    embed.color = discord.Color.blue()
                    await channel.send(embed=embed)
                    return
                else:
                    m = await get_member(channel, m, responder=author)

            #if member isn't muted
            if mute not in m.roles:
                print(f"User @{m} is not muted")
                embed.set_author(
                    name=f"[UNMUTE] {m}",
                    icon_url=m.avatar_url_as(format='png')
                )
                embed.description = f"{m.mention}  is not muted"
                embed.color = discord.Color.blue()
                await channel.send(embed=embed)
            #unmute the member
            else:
                try:
                    #remove the member from the log file
                    log[str(m.guild.id)].pop(str(m.id))
                    with self.mute_log.open("w") as file:
                        json.dump(log, file, indent=4)
                    await m.remove_roles(mute)
                except KeyError as ke:
                    print(f"KeyError: {ke}")
                    #error if member is not logged to be muted
                    embed.color = discord.Color.red()
                    embed.set_author(
                        name=f"[ERROR] {m} Is Not Muted",
                        icon_url=m.avatar_url_as(format='png')
                    )
                    await channel.send(embed=embed)
                    return
                embed.set_author(
                    name=f"[UNMUTE] {m}",
                    icon_url=m.avatar_url_as(format='png')
                )
                embed.color = discord.Color.green()
                await channel.send(m.mention, embed=embed)


unmute = Unmute_Command()
bot_commands.add_command(unmute)
