from bot_cmd import Bot_Command, bot_commands, Bot_Command_Category
from utils import fmt

import discord


class Clear_Command(Bot_Command):
    name = "clear"

    aliases = ["c"]

    short_help = "Deletes messages from chat"

    long_help = """Clears specified number of messages from the channel
    __Usage:__
    **clear** *number*
    **c** *number*
    """

    category = Bot_Command_Category.MODERATION

    def can_run(self, location, member):
        # only admins can purge messages
        return member is not None and member.guild_permissions.administrator

    async def run(self, msg: discord.Message, args: str):
        if args:
            parsed_args = args.strip()
            if parsed_args.isdigit():
                # delete the command message
                await msg.delete()
                # delete the specified number of messages from this channel
                await msg.channel.purge(limit=int(parsed_args))
                print(fmt.format_maxlen("Deleted {} messages.", parsed_args))
                await msg.channel.send(
                    fmt.format_maxlen("Deleted {} messages.", parsed_args),
                    delete_after=5,
                )
            else:
                print("Your message was either NaN, or contained too many arguments")
                await msg.channel.send(
                    "Your message was either NaN, or contained too many arguments"
                )
        else:
            print("Please specify a number of messages to clear.")
            await msg.channel.send("Please specify a number of messages to clear.")


bot_commands.add_command(Clear_Command())
