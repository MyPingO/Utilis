from bot_cmd import Bot_Command, bot_commands

import discord


class New_Semester_Command(Bot_Command):
    name = "newsem"

    short_help = "Denotes a new semester"

    long_help = """Sends a divider message in chat denoting a new semester
    Arguments:
    `None`
    """

    categories = ["random"]

    def can_run(self, location, member):
        return member is not None and member.guild_permissions.administrator

    async def run(self, msg: discord.Message, args: str):
        if not args:
            for category in msg.guild.categories:
                if category.name.lower() in self.categories:
                    for channel in category.text_channels:
                        print("A new semester has started!")
                        await channel.send(
                            """```
         |\     |
         | \    |
         |  \   |
         |   \  |
         |    \ |
         |     \|
          _______
         |
         |
         |_____
         |
         |
         |_______
    \                /
     \              /
      \            /
       \    /\    /
        \  /  \  /
         \/    \/



         _________
        |
        |
        |________
                 |
                 |
        _________|
         _______
        |
        |
        |_____
        |
        |
        |_______

         |\    /|
         | \  / |
         |  \/  |
         |      |
         |      |
         |      |
         _______
        |
        |
        |_____
        |
        |
        |_______
         _________
        |
        |
        |________
                 |
                 |
        _________|
        ___________
             |
             |
             |
             |
             |
             |
        _________
        |
        |
        |_____
        |
        |
        |________
        _______
        |      |
        |      |
        |______|
        |   \\
        |    \\
        |     \\
        ``` """
                        )
        else:
            print("This command doesn't have any arguments.")
            await msg.channel.send("This command doesn't have any arguments.")


bot_commands.add_command(New_Semester_Command())
