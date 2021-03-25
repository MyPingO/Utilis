import discord
from pathlib import Path

from core import client
from cmd import bot_commands

bot_prefix = "!"

def remove_prefix(content: str) -> str:
    """Removes the bot prefix from the start of a string.
    Assumes that the string starts the bot prefix.
    """

    return content[len(bot_prefix) :]


def get_command(content: str) -> str:
    """Returns the command name from a message's text.
    Assumes that the bot prefix has been removed.
    """

    if " " in content.strip():
        return content.strip().split(" ")[0]
    else:
        return content.strip()


def get_args(content: str, command: str) -> str:
    """Returns the command arguments from a message's text.
    Assumes that the bot prefix has been removed.
    """
    return content.strip()[len(command) :].strip()


@client.event
async def on_connect():
    print("------------\n Connected ")


@client.event
async def on_ready():
    print("   Ready   \n------------\n")


@client.event
async def on_message(msg: discord.Message):
    if msg.content.startswith(bot_prefix):
        clean_content = remove_prefix(msg.content)
        command = get_command(clean_content)

        if bot_commands.has_command(command):
            args = get_args(clean_content, command)
            await bot_commands.call(command, msg, args)
        else:
            await msg.channel.send(f"No command `{command}`.", delete_after=7)


def start_bot() -> None:
    with Path("data/token.txt").open() as token:
        client.run(token.read())


if "__main__" == __name__:
    start_bot()
    print("------------\nDisconnected\n------------")
