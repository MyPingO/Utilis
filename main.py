import os

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)


import discord
import asyncio
import logging
from pathlib import Path

from core import client
from bot_cmd import bot_commands
from utils import fmt

bot_prefix = "!"

log = logging.getLogger("main")


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


def get_command_name(content: str) -> str:
    """Returns the command name from a message's text.
    Assumes that the bot prefix has been removed.
    """
    if " " in content:
        return content.split(" ")[0].casefold()
    else:
        return content.casefold()


def get_args(content: str, cmd_name: str) -> str:
    """Returns the command arguments from a message's text.
    Assumes that the bot prefix has been removed.
    """
    return content.strip()[len(cmd_name) :].strip()


async def assign_roles(msg: discord.Message):
    """Adds or removes specified roles from the message author.
    Multiple roles can be added/removed in one message if they are separated by commas.

    Parameters
    -----------
    msg: discord.Message
    The message containing the roles the author wants to assign or remove from themself.
    Roles are separated by commas.
    Role names are preceded by a `+` or `-` to specify whether they should be
    added or removed.
    """

    if not isinstance(msg.author, discord.Member):
        raise TypeError("msg.author must be a member.")

    # split the message into a list of individual roles
    arr = msg.content.split(", ")
    for role in arr:
        # get role name
        name = role.strip()[1:]

        # determine whether the role should be assigned or removed
        if role.startswith("+"):
            try:
                r = discord.utils.get(msg.author.guild.roles, name=name)
                if r is not None:
                    await msg.author.add_roles(r)
                    return
            except (discord.HTTPException, discord.Forbidden):
                pass
            print(f"no role called {role[1:]}")
        elif role.startswith("-"):
            try:
                r = discord.utils.get(msg.author.guild.roles, name=name)
                if r is not None:
                    await msg.author.remove_roles(r)
                    return
            except (discord.HTTPException, discord.Forbidden):
                pass
            print(f"{msg.author} doesn't have the role {role[1:]}")


@client.event
async def on_connect():
    print("------------\n Connected ")


@client.event
async def on_ready():
    print("   Ready   \n------------\n")
    # Runs the on_ready co-routine for every command.
    await asyncio.gather(*(c.on_ready() for c in bot_commands.get_all_commands()))


@client.event
async def on_message(msg: discord.Message):
    # Check to see if the message is not from a bot
    if not msg.author.bot and msg.author != client.user:
        # Check to see if the message is trying to run a command
        if msg.content.startswith(bot_prefix) or starts_with_mention(msg.content):
            # Get the command the member is trying to run
            clean_content = remove_prefix(msg.content)
            cmd_name = get_command_name(clean_content)

            if not cmd_name:
                # If the use did not specify a command, call the help command
                # to show a list of all commands.
                help_command = bot_commands.get_command("help", msg.guild)
                if help_command is not None:
                    await bot_commands.call(help_command, msg, "")
                else:
                    # If there is no help command, send an error message instead
                    await msg.channel.send("No command specified.", delete_after=7)
            else:
                command = bot_commands.get_command(cmd_name, msg.guild)
                if command is not None:
                    if bot_commands.can_run(command, msg.channel, msg.author):
                        # If the command exists and the member can run it, run the
                        # command
                        args = get_args(clean_content, cmd_name)
                        await bot_commands.call(command, msg, args)
                    else:
                        # If the command exists but the member can not run it, send
                        # an error message
                        command.log.info(
                            fmt.get_user_log(
                                f'tried to call command "{command}" with message: {fmt.escape_newlines(msg.content)}',
                                msg.author,
                                msg.channel,
                                msg.guild,
                            )
                        )
                        error_message = fmt.format_maxlen(
                            "You do not have permission to run `{}` here.", cmd_name
                        )
                        await msg.channel.send(
                            error_message,
                            delete_after=7,
                        )
                else:
                    # If the command does not exist, send an error message
                    log.info(
                        fmt.get_user_log(
                            f'tried to call command "{cmd_name}" with message: {fmt.escape_newlines(msg.content)}',
                            msg.author,
                            msg.channel,
                            msg.guild,
                        )
                    )
                    error_message = fmt.format_maxlen("No command `{}`", cmd_name)
                    await msg.channel.send(
                        error_message,
                        delete_after=7,
                    )
        # assigning roles
        # only if message is in designated role channel
        elif msg.channel.id == 846427205911052349:
            # deletes messages sent in designated role channel after a delay
            await msg.delete(delay=5)
            # if message has prefix, call roles
            if msg.content.startswith("+") or msg.content.startswith("-"):
                # assign role
                await assign_roles(msg)


# allows members to pin messages on their own by reaching a reaction goal
@client.event
async def on_reaction_add(reaction: discord.Reaction, user: discord.Member):
    if reaction.emoji == "📌" and reaction.count >= 3:
        await reaction.message.pin()


def start_bot() -> None:
    token_path = Path("data/token.txt")
    placeholder_token = "Bot token goes here"
    missing_token_message = (
        f"Error: did not find a bot token at {token_path}."
        + "\nFor information on how to get a bot token, see https://discordpy.readthedocs.io/en/stable/discord.html"
    )
    if not token_path.exists():
        token_path.parent.mkdir(parents=True, exist_ok=True)
        with token_path.open("w") as token_file:
            token_file.write(placeholder_token)
        print(missing_token_message)
        return

    with token_path.open("r") as token_file:
        token = token_file.read()
        if token != placeholder_token:
            client.run(token)
        else:
            print(missing_token_message)


if "__main__" == __name__:
    start_bot()
    print("------------\nDisconnected\n------------")
