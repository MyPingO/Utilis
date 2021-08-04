from bot_cmd import Bot_Command, bot_commands
from core import client
from pathlib import Path
from utils import (
    get_channel,
    get_role,
    user_select_from_list,
    format_max_len_string,
)

import discord
import json


class Del_Command(Bot_Command):
    name = "del"

    short_help = "Deletes the specified object"

    long_help = """Deletes the specified object from this server.
    Arguments:
    `Object`
    `Name`

    **Deletable objects:**
        -role
        -channel

    To delete multiple objects of the same type, separate the names by commas.
    Cannot delete objects of different types in one command.
    """

    def can_run(self, location, member):
        return member is not None and member.guild_permissions.administrator

    async def run(self, msg: discord.Message, args: str):
        # get the guild
        guild = msg.author.guild
        # get the current channel
        channel = msg.channel

        if args:
            # split the object type from the object names
            parsed_args = args.strip().split(" ", 1)
            # delete roles
            if parsed_args[0] == "role":
                # split the comma separated role names
                parsed_args = parsed_args[1].split(", ")
                # verify before deleting each role
                for r in parsed_args:
                    try:
                        role = await get_role(channel, r, responder=msg.author)
                        if await self.verify(
                            channel, type(role).__name__, r, msg.author
                        ):
                            await role.delete()
                            print(f"Role {r} has been deleted")
                            await channel.send(
                                format_max_len_string(
                                    "Role `{}` has been deleted.", r
                                )
                            )
                    except AttributeError:
                        print(f"Could not find a role called {r}")
                        await channel.send(
                            format_max_len_string(
                                "Could not find a role called `{}`", r
                            )
                        )
            elif parsed_args[0] == "channel":
                # split the comma separated channel names
                parsed_args = parsed_args[1].split(", ")
                for c in parsed_args:
                    try:
                        del_channel = await get_channel(
                            channel, c, responder=msg.author
                        )
                        if await self.verify(
                            channel, type(del_channel).__name__, c, msg.author
                        ):
                            await del_channel.delete()
                            print(f"Channel {c} has been deleted")
                            await msg.channel.send(
                                format_max_len_string(
                                    "Channel `{}` has been deleted.", c
                                )
                            )
                    except AttributeError:
                        print(f"Could not find a channel called {c}")
                        await msg.channel.send(
                            format_max_len_string(
                                "Could not find a channel called `{}`", c
                            )
                        )

    # requires verification before proceeding with deleting an object
    async def verify(
        self, channel: discord.channel, item: str, name: str, responder: discord.Member
    ) -> bool:
        # if item is of NoneType
        if item.lower() == "nonetype":
            raise AttributeError

        # ask for verification before deleting the object from the server
        msg = await channel.send(
            format_max_len_string(
                "Are you sure you want to delete the `{}` named `{}`? This action cannot be undone.",
                item,
                name,
            )
        )
        response = None
        # wait 90 seconds for user to respond
        try:
            check = lambda x: x.channel == channel and x.author == responder
            response = await client.wait_for("message", check=check, timeout=90)
            # if user verifies, return True
            if response.content.strip().lower() in ["y", "yes"]:
                await msg.delete()
                await response.delete()
                return True
        # if user fails to respond in time
        except:
            await channel.send(
                "Error: Timed out waiting for user input.", delete_after=10
            )
            await msg.delete()
            return False
        await msg.delete()
        await response.delete()
        return False


bot_commands.add_command(Del_Command())
