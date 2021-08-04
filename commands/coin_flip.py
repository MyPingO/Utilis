from bot_cmd import Bot_Command
import random
import discord


class coinF_Command(Bot_Command):
    name = "coin_flip"

    short_help = "Replies with a random coin flip (heads or tails)"

    long_help = """Replies with a random coin flip (heads or tails)!
    Arguments:
    `text`
    `None`
    """

    async def run(self, msg: discord.Message, args: str):
        if random.randint(1,2) == 1:
            print("Heads")
            await msg.channel.send("Heads")
        else:
            print("Tails")
            await msg.channel.send("Tails")

            """else print(f'Tails')"""
            """print(f'pong: "{single_line_args}"')"""



command = coinF_Command()