import discord
import json

from bot_cmd import Bot_Command, bot_commands, Bot_Command_Category
from discord import guild
from utils import wait_for_reply
from pathlib import Path
from main import bot_prefix

class Syllabus_Command(Bot_Command):
    name = "syllabus"
    short_help = "Gives syllabus of specified professor."
    long_help = "Gives syllabus of specified professor. Type $syllabus [professor] to get a download link for that professors syllabus."
    category = Bot_Command_Category.CLASS_INFO

    syllabus_path = Path("data/syllabus")
    # downloadSyllabus_path = Path("data/syllabus/211syllabus.pdf")

    async def run(self, msg: discord.Message, args: str):
        args.strip("syllabus")
        guild_id = str(msg.guild.id)
        if args.casefold() == "add":
            await msg.channel.send("Enter the class number")
            while True:
                class_number = await wait_for_reply(msg.author, msg.channel)
                if not all(class_number.isnumeric()):
                    await msg.channel.send("Class number can only contain numbers. Please try again or type **Stop** to exit the command.")
                    continue
                else:
                    break
            syllabus_path = (self.syllabus_path/guild_id/class_number)
            if syllabus_path.exists():
                await msg.channel.send(f"The syllabus to this class has already been added. To view it type **{bot_prefix} syllabus {class_number}")
        return
bot_commands.add_command(Syllabus_Command())