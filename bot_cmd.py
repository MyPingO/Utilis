from core import client
from utils import fmt, std_embed
from utils.errors import ReportableError, UserCancelError

import discord
import logging
import traceback
from pathlib import Path
from enum import Enum
from importlib import import_module
from abc import ABC, abstractmethod
from typing import Union, Optional


# A Union of different types that can be used to represent a guild
GuildRepr = Union[discord.Guild, str, int]


class Bot_Command_Category(Enum):
    CLASS_INFO = "Class info"
    COMMUNITY = "Community"
    TOOLS = "Tools"
    MODERATION = "Moderation"
    BOT_META = "Bot control"
    NONE = "Misc."


class Bot_Command(ABC):
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
    aliases: list[str] = []
    category: Bot_Command_Category = Bot_Command_Category.NONE
    log: logging.Logger

    def __init_subclass__(cls) -> None:
        cls.log = logging.getLogger(f"commands.{cls.name}")

    @abstractmethod
    async def run(self, msg: discord.Message, args: str):
        """The function to be run when the command is called."""

    def get_help(
        self, user: Optional[Union[discord.User, discord.Member]], args: Optional[str]
    ) -> Union[str, discord.Embed]:
        """Gives a detailed explanation of the command for use with the help
        command. Returns either a string explaining a command or an instance
        of `discord.Embed` for the help command to display.

        Attributes
        ------------
        user: Optional[Union[discord.User, discord.Member]]
        A user to show help for or `None`. Can be used to show different help
        messages for users with different permissions.

        args: Optional[str]
        Arguments for the help command. Can be used to provide help for
        subcommands instead of the entire command.
        """
        return self.long_help

    def get_description(self) -> str:
        """Returns a brief explanation of the command for use with the help
        command.
        """
        return self.short_help

    def can_run(
        self,
        location: Optional[Union[discord.abc.Messageable, discord.Guild]],
        user: Optional[Union[discord.User, discord.Member]],
    ) -> bool:
        """Returns whether or not `user` has permission to run this command
        in `location`.

        Attributes
        ------------
        location: Optional[Union[discord.abc.Messageable, discord.Guild]],
        Where the command is being run. Can be a channel or guild, or `None`
        to represent the 'default' location.

        user: Optional[Union[discord.User, discord.Member]],
        The user that is being checked to see if they can run the command.
        Can be `None` to represent the 'default' permission for most users.
        """
        return True

    async def on_ready(self):
        """The function to be run when the bot is ready for operation."""
        pass

    def __str__(self):
        return self.name


