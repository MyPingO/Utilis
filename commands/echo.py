from bot_cmd import Bot_Command, bot_commands

import discord


class Echo_Command(Bot_Command):
    name = "echo"

    short_help = "Repeats the arguments in a message."

    long_help = """Repeats the arguments in a message.
    Arguments:
    `text`
    `None`
    """

    async def run(self, msg: discord.Message, args: str):
        if args:
            single_line_args = args.replace("\n", "\\n")
            print(f'Echo: "{single_line_args}"')
            await msg.channel.send(args)
        else:
            print("Echo.")
            await msg.channel.send("Echo.")


bot_commands.add_command(Echo_Command())