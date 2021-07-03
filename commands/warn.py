import discord
import json
import random
from commands.mute import mute
from commands.unmute import unmute
from cmd import Bot_Command, bot_commands
from pathlib import Path
from datetime import datetime
from utils import get_member
#from commands.mute import command as mute

class Warn_Command(Bot_Command):
    name = "warn"

    short_help = "Warn a member in the server.\n**$warn [username/user id/nickname] [Optional reason]**\nGet the count of warns on a user.\n**$warn count [username/user id/nickname]**"

    long_help = """~Warns a member in the server or gets the count of warns on a user. 
    Warn Command Syntax: 
    **$warn [member] [Optional reason]**
    **$warn count [member]**
    `member`: *@User, User ID, Nickname* (Not Case Sensitive)
    'Optional reason': *Text* (Can have spaces)

    ~Example: (Assume this is the same user) 
    **$warn TheLegend47** or **$warn [1234567891012345678]** or **$warn Legend** """


    def __init__(self):
        self.warnings_path = Path("data/warn/warnings.json")
        if not self.warnings_path.exists():

            self.warning = {}
            self.save_warnings()
        else:
            with self.warnings_path.open() as file:
                self.warning = json.load(file)

    def save_warnings(self):
        with self.warnings_path.open("w") as file:
            json.dump(self.warning, file, indent=3)

    async def run(self, msg: discord.Message, args: str):
        if args.casefold().startswith("count ") and len(args) > len("count "):
            split_args = args.split(" ", 1)
            print(split_args)
            """ split_args[0] = count
                split_args[1:] = user_id """
            user_name = split_args[1]
            member = await get_member(msg.channel, user_name, msg.author)
            if member is None:
                await msg.channel.send(f"Error: **{user_name}** not found. If you are having trouble typing in a user's name, you can also use their User ID! Example: **$warn count {random.randint(100000000000000000, 999999999999999999)}**")
                return
            user_id = str(member.id)
            guild_id = str(msg.guild.id)
            if guild_id not in self.warning:
                await msg.channel.send("Error: No one in this server has been warned yet!")
                return
            if user_id not in self.warning[guild_id]:
                await msg.channel.send("This user has not been warned yet on this server.")
                return
            if user_id in self.warning[guild_id]:
                await msg.channel.send(f"**{member}** has been warned {self.warning[guild_id][user_id]['warning_count']} time(s).\nLast time warned: **{self.warning[guild_id][user_id]['last_warned_at']}** by **{self.warning[guild_id][user_id]['last_warned_by']}** ")
            return

        if msg.author.guild_permissions.administrator:
            if args is None:
                await msg.channel.send("Error: No user entered.")
                return
            split_args = args.split(" ", 1)
            """ split_args[0] = user_id
                split_args[1] = reason   """
            
            
            user_name = split_args[0]
            member = await get_member(msg.channel, user_name, msg.author)
            if member is None:
                await msg.channel.send(f"Error: **{user_name}** not found. If you are having trouble typing in a user's name, you can also use their User ID! Example: **$warn {random.randint(100000000000000000, 999999999999999999)}**")
                return
            user_id = str(member.id)

            
            guild_id = str(msg.guild.id)
            if guild_id not in self.warning:
                self.warning[guild_id] = {}
                self.save_warnings()

            red = 0xFF0000  # red
            warner = str(msg.author)
            user_info = {
                "warning_count": 1,
                "last_warned_at": str(datetime.now().replace(microsecond=0)),
                "last_warned_by": warner,
                "reasons": [],
                "message_logs": [],
            }

            if len(split_args) < 2:
                reason = "No reason given"
            else:
                reason = split_args[1]

            # run this 5 times
            check_counter = 0
            message_logs = []
            async for m in msg.channel.history(limit=200):
                if check_counter == 5:
                    break
                if m.author == member:
                    check_counter += 1
                    message_logs.append(m.content)

            message_logs.reverse()

            if user_id not in self.warning[guild_id]:
                self.warning[guild_id][user_id] = {}
                self.warning[guild_id][user_id].update(user_info)
                self.warning[guild_id][user_id]["reasons"].append(reason)
                self.warning[guild_id][user_id]["message_logs"].append(message_logs)
                self.save_warnings()
                                
                warning_message = discord.Embed(
                    title = "You have been warned!",
                    description = f"~You have been warned by **{msg.author}** from the server: **{msg.guild.name}**\n\n~The reason you were warned: **{reason}**\n\n~Since this is your first warning, nothing will happen to you. However, if you keep getting warned by mods you will either get muted or possibly banned depending on how many times you have been warned.\n\n~Be sure to not spam chats, say anything that would offend someone else, or post NSFW pictures in chats unless they are labeled NSFW.\n\n~If you believe you have been accidentally or wrongfully warned, don't hesitate to ping or PM a mod so that they can look into it.",
                    color = red
                    )
                await member.send(embed=warning_message)
                await msg.channel.send(
                    f"**{member}** has been warned. They have been warned **{self.warning[guild_id][user_id]['warning_count']}** time(s)."
                )
                return

            if user_id in self.warning[guild_id]:
                self.warning[guild_id][user_id]["warning_count"] += 1
                self.warning[guild_id][user_id].update(user_info)
                self.warning[guild_id][user_id]["reasons"].append(reason)
                self.warning[guild_id][user_id]["message_logs"].append(message_logs)
                self.save_warnings()
                
                previous_reasons = ""
                for reason in self.warning[guild_id][user_id]["reasons"]:
                    previous_reasons += "\n" + reason

                #https://stackoverflow.com/questions/9647202/ordinal-numbers-replacement  
                ordinal = lambda n: "%d%s" % (n,"tsnrhtdd"[(n//10%10!=1)*(n%10<4)*n%10::4])
                warning_count = self.warning[guild_id][user_id]["warning_count"]

                if self.warning[guild_id][user_id]["warning_count"] > 1:
                    warning_message = discord.Embed(
                        title = "You have been warned!",
                        description = f"~You have been warned by **{msg.author}** from the server: **{msg.guild.name}**\n\n~The reason you were warned: **{reason}**\n\n~This is your **{ordinal(warning_count)}** warning.\n\n~Previous Reason(s): **{previous_reasons}**\n\n~These are the punishments for a warning beyond the first one:\nTwo Warnings: Server Muted for **6 Hours**\nThree Warnings: Server Muted for **3 Days + SlowMode (One message per minute)**\nFour+ Warnings: A moderator will deal with you manually. This can result in a **permanent ban** or **permanent mute**.\n\n~Be sure to not spam chats, say anything that would offend someone else, or post NSFW pictures in chats unless they are labeled NSFW.\n\n~If you believe you have been accidentally or wrongfully warned, don't hesitate to ping or PM a mod so that they can look into it.",
                        color = red
                    )
                    await member.send(embed=warning_message)
                await msg.channel.send(
                    f"**{member}** has been warned. They have been warned **{self.warning[guild_id][user_id]['warning_count']}** time(s)."
                )
                return
        # elif args.casefold().startswith("count ") and len(args) > len("count "):
        #     split_args = args.split(" ")
        #     """ split_args[0] = count
        #         split_args[1] = user_id   """
        #     user_name = split_args[1]
        #     member = await get_member(msg.channel, user_name, responder=msg.author)
        #     if member is None:
        #         await msg.channel.send(f"Error: {user_name} Not Found")
        #         return
        #     user_id = str(member.id)
        #     guild_id = str(msg.guild.id)
        #     if guild_id not in self.warning:
        #         await msg.channel.send("Error: No one in this server has been warned yet!")
        #         return
        #     if user_id not in self.warning[guild_id]:
        #         await msg.channel.send("This user has not been warned yet on this server.")
        #         return
        #     if user_id in self.warning[guild_id]:
        #         await msg.channel.send(f"**{member}** has been warned {self.warning[guild_id][user_id]['warning_count']} times.\nLast time warned: **{self.warning[guild_id][user_id]['last_warned_at']}** by **{self.warning[guild_id][user_id]['last_warned_by']}** ")
        #     return
        
        else:
            await msg.channel.send("You need to be admin lol")


bot_commands.add_command(Warn_Command())