class Bot_Commands:
    """Stores all possible commands that the bot can run.

    Attributes
    ------------
    _global_commands: dict[str, Bot_Command]
    A dictionary of all possible commands names and aliases for global commands
    that the bot can run and their corresponding commands.

    _guild_commands: dict[int, dict[str, Bot_Command]]
    A dictionary of guild ids corresponding to dictionaries of all possible
    commands names and aliases for that guild's unique commands that the bot
    can run and their corresponding commands.

    _unique_global_commands: dict[str, Bot_Command]
    A dictionary of all possible global commands without any aliases in the
    keys.

    _unique_guild_commands: dict[int, dict[str, Bot_Command]]
    A dictionary of guild ids corresponding to dictionaries of all possible
    commands unique to that guild without any aliases in the keys.
    """

    _global_commands: dict[str, Bot_Command] = {}
    _guild_commands: dict[int, dict[str, Bot_Command]] = {}

    _unique_global_commands: dict[str, Bot_Command] = {}
    _unique_guild_commands: dict[int, dict[str, Bot_Command]] = {}

    def _get_guild_id(self, guild: GuildRepr) -> int:
        if isinstance(guild, discord.Guild):
            return guild.id
        else:
            return int(guild)

    def _get_guild(self, guild: Optional[GuildRepr]) -> Optional[discord.Guild]:
        if guild is not None:
            if isinstance(guild, discord.Guild):
                return guild
            guild = int(guild)
            for g in client.guilds:
                if g.id == guild:
                    return g
        return None

    def _load_all_commands(self, path: Path = Path("commands"), indent=2) -> None:
        """Loads all commands in a directory."""

        print("Loading commands.")
        for file in path.iterdir():
            # Don't load files or directories that start with an underscore
            if file.name[0] != "_":
                if file.is_dir():
                    print(f"{' '*indent}Loading module '{file.name}'.")
                    self._load_all_commands(file, indent=(indent + 2))
                else:
                    if file.suffix == ".py":
                        self._load_command(file, indent)
        print("Done.")

    def _load_command(self, path: Path, indent=2) -> None:
        """Loads a Python file."""

        module_name = path.as_posix()[: -len(path.suffix)].replace("/", ".")
        print(f"{' '*indent}Loading {module_name}")

        c = import_module(module_name)

    def add_command(
        self, command: Bot_Command, guild: Optional[GuildRepr] = None
    ) -> None:
        """Adds a command to the list of the bot's commands. If `guild` is
        `None` then `command` will be a global command that can be accessed
        from any guild. If `guild` is a `Guild`, then `command` will be local
        to the guild.
        """
        if not command.name:
            raise ValueError("Tried to add command with no name.")

        lower_cmd_name = command.name.casefold()

        if guild is None:
            if self.has_command(lower_cmd_name):
                raise ValueError(f"A command of name {command.name} was already added.")
            for alias in command.aliases:
                if self.has_command(alias):
                    raise ValueError(f"A command of name {alias} was already added.")

            commands = self._global_commands
            unique_commands = self._unique_global_commands
        else:
            g_id = self._get_guild_id(guild)
            if g_id is None:
                raise ValueError(f"Could not find guild {guild}.")

            if g_id not in self._guild_commands:
                self._guild_commands[g_id] = {}
            if g_id not in self._unique_guild_commands:
                self._unique_guild_commands[g_id] = {}

            commands = self._guild_commands[g_id]
            unique_commands = self._unique_guild_commands[g_id]

            if self.is_global_command(lower_cmd_name):
                raise ValueError(
                    f"A global command of name {command.name} was already added."
                )
            if lower_cmd_name in commands:
                raise ValueError(
                    f"A command of name {command.name} was already added to {guild}."
                )
            for alias in command.aliases:
                if self.is_global_command(alias):
                    raise ValueError(
                        f"A global command of name {alias} was already added."
                    )
                if alias.casefold() in commands:
                    raise ValueError(
                        f"A command of name {alias} was already added to {guild}."
                    )

        commands[lower_cmd_name] = command
        unique_commands[lower_cmd_name] = command

        for alias in command.aliases:
            commands[alias.casefold()] = command

    def remove_command(
        self, command: Union[Bot_Command, str], guild: Optional[GuildRepr] = None
    ) -> None:
        """Removes a `command` from a `guild`, or tries to remove `command`
        globally if `guild` is `None`.
        """
        cmd: Optional[Bot_Command]
        if isinstance(command, Bot_Command):
            cmd = command
        else:
            cmd = self.get_command(command, guild)

        g = self._get_guild(guild)
        if guild is not None and g is None:
            raise ValueError(f"No guild {guild} found.")

        if cmd is None:
            if g is None:
                raise ValueError(f"No global command {command} found.")
            else:
                raise ValueError(
                    f"No command {command} found in guild {g.name} [{g.id}]."
                )

        if self.is_global_command(cmd):
            if g is not None:
                raise ValueError(
                    f"{cmd.name} is a global command and can not be removed from guild {g.name} [{g.id}]."
                )
            del self._global_commands[cmd.name]
            del self._unique_global_commands[cmd.name]
            for alias in cmd.aliases:
                del self._global_commands[alias]
        else:
            if g is None:
                raise ValueError(f"No global command {cmd} found.")
            if cmd not in self._guild_commands[g.id].values():
                raise ValueError(f"No command {cmd} found.")
            del self._guild_commands[g.id][cmd.name]
            del self._unique_guild_commands[g.id][cmd.name]
            for alias in cmd.aliases:
                del self._guild_commands[g.id][alias]

    def get_global_commands(self) -> list[Bot_Command]:
        """Returns a list of all global commands."""
        return list(self._unique_global_commands.values())

    def get_commands_in(
        self, guild: Optional[GuildRepr] = None, include_global_commands: bool = True
    ) -> list[Bot_Command]:
        """Returns a list of all commands that can be used in `guild`. If
        `guild` is `None`, only global commands are returned.
        `include_global_commands` controls whether to include global commands
        in the return list or only guild commands.
        """
        if guild is None:
            if include_global_commands:
                return self.get_global_commands()
            else:
                return []

        if guild is not None:
            g_id = self._get_guild_id(guild)
        else:
            g_id = None
        if g_id is not None and g_id in self._unique_guild_commands:
            if include_global_commands:
                return [
                    *self._unique_global_commands.values(),
                    *self._unique_guild_commands[g_id].values(),
                ]
            else:
                return list(self._unique_guild_commands[g_id].values())
        else:
            if include_global_commands:
                return list(self._unique_global_commands.values())
            else:
                return []

    def get_all_commands(self) -> set[Bot_Command]:
        """Returns all bot commands registered in all guilds."""

        return {
            *self._unique_global_commands.values(),
            *(c for g in self._unique_guild_commands.values() for c in g.values()),
        }

    def is_global_command(self, command: Union[Bot_Command, str]) -> bool:
        """Returns whether or not a command is a global command."""

        if isinstance(command, str):
            return command.casefold() in self._global_commands
        else:
            return command in self._global_commands.values()

    def has_command(self, command: Union[Bot_Command, str]) -> bool:
        """Returns whether a command was added either globally or in a guild.
        If `command` is a `Bot_Command`, then `has_command` only looks for
        that exact command. If `command` is a `str`, then `has_command` looks
        for any command with `command` as a name or alias.
        """
        if isinstance(command, Bot_Command):
            return command in self.get_all_commands()
        else:
            return command.casefold() in (
                cmd.name.casefold() for cmd in self.get_all_commands()
            ) or command.casefold() in (
                a.casefold() for cmd in self.get_all_commands() for a in cmd.aliases
            )

    def registered_in(self, command: Union[Bot_Command, str]) -> list[int]:
        """Returns a list of guild ids in which a command is registered. This
        is the ids of every guild the bot is in if a command is global. If
        `command` is a `Bot_Command`, then `registerd_in` only looks for that
        exact command. If `command` is a `str`, then `registerd_in` looks for
        any command with `command` as a name or alias.
        """
        if self.is_global_command(command):
            return [g.id for g in client.guilds]
        elif isinstance(command, Bot_Command):
            return [
                g_id
                for g_id, cmds in self._unique_guild_commands.items()
                if command in cmds.values()
            ]
        else:
            return [
                g_id for g_id, cmds in self._guild_commands.items() if command in cmds
            ]

    def get_command(
        self, command: str, guild: Optional[GuildRepr]
    ) -> Optional[Bot_Command]:
        """Gets a `Bot_Command` with the name or alias `command`. If `guild`
        is `None`, `get_command` only checks global commands for a command
        named `command`. If `guild` represents a guild, then `get_command`
        also searches in the local commands for that guild.

        Returns `None` if no command was found.
        """
        command = command.casefold()
        try:
            return self._global_commands[command]
        except KeyError:
            try:
                if guild is not None:
                    return self._guild_commands[self._get_guild_id(guild)][command]
            except KeyError:
                pass
        return None

    def can_run(
        self,
        command: Union[Bot_Command, str],
        location: Optional[Union[discord.abc.Messageable, discord.Guild]],
        member: Optional[Union[discord.User, discord.Member]],
    ) -> bool:
        """A wrapper function that calls a command's `can_run` method and
        returns `False` if an exception was thrown.
        """
        try:
            cmd: Optional[Bot_Command]
            if not isinstance(command, Bot_Command):
                if isinstance(location, discord.Guild):
                    cmd = self.get_command(command, location)
                elif isinstance(location, discord.TextChannel):
                    cmd = self.get_command(command, location.guild)
                else:
                    cmd = self.get_command(command, None)
            else:
                cmd = command
            if cmd is None:
                return False

            return cmd.can_run(location, member)
        except Exception:
            # If the commands can_run method does not successfully return,
            # assume the command can not be run. This prevents bugs from
            # allowing access to commands that should not be allowed to be run.
            return False

    async def call(self, command: Bot_Command, msg: discord.Message, args: str) -> None:
        """A wrapper function that calls a command and logs it, logging and
        sending an error message to a message's channel if it fails.
        """
        try:
            log_action = f'called command "{command}" '
            if args:
                log_action += f"with args: {fmt.escape_newlines(args)}"
            else:
                log_action += f"without args"
            command.log.info(
                fmt.get_user_log(log_action, msg.author, msg.channel, msg.guild)
            )
            await command.run(msg, args)
        except UserCancelError as e:
            if e.log:
                self.log_error(command, e)
            await self.send_cancel_message(msg.channel, command, str(e), msg.author)
            if e.log:
                raise e
        except ReportableError as e:
            if e.log:
                self.log_error(command, e)
            await self.send_error_message(msg.channel, command, str(e), msg.author)
            if e.log:
                raise e
        except Exception as e:
            self.log_error(command, e)
            await self.send_error_message(
                msg.channel,
                command,
                fmt.format_maxlen(
                    "An internal error occured while executing `{}`", command
                ),
                msg.author,
            )
            raise e

    def log_error(self, command: Bot_Command, e: Exception) -> None:
        """Logs an error raised while executing a command."""
        command.log.error(
            f"{type(e).__name__}: {e}\n"
            + "".join(traceback.format_exception(None, e, e.__traceback__))
        )

    async def send_error_message(
        self,
        channel: discord.abc.Messageable,
        command: Bot_Command,
        description: str,
        author: Optional[Union[discord.User, discord.Member]],
    ) -> Optional[discord.Message]:
        """Sends an error message, printing and raising any errors that occur
        in the process.
        """
        if not client.is_closed():
            try:
                return await std_embed.send_error(
                    channel,
                    title=fmt.format_maxlen("Error executing {}", command.name.upper()),
                    description=description,
                    author=author,
                )
            except Exception as e:
                print("Error sending error message:", e, sep="\n")
                raise e
        else:
            return None

    async def send_cancel_message(
        self,
        channel: discord.abc.Messageable,
        command: Bot_Command,
        description: str,
        author: Optional[Union[discord.User, discord.Member]],
    ) -> Optional[discord.Message]:
        """Sends an error message, printing and raising any errors that occur
        in the process.
        """
        if not client.is_closed():
            try:
                return await std_embed.send_success(
                    channel,
                    title=fmt.format_maxlen(
                        "Cancelled command {}", command.name.upper()
                    ),
                    description=description,
                    author=author,
                )
            except Exception as e:
                print("Error sending error message:", e, sep="\n")
                raise e
        else:
            return None


bot_commands = Bot_Commands()
bot_commands._load_all_commands()
