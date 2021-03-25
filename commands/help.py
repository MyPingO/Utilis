from cmd import Bot_Command, bot_commands

import discord


class Help_Command(Bot_Command):
    name = "help"

    short_help = "Gives information about the bot's methods."

    long_help = """Gives information about the bot's methods.
    Arguments:
    `command`
    `None`
    """

    async def run(self, msg: discord.Message, args: str):
        if args:
            if bot_commands.has_command(args):
                cmd = bot_commands.get_command(args)

                help_output = f"__**{cmd.name}**__\n"

                if cmd.aliases:
                    cmd_aliases = cmd.aliases.copy()
                    cmd_aliases.sort()
                    help_output += "__*Aliases:*__\n"
                    for alias in cmd_aliases:
                        help_output += "  " + alias + "\n"
                    help_output += "\n"
                help_output += cmd.long_help
                await msg.channel.send(help_output)
            else:
                await msg.channel.send(f"Could not find the command `{args}`.", delete_after=7)

        else:
            help_output = f"__**Commands**__\n"
            commands = list(bot_commands.unique_commands.keys())
            for cmd_name in commands:
                cmd = bot_commands.unique_commands[cmd_name]
                help_output += f"*{cmd_name}*: {cmd.short_help}\n"

            await msg.channel.send(help_output)


command = Help_Command()