from core import client
from utils import format_max_utf16_len_string

import discord
from pathlib import Path
from importlib import import_module
from typing import Union, Optional


# A Union of different types that can be used to represent a guild
Guild = Union[discord.Guild, str, int]


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

    aliases: list[str] = []

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

    def _get_guild_id(self, guild: Guild) -> int:
        if isinstance(guild, discord.Guild):
            return guild.id
        else:
            return int(guild)

    def _get_guild(self, guild: Optional[Guild]) -> Optional[discord.Guild]:
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
                        try:
                            self._load_command(file, indent)
                        except AttributeError as e:
                            print(f"{' ' * (indent + 2)}Error:", e)
        print("Done.")

    def _load_command(self, path: Path, indent=2) -> None:
        """Loads a Python file."""

        module_name = path.as_posix()[: -len(path.suffix)].replace("/", ".")
        print(f"{' '*indent}Loading {module_name}")

        c = import_module(module_name)

    def add_command(self, command: Bot_Command, guild: Optional[Guild] = None) -> None:
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
        self, command: Union[Bot_Command, str], guild: Optional[Guild] = None
    ) -> None:
        """Removes a `command` from a `guild`, or tries to remove `command`
        globally if `guild` is `None`.
        """
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

    def get_commands_in(
        self, guild: Optional[Guild] = None, include_global_commands: bool = True
    ) -> list[Bot_Command]:
        """Returns a list of all commands that can be used in `guild`. If
        `guild` is `None`, only global commands are returned.
        `include_global_commands` controls whether to include global commands
        in the return list or only local commands.
        """
        if guild is None:
            if include_global_commands:
                return list(self._unique_global_commands.values())
            else:
                return []

        g_id = self._get_guild_id(guild)
        if g_id in self._unique_guild_commands:
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

    def get_all_commands(self) -> list[Bot_Command]:
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
        self, command: str, guild: Optional[Guild]
    ) -> Optional[Bot_Command]:
        """Gets a `Bot_Command` with the name or alias `command`. If `guild`
        is `None`, `get_command` only checks global commands for a command
        named `command`. If `guild` is a `Guild`, then `get_command` also
        searches in the local commands for that `Guild`.

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
        location: Optional[Union[discord.TextChannel, discord.Guild]],
        member: Optional[discord.Member],
    ) -> bool:
        """A wrapper function that calls a command's `can_run` method and
        returns `False` if an exception was thrown.
        """
        try:
            if not isinstance(command, Bot_Command):
                command = self.get_command(command, self._location_to_guild(location))
            if command is None:
                return False

            return command.can_run(location, member)
        except Exception:
            # If the commands can_run method does not successfully return,
            # assume the command can not be run. This prevents bugs from
            # allowing access to commands that should not be allowed to be run.
            return False

    async def call(self, command: Bot_Command, msg: discord.Message, args: str) -> None:
        """A wrapper function that calls a command and sends an error message
        to a message's channel if it fails.
        """
        try:
            await command.run(msg, args)
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
bot_commands._load_all_commands()