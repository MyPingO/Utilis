from cmd import Bot_Command

import discord
import asyncio
import re
from utils import get_member

class Mute_Command(Bot_Command):
    name = "mute"

    default_time = "10m"
    
    short_help = "Mutes user for specified time"

    long_help = f"""Mutes the specified user for specified time. Default time is {default_time}. 
    Arguments:
    `User`
    `Time: [XXwXXdXXhXXm] (optional)`

    Empty time units may be omitted.
    Replace `User` with `all` to server mute.
    """

    async def run(self, msg: discord.Message, args: str):
        #only admins are able to use this command
        if msg.author.guild_permissions.administrator:
            #checks that user entered arguments for the command
            if args:
                #gets current server
                guild = msg.author.guild

                #creates 'mute' role if it doesn't already exist in this server
                if discord.utils.get(guild.roles, name="mute") is None:
                    #disables messaging, reaction and voice channel permissions
                    perms = discord.Permissions(send_messages=False, connect=False, speak=False, add_reactions=False)
                    await guild.create_role(name="mute", hoist=True, permissions=perms, color=0x36393f)
                mute = discord.utils.get(guild.roles, name="mute")

                try:
                    #if a time argument is specified
                    if self.second_conversion(args.rsplit(" ", 1)[1]):
                        parsed_args = args.rsplit(" ", 1)
                    #if only a user is mentioned (with spaces in username)
                    else:
                        parsed_args = [args.strip(), self.default_time]
                #if only username is specified (without spaces)
                except IndexError:
                    parsed_args = [args.strip(), self.default_time]

                seconds = self.second_conversion(parsed_args[1])

                #for server mutes
                if parsed_args[0].lower() == "all":
                    print(f"Muted @everyone for {parsed_args[1]}")
                    await msg.channel.send(f"Muted all members for {parsed_args[1]}")
                    for m in guild.members:
                        #doesn't assign role to serve owner and optionally admins
                        if m is guild.owner: #or m.guild_permissions.administrator:
                            continue
                        await m.add_roles(mute)
                    try:
                        await asyncio.sleep(self.second_conversion(parsed_args[1]))
                    except:
                        print("Could not mute everyone")
                        await msg.channel.send("Could not mute everyone")
                    for m in guild.members:
                        await m.remove_roles(mute)
                    return

                member = await get_member(msg.channel, parsed_args[0], responder=msg.author)
                #if member does not exist in this server
                if member is None:
                    print(f"User @{parsed_args[0]} could not be found")
                    await msg.channel.send(f"User @\{parsed_args[0]} could not be found")
                    return

                #assigns member the role
                await member.add_roles(mute)
                print(f"Muted @{member} for {parsed_args[1]}")
                await msg.channel.send(f"Muted {member.mention} for {parsed_args[1]}")
                #waits for the specified time and then removes the role from user
                await asyncio.sleep(seconds)
                await member.remove_roles(mute)
            #if user didnt enter any arguments
            else:
                print("Please specify a user and (optional) duration")
                await msg.channel.send("Please specify a user and (optional) duration")
        #unauthorized user tried to use this command
        else:
            print("You do not have permission to use this command.")
            await msg.channel.send("You do not have permission to use this command.")

    #takes in a string representing a time and converts it into seconds
    def second_conversion(self, time: str) -> int:
        units = re.split(r"(\d+\s*w)?\s*(\d+\s*d)?\s*(\d+\s*h)?\s*(\d+\s*m)?", time)
        seconds = 0
        for s in units:
            if s:
                if s[-1] == "w":
                    seconds += int(s[:-1]) * 604800
                elif s[-1] == "d":
                    seconds += int(s[:-1]) * 86400
                elif s[-1] == "h":
                    seconds += int(s[:-1]) * 3600
                elif s[-1] == "m":
                    seconds += int(s[:-1]) * 60
        return seconds

command = Mute_Command()
