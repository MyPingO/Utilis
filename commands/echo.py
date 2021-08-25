from bot_cmd import Bot_Command, bot_commands, Bot_Command_Category

import discord


class Echo_Command(Bot_Command):
    name = "echo"

    short_help = "Repeats the arguments in a message."

    long_help = """Repeats the arguments in a message.
    Arguments:
    `text`
    `None`
    """

    category = Bot_Command_Category.TOOLS

    def can_run(self, location, member):
        return member is not None and member.guild_permissions.administrator

    async def run(self, msg: discord.Message, args: str):
        if args:
            single_line_args = args.replace("\n", "\\n")
            print(f'Echo: "{single_line_args}"')
            await msg.channel.send(args)
        else:
            print("Echo.")
            await msg.channel.send("Echo.")


bot_commands.add_command(Echo_Command())
