from cmd import Bot_Command, bot_commands
from pathlib import Path
from utils import get_member, format_max_utf16_len_string
from commands.unmute import unmute
from main import bot_prefix

import datetime
import json
import discord
import asyncio
import re

class Mute_Command(Bot_Command):
    name = "mute"

    default_time = "10m"

    mute_log = Path("data/mute_log.json")

    short_help = "Mutes user for specified time"

    long_help = f"""Mutes the specified user for specified time. Default time is {default_time}.
    Arguments:
    `User`
    `Time: [XXwXXdXXhXXm] (optional)`

    Empty time units may be omitted.
    Replace `User` with `all` to server mute.

    Examples: `{bot_prefix}mute @user 2h` `{bot_prefix}mute nickname 2h` `{bot_prefix}mute @user`
    """

    #ensures log file exists and self.muted contains its contents
    def __init__(self):
        #if the log file does not exist, create it
        if not self.mute_log.exists():
            self.mute_log.parent.mkdir(parents=True, exist_ok=True)
            self.muted = {}
            self.save()
        with self.mute_log.open("r") as file:
            self.muted = json.load(file)





    def can_run(self, location, member):
        # only admins are able to use this command
        return member is not None and member.guild_permissions.administrator





    async def run(self, msg: discord.Message, args: str): 
        #checks that user entered arguments for the command
        if args:
            #gets current server
            guild = msg.author.guild
            #gets current channel
            channel = msg.channel

            #creates 'mute' role if it doesn't already exist in this server
            if discord.utils.get(guild.roles, name="mute") is None:
                #disables messaging, reaction and voice channel permissions
                perms = discord.Permissions(send_messages=False, connect=False, speak=False, add_reactions=False)
                await guild.create_role(name="mute", hoist=True, permissions=perms, color=0x36393f)
            self.role = discord.utils.get(guild.roles, name="mute")

            #split the mute duration from the member
            parsed_args = self.split_args(args)

            #convert the mute duration into a datetime object
            unmute_at = self.date_conversion(parsed_args[1:])

            #for server mutes
            if parsed_args[0].lower() == "all":
                try:
                    for mem in guild.members:
                        #doesn't assign role to server admins
                        if mem.guild_permissions.administrator:
                            continue
                        #if member is not already muted, mute them
                        if self.role not in mem.roles:
                            await self.mute(mem, unmute_at)
                except Exception as e:
                    print(e)
                    print("Could not mute everyone")
                    await channel.send("Could not mute everyone")
                    return
                print(f"Muted @everyone for {self.date_string(parsed_args[1:])}")
                await channel.send(f"Muted all members for {self.date_string(parsed_args[1:])}")

                #sleep until the time to unmute everyone
                await discord.utils.sleep_until(unmute_at)
                for mem in guild.members:
                    #check if the member is muted and due to be unmuted
                    if self.role in mem.roles and self.compare_time(mem):
                        #calls the unmute command from unmute.py
                        await unmute.unmute(mem, channel)
                await channel.send("Unmuted all members")
            else:
                #get the member to be muted
                member = await get_member(channel, m=parsed_args[0], responder=msg.author)

                if await self.mute(member, unmute_at):
                    print(f"Muted @{member}")
                    await channel.send(f"Muted **{member}** for {self.date_string(parsed_args[1:])}")

                    #waits for the specified time and then removes the role from user
                    await discord.utils.sleep_until(unmute_at)
                    #check if member is muted and is due to be unmuted
                    if self.compare_time(member):
                        #calls unmute command from unmute.py
                        await unmute.unmute(member, channel)
                        print(f"{member} was unmuted.")
                        await channel.send(f"{member} was unmuted.")
                #if member does not exist in this server
                else:
                    print(f"User @{parsed_args[0]} could not be found")
                    await channel.send(
                        format_max_utf16_len_string(
                            "User **{}** could not be found",
                            parsed_args[0]
                        )
                    )

        #if user didnt enter any arguments
        else:
            print("A user (and optional duration) must be provided")
            await msg.channel.send("A user (and optional duration) must be provided.")





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
            if units_dict[group] is None:
                parsed_args.append(0)
            else:
                parsed_args.append(int(units_dict[group]))

        #if all time units are zeroed out, time wasn't specified or formatted incorrectly and the default time is used
        if 0 in parsed_args[1:] and len(set(parsed_args[1:])) == 1:
            parsed_args = self.split_args(f"{parsed_args[0]} {self.default_time}")
        return parsed_args





    #adds the mute duration onto the current datetime
    def date_conversion(self, time: list) -> datetime.datetime:
        return datetime.datetime.now(tz=datetime.timezone(datetime.timedelta(hours=-4))) + datetime.timedelta(weeks=time[0], days=time[1], hours=time[2], minutes=time[3])





    #formats the list of time units into a string
    def date_string(self, time: list) -> str:
        out = ""
        if time[0]:
            out += f"{time[0]} week(s) "
        if time[1]:
            out += f"{time[1]} day(s) "
        if time[2]:
            out += f"{time[2]} hour(s) "
        if time[3]:
            out += f"{time[3]} minute(s)"
        return out





    #mutes the passed member given a string representation of a string
    async def mute(self, member: discord.Member, unmute_at: str) -> bool:
        if member is not None:
            #assign the member the mute role
            await member.add_roles(self.role)
            #writes to the file when the member should be unmuted
            if str(member.guild.id) not in self.muted:
                self.muted[str(member.guild.id)] = {str(member.id): unmute_at}
            else:
                self.muted[str(member.guild.id)][str(member.id)] = unmute_at
            self.save()
            return True
        else:
            return False





    #mutes the passed member given a datetime object
    async def mute(self, member: discord.Member, unmute_at: datetime.datetime) -> bool:
        if member is not None:
            #assign member the mute role
            await member.add_roles(self.role)
            #writes to the file when the member should be unmuted
            if str(member.guild.id) not in self.muted:
                self.muted[str(member.guild.id)] = {str(member.id): str(unmute_at)}
            else:
                self.muted[str(member.guild.id)][str(member.id)] = str(unmute_at)
            self.save()
            return True
        else:
            return False





    #check if the member is due to be unmuted
    def compare_time(self, member: discord.Member) -> bool:
        with self.mute_log.open("r") as file:
            self.muted = json.load(file)
            #get the datetime of when this member should be unmuted
            unmute_date = self.muted[str(member.guild.id)][str(member.id)]
            #parse the string to a datetime object and compare it to the current time
            return datetime.datetime.strptime(unmute_date, '%Y-%m-%d %H:%M:%S.%f%z') < datetime.datetime.now(tz=datetime.timezone(datetime.timedelta(hours=-4)))





    #save any writes to the log file
    def save(self):
        with self.mute_log.open("w") as file:
            json.dump(self.muted, file, indent=4)

bot_commands.add_command(Mute_Command())
