from bot_cmd import Bot_Command, bot_commands, Bot_Command_Category

import discord
import random


class Coin_Flip_Command(Bot_Command):
    name = "coinflip"

    coin = ["heads", "tails"]

    short_help = "Flips a coin"

    long_help = """Simulates a coin flip and sends the result
    Arguments:
    `None`
    """

    category = Bot_Command_Category.MODERATION

    async def run(self, msg: discord.Message, args: str):
        choice = f"{random.choice(self.coin)}"
        print(choice)
        await msg.channel.send(choice)


bot_commands.add_command(Coin_Flip_Command())
