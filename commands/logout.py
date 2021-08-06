import discord
from core import client
from bot_cmd import Bot_Command, bot_commands, Bot_Command_Category


class Logout_Command(Bot_Command):
    name = "logout"

    aliases = ["quit", "q"]

    short_help = "Shuts down the bot."

    long_help = """Shuts down the bot.
    Arguments:
    `None`"""

    category = Bot_Command_Category.BOT_META

    def can_run(self, location, member):
        return member is not None and member.guild_permissions.administrator

    async def run(self, msg: discord.Message, args: str):
        await msg.channel.send("Logging out.")
        await client.logout()


bot_commands.add_command(Logout_Command())