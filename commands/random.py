from cmd import Bot_Command, bot_commands

import discord
import random
import re


class Random_Command(Bot_Command):
    name = "random"

    short_help = "Sends a random number in range."

    long_help = """Sends a random number in the specified range.
    Arguments:
    `Lower bound`
    `Upper bound`
    """

    args_matcher = re.compile(r"^(\d+)\s+(\d+)$")

    async def run(self, msg: discord.Message, args: str):
        m = self.args_matcher.fullmatch(args)
        if m is not None:
            arg1, arg2 = sorted((int(m.group(1)), int(m.group(2))))
            # requires user to enter a valid range
            if arg1 == arg2:
                print("Please enter two different numbers")
                await msg.channel.send("Please enter two different numbers")
                return
            num = random.randint(arg1, arg2)

            print(num)
            await msg.channel.send(num)
        else:
            print("Must enter 2 integer values arguments")
            await msg.channel.send("Must enter 2 integer value arguments")


bot_commands.add_command(Random_Command())
