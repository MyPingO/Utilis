from bot_cmd import Bot_Command, bot_commands, Bot_Command_Category
from utils import std_embed

import discord
import random


class Coin_Flip_Command(Bot_Command):
    name = "coinflip"

    coin = ["Heads!", "Tails!"]

    short_help = "Flips a coin"

    long_help = """Simulates a coin flip and sends the result
    __Usage:__
    **coinflip**
    """

    async def run(self, msg: discord.Message, args: str):
        await std_embed.send_info(
            msg.channel,
            title="Coinflip",
            description=random.choice(self.coin),
            author=msg.author,
        )


bot_commands.add_command(Coin_Flip_Command())
