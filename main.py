import discord
from pathlib import Path

from core import client
from cmd import bot_commands

bot_prefix = "!"


def starts_with_mention(content: str) -> bool:
    """Returns whether or not the bot was mentioned at the start of the
    message.
    """

    return content.startswith(client.user.mention) or content.startswith(
        f"<@!{client.user.id}>"
    )


def remove_prefix(content: str) -> str:
    """Removes the bot prefix or bot's mention string from the start of a
    string.
    """

    if content.startswith(bot_prefix):
        return content[len(bot_prefix) :].strip()
    elif starts_with_mention(content):
        return content[content.index(">") + 1 :].strip()
    else:
        raise ValueError(f"String '{content}' does not start with the bot's prefix.")


def get_command(content: str) -> str:
    """Returns the command name from a message's text.
    Assumes that the bot prefix has been removed.
    """

    if " " in content:
        return content.split(" ")[0].casefold()
    else:
        return content.casefold()


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
    if msg.author != client.user:
        if msg.content.startswith(bot_prefix) or starts_with_mention(msg.content):
            clean_content = remove_prefix(msg.content)
            command = get_command(clean_content)

            if not command:
                await bot_commands.call("help", msg, "")
            elif bot_commands.has_command(command):
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
