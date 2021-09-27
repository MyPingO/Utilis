import discord
import asyncio
from core import client
from bot_cmd import Bot_Command, bot_commands, Bot_Command_Category
from utils import std_embed


class Logout_Command(Bot_Command):
    name = "logout"

    aliases = ["quit", "q"]

    short_help = "Shuts down the bot."

    long_help = """Shuts down the bot.
    Arguments:
    `None`"""

    category = Bot_Command_Category.BOT_META

    async def can_run(self, location, member):
        if member is not None:
            appinfo = await client.application_info()
            if appinfo.owner.id == member.id:
                return True
            if appinfo.team is not None:
                return any((member.id == m.id for m in appinfo.team.members))
        return False

    async def run(self, msg: discord.Message, args: str):
        await std_embed.send_success(
            msg.channel, title="Logging out", author=msg.author
        )
        await client.close()


bot_commands.add_command(Logout_Command())
