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
        # TODO: Remove this check
        if msg.author.guild_permissions.administrator:
            #checks that user entered arguments for the command
            if args:
                #trims whitespace off of args
                parsed_args = args.strip()
                #current server
                guild = msg.author.guild

                mute = discord.utils.get(guild.roles, name="mute")

                #for server unmutes
                if parsed_args.lower() == "all":
                    try:
                        for m in guild.members:
                            #remove the mute role from the member and remove them from the log file
                            await m.remove_roles(mute)
                            with self.mute_log.open("w") as file:
                                log = json.load(file)
                                log[str(guild.id)].pop(str(m.id))
                                json.dump(log, file, indent=4)
                        print("Unmuted all members")
                        await msg.channel.send("Unmuted all members")
                    except Exception as e:
                        print(e)
                        print("There was an error unmuting all members")
                        await msg.channel.send("Could not unmute all members")
                    return

                #get the member to be unmuted
                member = await get_member(msg.channel, parsed_args, responder=msg.author)

                #if member could not be found
                if member is None:
                    print(f"User @{parsed_args} could not be found")
                    await msg.channel.send(
                        format_max_utf16_len_string(
                            "User **@\{}** could not be found",
                            parsed_args
                        )
                    )
                    return

                #if member is muted
                if mute in member.roles:
                    #remove role from member and remove member from log file
                    await member.remove_roles(mute)
                    with self.mute_log.open("w") as file:
                        log = json.load(file)
                        log[str(guild.id)].pop(str(member.id))
                        json.dump(log, file, indent=4)

                    print(f"User @{member} was unmuted")
                    await msg.channel.send(
                        format_max_utf16_len_string(
                            "User {} was unmuted",
                            member.mention
                        )
                    )
                else:
                    print(f"User @{member} is not muted")
                    await msg.channel.send(
                        format_max_utf16_len_string(
                            "User **@\{}** is not muted",
                            member
                        )
                    )
            #if user didnt enter any arguments
            else:
                print("Please specify a user.")
                await msg.channel.send("Please specify a user.")
        #unauthorized user tried to use this command
        else:
            print("You do not have permission to use this command.")
            await msg.channel.send("You do not have permission to use this command.")

unmute = Unmute_Command()
bot_commands.add_command(unmute)
