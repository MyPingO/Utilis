import discord
from typing import Union, Optional

from bot_cmd import Bot_Command, bot_commands, Bot_Command_Category
import utils


class Help_Command(Bot_Command):
    name = "help"

    short_help = "Gives information about the bot's commands. Specifying what command you need help with by doing `help <command>` will show you more details about that command"

    long_help = """Gives information about the bot's commands.
    Arguments:
    `command`
    `None`
    """

    category = Bot_Command_Category.TOOLS

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

            def embed_editor(
                embed: discord.Embed, paged_embed_msg: utils.Multi_Page_Embed_Message
            ) -> discord.Embed:
                # Updates the help message's embed after pages can no longer
                # be turned.
                if paged_embed_msg.page is not None:
                    embed.set_footer(text="")
                    max_footer_len = 6000 - len(embed)

                    new_footer = utils.max_len_string(
                        f" Requested by {msg.author.name}#{msg.author.discriminator} |"
                        + f" Page {paged_embed_msg.page + 1}/{len(paged_embed_msg.pages)}.",
                        max_footer_len,
                        add_ellipsis=False,
                    )
                    embed.set_footer(text=new_footer)

                return embed

            help_embeds = self.get_help_embeds(msg.channel, msg.author)

            await utils.Multi_Page_Embed_Message(
                help_embeds, msg.author, embed_editor if len(help_embeds) > 1 else None
            ).send(msg.channel)

    def get_help_embeds(
        self,
        channel: discord.abc.Messageable,
        user: Union[discord.User, discord.Member],
    ) -> list[discord.Embed]:
        """Returns a list of embeds giving an overview of all the commands
        `user` has access to in `channel` separated by each command's
        category.
        """
        # Group all available commands based on their category
        command_categories: dict[Bot_Command_Category, list[Bot_Command]] = {
            k: [] for k in Bot_Command_Category
        }
        if isinstance(channel, discord.abc.GuildChannel):
            for cmd in bot_commands.get_commands_in(channel.guild):
                if cmd.can_run(channel, user):
                    command_categories[cmd.category].append(cmd)
        else:
            for cmd in bot_commands.get_global_commands():
                if cmd.can_run(channel, user):
                    command_categories[cmd.category].append(cmd)

        ret = []
        sample_footer_len = len(utils.paged_footer_generator(999, 999, user) or "")
        description = (
            "Run `help <command>` to get detailed information about a specific command."
        )

        for category, commands in command_categories.items():
            # Create one or more embeds for all of the commands in each
            # category
            if not commands:
                continue
            commands.sort(key=lambda c: c.name.casefold())

            embed = discord.Embed(
                title=f"Commands | {category.value}",
                description=description,
            )
            for command in commands:
                cmd_description = command.short_help
                if (
                    len(embed)
                    + len(command.name)
                    + len(cmd_description)
                    + sample_footer_len
                    > 6000
                    or len(embed.fields) >= 25
                ):
                    # If command info won't fit in the embed, create a new one
                    ret.append(embed)
                    embed = discord.Embed(
                        title=f"Commands | {category.value}",
                        description=description,
                    )
                embed.add_field(name=command.name, value=cmd_description, inline=False)
            ret.append(embed)

        # Add footers to embeds
        for index, e in enumerate(ret):
            footer = utils.paged_footer_generator(index + 1, len(ret), user)
            if footer:
                e.set_footer(text=footer)

        return ret

    async def get_command_info(
        self,
        command: Union[Bot_Command, str],
        channel: discord.abc.Messageable,
        user: Optional[Union[discord.User, discord.Member]] = None,
        args: Optional[str] = None,
    ) -> None:
        """Sends a help message to `channel` for a specified `command`.

        Parameters
        ------------
        command: Union[Bot_Command, str]
        A command or the name of a command to display help for. If an invalid
        command name or a command that `user` does not have permission to run
        in `channel` is passed, an error message will be sent.

        channel: discord.abc.Messageable
        The channel to send the help message to. The bot also makes sure that
        `user` has permission to run `command` in `channel`.

        user: Optional[Union[discord.User, discord.Member]]
        The user to get help for. Can be `None` to represent a 'default' user
        `user` is passed to `command`'s `get_help` method, and also
        is used to check if `user` has permission to run `command` in
        `channel`.

        args: Optional[str]
        The arguments passed to the help command. These can be used to get
        help for a subcommand instead of all of `command`.
        """
        # If the name of a command was passed, try to find a command with that
        # name or alias
        if isinstance(command, str):
            if isinstance(channel, discord.TextChannel):
                cmd = bot_commands.get_command(command, channel.guild)
            else:
                cmd = bot_commands.get_command(command, None)
        else:
            cmd = command

        # Check to see that a valid command was passed or found
        if not isinstance(cmd, Bot_Command):
            error_message = utils.format_max_len_string(
                "Could not find the command `{}`", command
            )
            await channel.send(error_message, delete_after=7)
            return

        # Make sure the user can run the command
        if not cmd.can_run(channel, user):
            error_message = utils.format_max_len_string(
                "You do not have permission to run `{}` here.", cmd.name
            )
            await channel.send(error_message, delete_after=7)
            return

        # Remove whitespace from start and end of args
        if isinstance(args, str):
            args = args.strip()

        # Get help info about the command to display
        cmd_help = cmd.get_help(user, args)

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