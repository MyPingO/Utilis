from bot_cmd import Bot_Command, bot_commands, Bot_Command_Category
from utils import get_member

import discord
import re


class Image_Command(Bot_Command):
    name = "img"

    short_help = "Sends a profile picture or custom emoji."

    long_help = """Sends the profile picture of a specified user or the image of a custom
    emoji in this guild. If no user is specified, sends the message author's profile picture.
    Arguments:
    `User or Emoji` (optional)
    """

    category = Bot_Command_Category.TOOLS

    #matches a custom emoji
    re_emoji = re.compile(r"<:(?P<name>(.+)):(\d){18}>")

    async def run(self, msg: discord.Message, args: str):
        #if no arguments are provided, send the avatar of the message author
        if not args:
            await self.get_image_embed(msg.author.name, msg.channel)
        #try to send the image of an emoji or sepcified member's avatar
        else:
            await self.get_image_embed(args, msg.channel)





    #get the image/gif of an emoji or member avatar and create an embed
    async def get_image_embed(self, item, channel: discord.TextChannel):
        #try to parse the item as a member
        member = await get_member(channel, item)
        #get the avatar image of the member
        if member is not None:
            #determine how to format the avatar
            if member.is_avatar_animated():
                image = member.avatar_url_as(format="gif")
            else:
                image = member.avatar_url_as(format="png")
            #create the embed
            embed = discord.Embed(title=f"**{member.display_name}**", color=discord.Color.blue())
            embed.set_image(url=image)
            #send an embed of the member's avatar to the channel
            await channel.send(embed=embed)
            return


        #try to parse the item as an emoji
        emoji = self.re_emoji.fullmatch(item)
        if emoji is not None:
            image = discord.utils.get(channel.guild.emojis, name=emoji.group("name"))
            #get the emoji image
            if image is not None:
                #determine how to format the emoji
                if image.animated:
                    image = image.url_as(static_format="gif")
                else:
                    image = image.url_as(static_format="png")

                #create the embed
                embed = discord.Embed(title=f"**{emoji.group('name')}**", color=discord.Color.blue())
                embed.set_image(url=image)
                await channel.send(embed=embed)
                return
        embed = discord.Embed(title=f"[{item}] Not Found", color=discord.Color.blue())
        await channel.send(embed=embed)

bot_commands.add_command(Image_Command())
