import discord
from core import client
from cmd import Bot_Command


class Logout_Command(Bot_Command):
    name = "logout"

    aliases = ["quit", "q"]

    short_help = "Shuts down the bot."

    long_help = """Shuts down the bot.
    Arguments:
    `None`"""

    async def run(self, msg: discord.Message, args: str):
        if msg.author.guild_permissions.administrator:
            await msg.channel.send("Logging out.")
            await client.logout()
        else:
            await msg.channel.send(
                "Must be an administrator to use this command.", delete_after=7
            )


command = Logout_Command()