import discord
from typing import Union, Optional

from cmd import Bot_Command, bot_commands
from utils import utf16_len, utf16_embed_len, format_max_utf16_len_string


class Help_Command(Bot_Command):
    name = "help"

    short_help = "Gives information about the bot's commands. Specifying what command you need help with by doing `help <command>` will show you more details about that command"

    long_help = """Gives information about the bot's commands.
    Arguments:
    `command`
    `None`
    """

    async def run(self, msg: discord.Message, args: str):
        if args:
            # If a command to get help for was specified, try to get help for
            # that command
            if " " not in args:
                await self.get_command_info(args, msg.channel, msg.author, None)
            else:
                cmd_name, help_args = args.split(" ", 1)
                await self.get_command_info(
                    cmd_name, msg.channel, msg.author, help_args
                )
        else:
            # Otherwise, print a list of all commands with a short description

            help_embed = discord.Embed(
                title="Commands",
                description="Run `help <command>` to get detailed information about a specific command.",
            )

            # Get all of the commands in alphabetical order and add them to
            # the embed.
            for cmd in sorted(
                bot_commands.get_commands_in(msg.guild), key=lambda c: c.name.casefold()
            ):
                # Make sure that the command can be run by the user
                if bot_commands.can_run(cmd, msg.channel, msg.author):
                    # If the command name and its help info can't fit in the
                    # embed, send the embed and create a new one
                    if (
                        utf16_embed_len(help_embed)
                        + utf16_len(cmd.name)
                        + utf16_len(cmd.short_help)
                        > 6000
                    ):
                        await msg.channel.send(embed=help_embed)
                        help_embed = discord.Embed(title="Commands (cont.)")

                    help_embed.add_field(
                        name=cmd.name, value=cmd.short_help, inline=False
                    )

            await msg.channel.send(embed=help_embed)

    async def get_command_info(
        self,
        command: Union[Bot_Command, str],
        channel: discord.TextChannel,
        member: Optional[discord.Member] = None,
        args: Optional[str] = None,
    ):
        """Sends a help message to `channel` for a specified `command`.

        Attributes
        ------------
        command: Union[Bot_Command, str]
        A command or the name of a command to display help for. If an invalid
        command name or a command that `member` does not have permission to run
        in `channel` is passed, an error message will be sent.

        channel: discord.TextChannel
        The channel to send the help message to. The bot also makes sure that
        `member` has permission to run `command` in `channel`.

        member: Optional[discord.Member]
        The member to get help for. Can be `None` to represent a 'default'
        member. `member` is passed to `command`'s `get_help` method, and also
        is used to check if `member` has permission to run `command` in
        `channel`.

        args: Optional[str]
        The arguments passed to the help command. These can be used to get
        help for a subcommand instead of all of `command`.
        """
        # If the name of a command was passed, try to find a command with that
        # name or alias
        if isinstance(command, str):
            cmd = bot_commands.get_command(command, channel.guild)
        else:
            cmd = command

        # Check to see that a valid command was passed or found
        if not isinstance(cmd, Bot_Command):
            error_message = format_max_utf16_len_string(
                "Could not find the command `{}`", command
            )
            await channel.send(error_message, delete_after=7)
            return

        # Make sure the member can run the command
        if not cmd.can_run(channel, member):
            error_message = format_max_utf16_len_string(
                "You do not have permission to run `{}` here.", cmd.name
            )
            await channel.send(error_message, delete_after=7)
            return

        # Remove whitespace from start and end of args
        if isinstance(args, str):
            args = args.strip()

        # Get help info about the command to display
        cmd_help = cmd.get_help(member, args)

        # If the command returned its own custom help embed, send it
        if isinstance(cmd_help, discord.Embed):
            await channel.send(embed=cmd_help)
            return
        # Otherwise, create an embed for the command and send it
        help_embed = discord.Embed(title=f"__{cmd}__")
        help_embed.description = cmd_help

        # Add all of the commands aliases to the help embed if it has any
        if cmd.aliases:
            help_embed.add_field(
                name="__*Aliases:*__\n",
                value="\n".join(
                    (alias for alias in sorted(cmd.aliases, key=lambda a: a.casefold()))
                ),
            )

        await channel.send(embed=help_embed)


help_cmd = Help_Command()
bot_commands.add_command(help_cmd)