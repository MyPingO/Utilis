from bot_cmd import Bot_Command, bot_commands, Bot_Command_Category
from utils import std_embed

import discord
import random
import re


class Random_Command(Bot_Command):
    name = "random"

    aliases = ["rand"]

    short_help = "Sends a random number in range."

    long_help = """Sends a random number in the specified range.
    __Usage:__
    **random** *num1 num2*
    **rand** *num1 num2*
    """

    args_matcher = re.compile(r"^(\d+)\s+(\d+)$")

    async def run(self, msg: discord.Message, args: str):
        m = self.args_matcher.fullmatch(args)
        if m is not None:
            arg1, arg2 = sorted((int(m.group(1)), int(m.group(2))))
            # requires user to enter a valid range
            if arg1 == arg2:
                await std_embed.send_error(msg.channel, description="Please enter two different numbers")
                return
            await std_embed.send_info(msg.channel, description=random.randint(arg1, arg2))

        else:
            await std_embed.send_error(msg.channel, description="Must enter 2 integer value arguments")


bot_commands.add_command(Random_Command())
