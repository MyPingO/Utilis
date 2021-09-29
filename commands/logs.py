import discord
from pathlib import Path
from core import client
from bot_cmd import Bot_Command, bot_commands, Bot_Command_Category
from utils import errors, get, std_embed

_max_log_history = len(get.User_Selection_Message.default_selection_reactions)


class Logs_Command(Bot_Command):
    name = "logs"
    aliases = ["log"]
    short_help = "Downloads the bot's logs."
    long_help = (
        f"Downloads the bot's logs. Only the {_max_log_history} latest logs "
        "are available for download."
    )

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
        log_path = Path("data/bot/logs")
        if log_path.exists():
            log_files = sorted(log_path.iterdir(), key=lambda f: f.name, reverse=True)[
                :_max_log_history
            ]
            if log_files:
                send_files = await get.selections(
                    msg.channel,
                    log_files,
                    lambda f: f.name,
                    msg.author,
                    "Logs",
                    "Choose log files to send",
                )
                if not send_files:
                    await std_embed.send_success(
                        msg.channel,
                        title="Logs",
                        description="Cancelled sending log files",
                        author=msg.author,
                    )
                else:
                    send_logs_embed = std_embed.get_success(
                        title="Logs", author=msg.author
                    )
                    await msg.channel.send(
                        embed=send_logs_embed,
                        files=[discord.File(f) for f in send_files],
                    )
                return
        await std_embed.send_info(
            msg.channel,
            title="Logs",
            description="No log files to send",
            author=msg.author,
        )


bot_commands.add_command(Logs_Command())
