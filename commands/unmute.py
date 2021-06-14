from cmd import Bot_Command, bot_commands
from utils import get_member, format_max_utf16_len_string
from pathlib import Path

import discord
import json

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
            #current server
            guild = msg.author.guild

            #for server unmutes
            if args.lower() == "all":
                try:
                    for mem in guild.members:
                        #remove the mute role from the member and remove them from the log file
                        await self.unmute(mem, msg.channel)
                    print("Unmuted all members")
                    await msg.channel.send("Unmuted all members")
                except Exception as e:
                    print(e)
                    print("There was an error unmuting all members")
                    await msg.channel.send("Could not unmute all members")
                return

            #get the member to be unmuted
            member = await get_member(msg.channel, args, responder=msg.author)

            #if member is muted
            if await self.unmute(member, msg.channel):
                print(f"User @{member} was unmuted")
                await msg.channel.send(
                    format_max_utf16_len_string(
                        "User **{}** was unmuted",
                        member.mention
                    )
                )

        #if user didnt enter any arguments
        else:
            print("Please specify a user.")
            await msg.channel.send("Please specify a user.")





    #unmutes the passed member and removes them from the log file
    async def unmute(self, member: discord.Member, channel: discord.channel.TextChannel) -> bool:
        #verify member exists
        if member is None:
            print(f"User could not be found")
            await channel.send(
                format_max_utf16_len_string("**User could not be found**")
            )
            return False

        #get the mute role from this guild
        mute = discord.utils.get(member.guild.roles, name="mute")

        #if user isn't muted
        if mute not in member.roles:
            print(f"User @{member} is not muted")
            await channel.send(
                format_max_utf16_len_string(
                    "User **{}** is not muted",
                    member
                )
            )
            return False

        #unmute the member
        await member.remove_roles(mute)
        with self.mute_log.open("r") as file:
            log = json.load(file)
        with self.mute_log.open("w") as file:
            log[str(member.guild.id)].pop(str(member.id))
            json.dump(log, file, indent=4)
        return True


unmute = Unmute_Command()
bot_commands.add_command(unmute)
