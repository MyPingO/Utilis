from core import client
from util import format_max_utf16_len_string

import discord
from pathlib import Path
from importlib import import_module
from typing import Union, Optional


class Bot_Command:
    """Represents a command the bot can run.

    Attributes
    ------------
    name: str
    The name of the command. This can be used to run the command in Discord by
    putting the bot Prefix before the name at the start of a message. Each
    command's name must be unique.

    short_help: str
    A short help string that briefly describes what the command does.

    long_help: str
    A long help string that describes what the command does and how to use it.

    aliases: list[str]
    A list of alternate callable command names for a command. These aliases
    will allow the command to be called in Discord by putting the bot's prefix
    in front of an alias. Multiple commands can not have the same alias.
    """

    name: str = ""

    short_help: str = "No info on this command."

    long_help: str = "No information available for this command."

    def get_help(
        self, member: Optional[discord.Member], args: Optional[str]
    ) -> Union[str, discord.Embed]:
        """Gives a detailed explanation of the command for use with the help
        command. Returns either a string explaining a command or an instance
        of `discord.Embed` for the help command to display.

        Attributes
        ------------
        member: Optional[discord.Member]
        A member to show help for or `None`. Can be used to show different help
        messages for members with different permissions.

        args: Optional[str]
        Arguments for the help command. Can be used to provide help for
        subcommands instead of the entire command.
        """
        return self.long_help

    def can_run(
        self,
        location: Optional[Union[discord.TextChannel, discord.Guild]],
        member: Optional[discord.Member],
    ) -> bool:
        """Returns whether or not `member` has permission to run this command
        in `location`.

        Attributes
        ------------
        location: Optional[Union[discord.TextChannel, discord.Guild]]
        Where the command is being run. Can be a channel or guild, or `None`
        to represent the 'default' location.

        member: Optional[discord.Member]
        The member that is being checked to see if they can run the command.
        Can be `None` to represent the 'default' permission for most users.
        """
        return True

    async def run(self, msg: discord.Message, args: str):
        """The function to be run when the command is called."""
        pass

    async def on_ready(self):
        """The function to be run when the bot is ready for operation."""
        pass

    aliases: list[str] = []


class Bot_Commands:
    """Stores all possible commands that the bot can run.

    Attributes
    ------------
    commands: dict[`str`, `Bot_Command`]
    A dictionary of all possible commands names that the bot can run and their
    corresponding commands.

    unique_commands: dict[`str`, `Bot_Command`]
    A dictionary of all commands the bot can run, without any aliases.
    """

    commands: dict[str, Bot_Command] = {}

    unique_commands: dict[str, Bot_Command] = {}

    def load_all_commands(self, path: Path = Path("commands"), indent=2) -> None:
        """Loads all commands in a directory."""

        print("Loading commands.")
        for file in path.iterdir():
            # Don't load files or directories that start with an underscore
            if file.name[0] != "_":
                if file.is_dir():
                    print(f"{' '*indent}Loading module '{file.name}'.")
                    self.load_all_commands(file, indent=(indent + 2))
                else:
                    if file.suffix == ".py":
                        try:
                            self.load_command(file, indent)
                        except AttributeError as e:
                            print(f"{' ' * (indent + 2)}Error:", e)
        print("Done.")

    def load_command(self, path: Path, indent=2) -> None:
        """Loads a command from a Python file.
        Expects the file to have a global variable `command` that is an instance
        of a subclass of `Bot_Command`, and/or a global variable `commands` that
        is a list of instances that are subclasses of `Bot_Command`.
        """

        module_name = path.as_posix()[: -len(path.suffix)].replace("/", ".")
        print(f"{' '*indent}Loading {module_name}")

        c = import_module(module_name)

        loaded_commands = False
        if hasattr(c, "command"):
            self.add_command(c.command)
            loaded_commands = True
        if hasattr(c, "commands"):
            for command in c.commands:
                self.add_command(command)
            loaded_commands = True
        if not loaded_commands:
            raise AttributeError(f"Could not find command(s) in file {module_name}.")

    def add_command(self, command: Bot_Command) -> None:
        """Adds a command to the list of the bot's commands."""

        if not command.name:
            raise ValueError("Tried to add command with no name.")

        lower_cmd_name = command.name.casefold()

        if lower_cmd_name not in self.unique_commands:
            self.commands[lower_cmd_name] = command
            self.unique_commands[lower_cmd_name] = command
        else:
            raise ValueError(
                f"Tried to add command '{command.name}' but command '{self.commands[lower_cmd_name].name}' already had alias '{lower_cmd_name}'."
            )

        for alias in [a.casefold() for a in command.aliases]:
            if alias not in self.commands:
                self.commands[alias] = command
            else:
                raise ValueError(
                    f"Tried to assign alias '{alias}' to command '{command.name}' already assigned to command '{self.commands[alias].name}'."
                )

    def has_command(self, command: str) -> bool:
        return command in self.commands

    def get_command(self, command: str) -> Bot_Command:
        return self.commands[command]

    def can_run(
        self,
        command: str,
        location: Optional[Union[discord.TextChannel, discord.Guild]],
        member: Optional[discord.Member],
    ) -> bool:
        try:
            return self.commands[command].can_run(location, member)
        except:
            # If the commands can_run method does not successfully return,
            # assume the command can not be run. This prevents bugs from
            # allowing access to commands that should not be allowed to be run.
            return False

    async def call(self, command: str, msg: discord.Message, args: str) -> None:
        try:
            await self.commands[command].run(msg, args)
        except Exception as e:
            if not client.is_closed():
                try:
                    error_message = format_max_utf16_len_string(
                        "Error executing `{}`", command
                    )
                    await msg.channel.send(error_message, delete_after=7)
                except Exception as e2:
                    print("Error sending error message:", e2, sep="\n")
            raise e


bot_commands = Bot_Commands()
bot_commands.load_all_commands()