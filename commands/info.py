from bot_cmd import Bot_Command, bot_commands, Bot_Command_Category
from utils import find, std_embed

import discord


class Info_Command(Bot_Command):
    name = "Info"

    short_help = "Returns information about the specified argument."

    long_help = """Provides more information on various objects.
    __Usage:__
    **info** *roles|channels|guild*
    **info role** *role*
    **info user** [*user*]
    """

    category = Bot_Command_Category.COMMUNITY

    async def run(self, msg: discord.Message, args: str):
        channel = msg.channel
        guild = msg.guild
        if not args:
            await std_embed.send_error(
                channel,
                title="Error",
                description="An item is required to return a count of"
            )

        elif args.strip().casefold() == "roles":
            await std_embed.send_info(
                channel,
                title=f"{guild.name}'s Roles",
                description = "\n".join(
                    f"{role.mention} - {str(len(role.members))+' members' if len(role.members) != 1 else str(len(role.members))+' member'}" 
                    for role in guild.roles 
                    if (not role.is_default() and not role.is_bot_managed())
                )
            )

        elif args.casefold().startswith("role "):
            #get the role name
            role = args[len("role "):].strip()
            role = await find.role(channel, role, responder=msg.author)
            if role is not None:
                #create an embed with the role's color and how many members have the role
                embed = discord.Embed(
                    title=role.name,
                    color=role.color,
                )

                #add fields of role attributes
                embed.add_field(name="ID", value=str(role.id), inline=True)
                embed.add_field(name="Color", value=str(role.color), inline=True)

                #add a field displaying up to the first 10 members with this role
                value = ""
                try:
                    for i in range(10):
                        value += f"{i+1}. {role.members[i].mention}\n"
                except IndexError:
                    pass
                if len(role.members) > 0:
                    embed.add_field(
                        name=f"Members: {len(role.members)}",
                        value=value,
                        inline=False
                    )
                await channel.send(embed=embed)

        #TODO
        elif args.casefold().startswith("channels"):
            pass

        #contains all of the above abriefed
        elif args.casefold().startswith("guild"):
            embed = discord.Embed(
                title=f"{guild.name}",
                color=discord.Color.blue(),
            )
            embed.set_thumbnail(url=guild.icon_url_as(format='png'))
            #first row
            embed.add_field(
                name="Owner",
                value=f"{guild.owner.mention}",
                inline=True
            )
            embed.add_field(
                name="Created",
                value=f"<t:{int(guild.created_at.timestamp())}:D>",
                inline=True
            )
            embed.add_field(
                name="ID",
                value=guild.id,
                inline=True
            )
            #second row
            text_channels = len(guild.text_channels)
            voice_channels = len(guild.voice_channels)
            categories = len(guild.categories)
            embed.add_field(
                name="Channels",
                value=f"""
                {len(guild.channels)}: {str(categories)+' categories' if categories != 1 else str(categories)+' category'},
                {str(text_channels)+' text channels' if text_channels != 1 else str(text_channels)+' text channel'},
                {str(voice_channels)+' voice channels' if voice_channels != 1 else str(voice_channels)+' voice channel'}
                """,
                inline=True
            )
            embed.add_field(
                name="Roles",
                value=f"{len(guild.roles)}",
                inline=True
            )
            embed.add_field(
                name="Members",
                value=f"""
                {guild.member_count} members
                """,
                inline=True
            )

            await channel.send(embed=embed)
        elif args.casefold().startswith("user"):
            user = args[len("user"):].strip()
            #if no user is passed, return the info of the author
            if not user:
                user = msg.author
            else:
                user = await find.member(channel, user, responder=msg.author)

            if user is not None:
                embed = discord.Embed(
                    title=user.name,
                    color=user.color
                )
                embed.set_thumbnail(url=user.avatar_url_as(format='png'))
                embed.add_field(
                    name="ID",
                    value=user.id,
                    inline=True
                )
                embed.add_field(
                    name="Created at",
                    value=f"<t:{int(user.created_at.timestamp())}:D>",
                    inline=True
                )
                embed.add_field(
                    name="Joined server at",
                    value=f"<t:{int(user.joined_at.timestamp())}:D>",
                    inline=True
                )
                embed.add_field(
                    name="Roles",
                    value=", ".join(role.name for role in user.roles if role is not guild.default_role),
                    inline=True
                )
                embed.add_field(
                    name="Permissions",
                    value=f"""
                    {'Server Owner' if user == guild.owner else ''}
                    {'Server Admin' if user.guild_permissions.administrator else ''}
                    """,
                    inline=True
                )
                await channel.send(embed=embed)


bot_commands.add_command(Info_Command())
