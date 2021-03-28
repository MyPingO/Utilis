from cmd import Bot_Command

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

    async def run(self, msg: discord.Message, args: str):
        random.seed()
        choice = f'{random.choice(self.coin)}'          
        print(choice)
        await msg.channel.send(choice)

command = Coin_Flip_Command()
