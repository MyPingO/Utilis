from cmd import Bot_Command

import discord
import random

class Random_Command(Bot_Command):
    name = "random"

    short_help = "Sends a random number in range."

    long_help = """Sends a random number in the specified range.
    Arguments:
    `Lower bound`
    `Upper bound`
    """

    async def run(self, msg: discord.Message, args: str):
        parsed_args = args.split(" ")
        if len(parsed_args) == 2:
            try:
                #requires user to enter a valid range
                if int(parsed_args[0]) == int(parsed_args[1]):
                    print("Please enter two different numbers")
                    await msg.channel.send("Please enter two different numbers")
                    return
                #accepts user input if upper and lower bound are switched
                #elif (int(parsed_args[0]) > int(parsed_args[1])):
                #    num = random.randint(int(parsed_args[1]), int(parsed_args[0]))
                #else:
                #    num = random.randint(int(parsed_args[0]), int(parsed_args[1]))
                num = random.randint(int(parsed_args[0]), int(parsed_args[1]))
                print(num)
                await msg.channel.send(num)
            except ValueError:
                print("One or both of your arguments weren't integers")
                await msg.channel.send("One or both of your arguments weren't integers")
        else:
            print("Must enter 2 integer values arguments")
            await msg.channel.send("Must enter 2 integer value arguments")

command = Random_Command()
