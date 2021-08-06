from bot_cmd import Bot_Command, bot_commands, Bot_Command_Category
from utils import get_role

import discord


class Count_Command(Bot_Command):
    name = "count"

    short_help = "Returns a count of the specified argument."

    long_help = """Pass an item you want to know the count of
    Arguments:
    `item` (roles, members, role [role name])
    """

    category = Bot_Command_Category.COMMUNITY

    async def run(self, msg: discord.Message, args: str):
        channel = msg.channel
        guild = msg.guild
        if not args:
            embed = discord.Embed(
                title="Error",
                color=discord.Color.red(),
                description="An item is required to return a count of",
            )
            await channel.send(embed=embed)
        elif args.startswith("mem"):
            embed = discord.Embed(
                title=f"{guild.name}'s members",
                color=discord.Color.blue(),
                description=f"There are **{guild.member_count}** members in this server.",
            )
            await channel.send(embed=embed)
        elif args.strip().lower() == "roles":
            embed = discord.Embed(
                title=f"{guild.name}'s Roles",
                color=discord.Color.blue(),
                description="\n".join(
                    f"{role.name} - {len(role.members)} member(s)"
                    for role in guild.roles
                    if (not role.is_default() and not role.is_bot_managed())
                ),
            )
            await channel.send(embed=embed)
        elif args.startswith("role "):
            # get the role name
            role = args[len("role ") :].strip()
            role = await get_role(channel, role, responder=msg.author)
            if role is not None:
                # create an embed with the role's color and how many members have the role
                embed = discord.Embed(
                    title=role.name,
                    color=role.color,
                    description=f"Members: {len(role.members)}",
                )
                await channel.send(embed=embed)


bot_commands.add_command(Count_Command())
