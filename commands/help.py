import discord
from typing import Union, Optional

from cmd import Bot_Command, bot_commands


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
            await self.get_command_info(args.casefold(), msg.channel, msg.author)
        else:
            # Otherwise, print a list of all commands with a short description

            help_embed = discord.Embed(
                title="Commands",
                description="Run `help <command>` to get detailed information about a specific command.",
            )

            # Get all of the commands in alphabetical order
            commands = list(bot_commands.unique_commands.keys())
            commands.sort()

            # Add all of the commands to the embed
            for cmd_name in commands:
                # Make sure that the command can be run by the user
                if bot_commands.can_run(cmd_name, msg.channel, msg.author):
                    cmd = bot_commands.unique_commands[cmd_name]
                    # If the command name and its help info can't fit in the
                    # embed, send the embed and create a new one
                    if len(help_embed) + len(cmd_name) + len(cmd.short_help) > 6000:
                        await msg.channel.send(embed=help_embed)
                        help_embed = discord.Embed(title="Commands (cont.)")

                    help_embed.add_field(
                        name=cmd_name, value=cmd.short_help, inline=False
                    )

            await msg.channel.send(embed=help_embed)

    async def get_command_info(
        self,
        command: Union[Bot_Command, str],
        channel: discord.TextChannel,
        member: Optional[discord.Member],
    ):
        # If the name of a command was passed, try to find a command with that
        # name or alias
        if isinstance(command, str):
            if bot_commands.has_command(command):
                command = bot_commands.get_command(command)

        # Check to see that a valid command was passed or found
        if not isinstance(command, Bot_Command):
            await channel.send(
                f"Could not find the command `{command}`.", delete_after=7
            )
            return

        # Make sure the member can run the command
        if not command.can_run(channel, member):
            error_message = f"You do not have permission to run `{command.name}` here."
            if len(error_message) > 2000:
                error_message = f"You do not have permission to run `{command.name[:2000-44]}...` here."
            await channel.send(error_message, delete_after=7)
            return

        # Get help info about the command to display
        cmd_help = command.get_help(member)

        # If the command returned its own custom help embed, send it
        if isinstance(cmd_help, discord.Embed):
            await channel.send(embed=cmd_help)
            return
        # Otherwise, create an embed for the command and send it
        help_embed = discord.Embed(title=f"__{command.name}__")
        help_embed.description = cmd_help

        # Add all of the commands aliases to the help embed if it has any
        if command.aliases:
            cmd_aliases = command.aliases.copy()
            cmd_aliases.sort()
            help_embed.add_field(
                name="__*Aliases:*__\n",
                value="\n".join((alias for alias in cmd_aliases)),
            )

        await channel.send(embed=help_embed)


command = Help_Command()