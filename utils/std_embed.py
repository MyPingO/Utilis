import discord
import datetime
from typing import Optional, Union


class Colors:
    INFO = discord.Color.blue()
    SUCCESS = discord.Color.green()
    INPUT = discord.Color.gold()
    RE_INPUT = discord.Color.orange()
    ERROR = discord.Color.red()


def _get_embed(
    *,
    color: Union[discord.Color, int],
    author: Optional[Union[discord.User, discord.Member]],
    title: Optional[str],
    description: Optional[str],
    url: Optional[str],
    timestamp: Optional[datetime.datetime],
) -> discord.Embed:
    ret = discord.Embed(color=color)

    if author is not None:
        ret.set_footer(text=f"Requested by {author}")
        if title:
            ret.set_author(name=title, icon_url=author.avatar_url_as(format="png"))
        else:
            ret.set_author(
                name=author.name, icon_url=author.avatar_url_as(format="png")
            )
    elif title is not None:
        ret.title = title

    if description is not None:
        ret.description = description
    if url is not None:
        ret.url = url
    if timestamp is not None:
        ret.timestamp = timestamp

    return ret


def get_info(
    *,
    title: Optional[str] = None,
    description: Optional[str] = None,
    url: Optional[str] = None,
    timestamp: Optional[datetime.datetime] = None,
    author: Optional[Union[discord.User, discord.Member]] = None,
) -> discord.Embed:
    return _get_embed(
        color=Colors.INFO,
        title=title,
        description=description,
        url=url,
        timestamp=timestamp,
        author=author,
    )


def get_success(
    *,
    title: Optional[str] = None,
    description: Optional[str] = None,
    url: Optional[str] = None,
    timestamp: Optional[datetime.datetime] = None,
    author: Optional[Union[discord.User, discord.Member]] = None,
) -> discord.Embed:
    return _get_embed(
        color=Colors.SUCCESS,
        title=title,
        description=description,
        url=url,
        timestamp=timestamp,
        author=author,
    )


def get_input(
    *,
    title: Optional[str] = None,
    description: Optional[str] = None,
    url: Optional[str] = None,
    timestamp: Optional[datetime.datetime] = None,
    author: Optional[Union[discord.User, discord.Member]] = None,
) -> discord.Embed:
    return _get_embed(
        color=Colors.INPUT,
        title=title,
        description=description,
        url=url,
        timestamp=timestamp,
        author=author,
    )


def get_reinput(
    *,
    title: Optional[str] = None,
    description: Optional[str] = None,
    url: Optional[str] = None,
    timestamp: Optional[datetime.datetime] = None,
    author: Optional[Union[discord.User, discord.Member]] = None,
) -> discord.Embed:
    return _get_embed(
        color=Colors.RE_INPUT,
        title=title,
        description=description,
        url=url,
        timestamp=timestamp,
        author=author,
    )


def get_error(
    *,
    title: Optional[str] = None,
    description: Optional[str] = None,
    url: Optional[str] = None,
    timestamp: Optional[datetime.datetime] = None,
    author: Optional[Union[discord.User, discord.Member]] = None,
) -> discord.Embed:
    return _get_embed(
        color=Colors.ERROR,
        title=title,
        description=description,
        url=url,
        timestamp=timestamp,
        author=author,
    )


async def send_info(
    channel: discord.abc.Messageable,
    *,
    title: Optional[str] = None,
    description: Optional[str] = None,
    url: Optional[str] = None,
    timestamp: Optional[datetime.datetime] = None,
    author: Optional[Union[discord.User, discord.Member]] = None,
) -> discord.Message:
    return await channel.send(
        embed=get_info(
            title=title,
            description=description,
            url=url,
            timestamp=timestamp,
            author=author,
        )
    )


async def send_success(
    channel: discord.abc.Messageable,
    *,
    title: Optional[str] = None,
    description: Optional[str] = None,
    url: Optional[str] = None,
    timestamp: Optional[datetime.datetime] = None,
    author: Optional[Union[discord.User, discord.Member]] = None,
) -> discord.Message:
    return await channel.send(
        embed=get_success(
            title=title,
            description=description,
            url=url,
            timestamp=timestamp,
            author=author,
        )
    )


async def send_input(
    channel: discord.abc.Messageable,
    *,
    title: Optional[str] = None,
    description: Optional[str] = None,
    url: Optional[str] = None,
    timestamp: Optional[datetime.datetime] = None,
    author: Optional[Union[discord.User, discord.Member]] = None,
) -> discord.Message:
    return await channel.send(
        embed=get_input(
            title=title,
            description=description,
            url=url,
            timestamp=timestamp,
            author=author,
        )
    )


async def send_reinput(
    channel: discord.abc.Messageable,
    *,
    title: Optional[str] = None,
    description: Optional[str] = None,
    url: Optional[str] = None,
    timestamp: Optional[datetime.datetime] = None,
    author: Optional[Union[discord.User, discord.Member]] = None,
) -> discord.Message:
    return await channel.send(
        embed=get_reinput(
            title=title,
            description=description,
            url=url,
            timestamp=timestamp,
            author=author,
        )
    )


async def send_error(
    channel: discord.abc.Messageable,
    *,
    title: Optional[str] = None,
    description: Optional[str] = None,
    url: Optional[str] = None,
    timestamp: Optional[datetime.datetime] = None,
    author: Optional[Union[discord.User, discord.Member]] = None,
) -> discord.Message:
    return await channel.send(
        embed=get_error(
            title=title,
            description=description,
            url=url,
            timestamp=timestamp,
            author=author,
        )
    )
