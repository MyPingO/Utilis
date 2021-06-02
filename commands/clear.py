from cmd import Bot_Command

import discord

class Clear_Command(Bot_Command):
    name = "clear"

    short_help = "Deletes messages from chat"

    long_help = """Clears specified number of messages from the channel
    Arguments:
    `Number`
    """

    async def run(self, msg: discord.Message, args: str):
        #only admins can purge messages
        if msg.author.guild_permissions.administrator:
            if args:
                parsed_args = args.strip()
                if parsed_args.isdigit():
                    #delete the command message
                    await msg.delete()
                    #delete the specified number of messages from this channel
                    await msg.channel.purge(limit=int(parsed_args))
                    print(f"Deleted {parsed_args} messages.")
                    await msg.channel.send(f"Deleted {parsed_args} messages.", delete_after=5)
                else:
                    print("Your message was either NaN, or contained too many arguments")
                    await msg.channel.send("Your message was either NaN, or contained too many arguments")
            else:
                print("Please specify a number of messages to clear.")
                await msg.channel.send("Please specify a number of messages to clear.")
        else:
            await msg.channel.send("You do not have permission to use this command.")

command = Clear_Command()
