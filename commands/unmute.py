from cmd import Bot_Command

import discord
from utils import get_member, format_max_utf16_len_string

class Unmute_Command(Bot_Command):
    name = "unmute"

    short_help = "Unmutes user"

    long_help = f"""Unmutes the specified user.
    Arguments:
    `User`

    Replace `User` with `all` to server unmute.
    """

    async def run(self, msg: discord.Message, args: str):
        #only admins are able to use this command
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
                    for m in guild.members:
                        await m.remove_roles(mute)
                    print("Unmuted all members")
                    await msg.channel.send("Unmuted all members")
                    return

                member = await get_member(msg.channel, parsed_args, responder=msg.author)
                if member is None:
                    print(f"User @\{parsed_args} could not be found")
                    await msg.channel.send(
                        format_max_utf16_len_string(
                            "User @\{} could not be found",
                            parsed_args
                        )
                    )
                    return
                #if member is muted
                if mute in member.roles:
                    #removes role from member
                    await member.remove_roles(mute)
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
                            "User @\{} is not muted",
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

command = Unmute_Command()
