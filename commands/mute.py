from cmd import Bot_Command
from pathlib import Path
from utils import get_member
from commands.unmute import command as unmute
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

    async def run(self, msg: discord.Message, args: str):
        #only admins are able to use this command
        if msg.author.guild_permissions.administrator:
            #checks that user entered arguments for the command
            if args:
                #gets current server
                guild = msg.author.guild
                #gets current channel
                channel = msg.channel

                with self.mute_log.open("r") as file:
                    try:
                        self.muted = json.load(file)
                    except Exception as e:
                        self.muted = {}
                        print(e)
                        self.save()

                #creates 'mute' role if it doesn't already exist in this server
                if discord.utils.get(guild.roles, name="mute") is None:
                    #disables messaging, reaction and voice channel permissions
                    perms = discord.Permissions(send_messages=False, connect=False, speak=False, add_reactions=False)
                    await guild.create_role(name="mute", hoist=True, permissions=perms, color=0x36393f)
                mute = discord.utils.get(guild.roles, name="mute")

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
                            if mute not in mem.roles:
                                await self.log_mute(mem, mute, unmute_at)
                    except Exception as e:
                        print(e)
                        print("Could not mute everyone")
                        await channel.send("Could not mute everyone")
                        return
                    print(f"Muted @everyone")
                    await channel.send(f"Muted all members")
                    
                    #sleep until the time to unmute everyone
                    await discord.utils.sleep_until(unmute_at)
                    for mem in guild.members:
                        #check if the member is muted and due to be unmuted
                        if mute in mem.roles and self.compare_time(mem):
                            #calls the unmute command from unmute.py
                            await unmute.run(msg, str(member))
                else:
                    #get the member to be muted
                    member = await get_member(channel, m=parsed_args[0], responder=msg.author)
                    
                    #if member does not exist in this server
                    if member is None:
                        print(f"User @{parsed_args[0]} could not be found")
                        await channel.send(f"User **\@{parsed_args[0]}** could not be found")
                    else:
                        await self.log_mute(member, mute, str(unmute_at))
                        print(f"Muted @{member}")
                        await channel.send(f"Muted **{member}**")

                        #waits for the specified time and then removes the role from user
                        await discord.utils.sleep_until(unmute_at)
                        #check if member is muted and is due to be unmuted
                        if mute in member.roles and self.compare_time(member):
                            #calls unmute command from unmute.py
                            await unmute.run(msg, str(member))

            #if user didnt enter any arguments
            else:
                print("A user (and optional duration) must be provided")
                await msg.channel.send("A user (and optional duration) must be provided.")

        #unauthorized user tried to use this command
        else:
            print("{msg.author} tried to use the mute command.")
            await msg.channel.send("You do not have permission to use this command.")





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

        #if all time units are zeroed out, no time was specified and the default time is used
        if 0 in parsed_args[1:] and len(set(parsed_args[1:])) == 1:
            parsed_args = self.split_args(f"{parsed_args[0]} {self.default_time}")
        return parsed_args





    #adds the mute duration onto the current datetime
    def date_conversion(self, time: list) -> datetime.datetime:
        return datetime.datetime.now(tz=datetime.timezone(datetime.timedelta(hours=-4))) + datetime.timedelta(weeks=time[0], days=time[1], hours=time[2], minutes=time[3])





    #writes to the log file: server id, member being muted, when to unmute
    async def log_mute(self, member: discord.Member, role: discord.Role, unmute_at: str):
        #assign the member the mute role
        await member.add_roles(role)
        #writes to the file when the member should be unmuted
        if str(member.guild.id) not in self.muted: 
            self.muted[str(member.guild.id)] = {str(member.id): str(unmute_at)}
        else:
            self.muted[str(member.guild.id)][str(member.id)] = str(unmute_at)
        self.save()





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

command = Mute_Command()
