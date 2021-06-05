from cmd import Bot_Command, bot_commands
from utils import format_max_utf16_len_string

import discord


class Clear_Command(Bot_Command):
    name = "clear"

    short_help = "Deletes messages from chat"

    long_help = """Clears specified number of messages from the channel
    Arguments:
    `Number`
    """

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
                print(format_max_utf16_len_string("Deleted {} messages.", parsed_args))
                await msg.channel.send(
                    format_max_utf16_len_string("Deleted {} messages.", parsed_args),
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
