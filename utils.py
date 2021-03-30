from core import client

import discord
from re import compile as re_compile
from typing import Callable

re_user_ping = re_compile(r"<@!?(\d{18})>")
re_user_discriminator = re_compile(r"(.+)#(\d{4})")

re_channel_mention = re_compile(r"<#(\d{18})>")

re_role_mention = re_compile(r"<@&(\d{18})>")


async def get_member(
    channel: discord.channel,
    m: str,
    responder: discord.Member = None,
    allow_multiple_matches: bool = True,
    timeout: int = None,
):
    """Gets a member in `channel`'s guild from the string `m`.
    If there are multiple members that match the string `m` and
    `allow_multiple_matches` is `True`, then a message will be sent asking for
    one of the matching members to be chosen in `channel`.

    Parameters
    -----------
    channel: `discord.Channel`
    A channel from the guild you want to search for the member `m` in. If
    multiple members that match `m` are found and `allow_multiple_matches` is
    `True`, a message will be sent to this channel asking for one of the
    matching members to be chosen.

    m: `str`
    The member you want to get. Can be a member mention, member id, username or
    user nickname (both case insensitive), or full username with the
    discriminator (ex. name#1234; case sensitive)

    responder: `discord.Member` or `None`
    If a message asking for one of multiple members matching `m` to be chosen
    is sent to `channel` and `responder` is not `None`, only the member `responder`
    can reply with a selection. Otherwise, anyone in `channel` can select a
    member matching `m` from the list.

    allow_multiple_matches: `bool`
    Whether or not a message should be sent to `channel` asking for a matching
    member to be chosen in the event that multiple members matching `m` are
    found. If multiple members matching `m` are found and
    `allow_multiple_matches` is `False`, the function will return `None`.

    timeout: `int` or `None`
    If multiple matching members are found for `m` and `allow_multiple_matches`
    is `True`, `timeout` controls how long in seconds it should take for the
    message asking for a matching member to be chosen to time out and make the
    function return `None`. If `timeout` is `None`, the default timeout length
    will be used.
    """
    # Try to parse `m` as a user id
    if m.isdigit():
        out = channel.guild.get_member(int(m))
        if out is not None:
            return out

    # Try to parse `m` as a member mention
    user_ping = re_user_ping.fullmatch(m)
    if user_ping:
        out = channel.guild.get_member(int(user_ping.group(1)))
        if out is not None:
            return out

    # Try to parse `m` as a full username, including the discriminator
    user_discriminator = re_user_discriminator.fullmatch(m)
    if user_discriminator:
        out = channel.guild.get_member_named(m)
        if out is not None:
            return out
        for member in channel.guild.members:
            if member.name.casefold() == user_discriminator.group(
                1
            ).casefold() and member.discriminator == user_discriminator.group(2):
                return member

    # Try to find members with the username or nickname `m` (case insensitive)
    m_lower = m.casefold()
    members = []
    for member in channel.guild.members:
        if member.name.casefold() == m_lower:
            members.append(member)
        elif member.nick:
            if member.nick == m_lower:
                members.append(member)

    if len(members) == 0:  # If no members were found, return `None`
        return None
    # If one member was found, return that member
    if len(members) == 1:
        return members[0]

    # If multiple members with the username/nickname were found and
    # `allow_multiple_matches` is True, send a messsage asking for a member to
    # be chosen.
    if not allow_multiple_matches:
        return None

    member_option_generator = (
        lambda m: f"{m.name}#{m.discriminator}{f' ({m.nick})' if m.nick else ''}"
    )
    if timeout is None:
        return await user_select_from_list(
            channel,
            members,
            member_option_generator,
            responder=responder,
            title="Select user:",
        )
    else:
        return await user_select_from_list(
            channel,
            members,
            member_option_generator,
            responder=responder,
            title="Select user:",
            timeout=timeout,
        )


async def get_channel(
    channel: discord.channel,
    c: str,
    responder: discord.Member = None,
    include_hidden_channels: bool = False,
    allow_multiple_matches: bool = True,
    timeout: int = None,
):
    """Gets a channel in `channel`'s guild from the string `c`.
    If there are multiple channels that match the string `c` and
    `allow_multiple_matches` is `True`, then a message will be sent asking for
    one of the matching channels to be chosen in `channel`.

    Parameters
    -----------
    channel: `discord.Channel`
    A channel from the guild you want to search for the channel `c` in. If
    multiple channels that match `c` are found and `allow_multiple_matches` is `True`, a
    message will be sent to this channel asking for one of the matching channels
    to be chosen.

    c: `str`
    The channel you want to get. Can be a channel mention, channel id, or channel name
    (case insensitive).

    responder: `discord.Member` or `None`
    If a message asking for one of multiple channels matching `c` to be chosen
    is sent to `channel` and `responder` is not `None`, only the member
    `responder` can reply with a selection. Otherwise, anyone in `channel` can
    select a channel matching `c` from the list.

    include_hidden_channels: `bool`
    If `responder` is not `None`, and `include_hidden_channels` is `True`, then
    only channels visible to `responder` will be checked to see if they match
    `c`.

    allow_multiple_matches: `bool`
    Whether or not a message should be sent to `channel` asking for a matching
    channel to be chosen in the event that multiple channels matching `c` are
    found. If multiple channels matching `c` are found and
    `allow_multiple_matches` is `False`, the function will return `None`.

    timeout: `int` or `None`
    If multiple matching channels are found for `c` and `allow_multiple_matches`
    is `True`, `timeout` controls how long in seconds it should take for the
    message asking for a matching channel to be chosen to time out and make the
    function return `None`. If `timeout` is `None`, the default timeout length
    will be used.
    """
    if include_hidden_channels or responder is None:
        include_channel = lambda channel: True
    else:
        include_channel = lambda channel: channel.permissions_for(
            responder
        ).view_channel

    # Try to parse `c` as a channel id
    if c.isdigit():
        out = channel.guild.get_channel(int(c))
        if out is not None and include_channel(out):
            return out

    # Try to parse `c` as a channel mention
    channel_mention = re_channel_mention.fullmatch(c)
    if channel_mention:
        out = channel.guild.get_channel(int(channel_mention.group(1)))
        if out is not None and include_channel(out):
            return out

    # Try to find channels with the name `c` (case insensitive)
    c_lower = c.casefold()
    channels = []
    for guild_channel in channel.guild.channels:
        if guild_channel.name.casefold() == c_lower and include_channel(guild_channel):
            channels.append(guild_channel)

    if len(channels) == 0:  # If no channels were found, return `None`
        return None
    # If one channel was found, return that channel
    if len(channels) == 1:
        return channels[0]

    # If multiple channels with the name were found and `allow_multiple_matches`
    # is True, send a messsage asking for a channel to be chosen.
    if not allow_multiple_matches:
        return None

    channel_option_generator = lambda c: c.mention

    if timeout is None:
        return await user_select_from_list(
            channel,
            channels,
            channel_option_generator,
            responder=responder,
            title="Select channel:",
        )
    else:
        return await user_select_from_list(
            channel,
            channels,
            channel_option_generator,
            responder=responder,
            title="Select channel:",
            timeout=timeout,
        )


async def get_role(
    channel: discord.channel,
    r: str,
    responder: discord.Member = None,
    allow_multiple_matches: bool = True,
    timeout: int = None,
):
    """Gets a role in `channel`'s guild from the string `r`.
    If there are multiple roles that match the string `r` and
    `allow_multiple_matches` is `True`, then a message will be sent asking for
    one of the matching roles to be chosen in `channel`.

    Parameters
    -----------
    channel: `discord.Channel`
    A channel from the guild you want to search for the role `r` in. If
    multiple roles that match `r` are found and `allow_multiple_matches` is
    `True`, a message will be sent to this channel asking for one of the
    matching roles to be chosen.

    r: `str`
    The role you want to get. Can be a role mention, role id, or role name
    (case insensitive).

    responder: `discord.Member` or `None`
    If a message asking for one of multiple roles matching `r` to be chosen is
    sent to `channel` and `responder` is not `None`, only the member `responder`
    can reply with a selection. Otherwise, anyone in `channel` can select a
    role matching `r` from the list.

    allow_multiple_matches: `bool`
    Whether or not a message should be sent to `channel` asking for a matching
    role to be chosen in the event that multiple roles matching `r` are
    found. If multiple roles matching `r` are found and `allow_multiple_matches`
    is `False`, the function will return `None`.

    timeout: `int` or `None`
    If multiple matching roles are found for `r` and `allow_multiple_matches`
    is `True`, `timeout` controls how long in seconds it should take for the
    message asking for a matching role to be chosen to time out and make the
    function return `None`. If `timeout` is `None`, the default timeout length
    will be used.
    """
    # Try to parse `r` as a role id
    if r.isdigit():
        out = channel.guild.get_role(int(r))
        if out is not None:
            return out

    # Try to parse `r` as a role mention
    role_mention = re_role_mention.fullmatch(r)
    if role_mention:
        out = channel.guild.get_role(int(role_mention.group(1)))
        if out is not None:
            return out

    # Try to find roles with the name `r` (case insensitive)
    role_lower = r.casefold()
    roles = []
    for r in channel.guild.roles:
        if r.name.casefold() == role_lower:
            roles.append(r)

    if len(roles) == 0:  # If no roles were found, return `None`
        return None
    # If one role was found, return that role
    if len(roles) == 1:
        return roles[0]

    # If multiple roles with the name were found and `allow_multiple_matches`
    # is True, send a messsage asking for a role to be chosen.
    if not allow_multiple_matches:
        return None

    role_option_generator = (
        lambda r: f"{r.name} ({len(r.members)} members with role) [{r.id}]"
    )

    if timeout is None:
        return await user_select_from_list(
            channel,
            roles,
            role_option_generator,
            responder=responder,
            title="Select role:",
        )
    else:
        return await user_select_from_list(
            channel,
            roles,
            role_option_generator,
            responder=responder,
            title="Select role:",
            timeout=timeout,
        )


async def user_select_from_list(
    channel: discord.channel,
    options: list,
    option_text_generator: Callable[[], str],
    responder: discord.Member = None,
    title: str = None,
    indent: int = 2,
    timeout: int = 60,
):
    """Sends a numbered list of options to be chosen from in a channel. If
    `responder` is not `None`, that member will then be able to choose one of
    the options provided in `options` by sending the number corresponding to
    that option. If `responder` is `None`, anyone in `channel` will be able to
    make a selection from `options` by sending a number in `channel`.
    Returns an option from `options` if an option from the list was selected or
    `None` if the function times out waiting for a selection.

    Parameters
    -----------
    channel: `discord.channel`
    The channel where the `options` will be sent to be chosen from.

    options: `list`
    The list of options that will be chosen from.

    option_text_generator: `Callable[[], str]`
    A function to convert an option from `options` to a string representation
    that can be sent in a message to `channel` to be chosen from by a user.

    responder: `discord.Member`
    If `responder` is not `None`, then `responder` will be mentioned in the
    message asking for a selection to be made from `options`, and only
    `responder` will be able to make a selection. If `responder` is `None`,
    anyone who can send messages in `channel` will be able to make a selection
    from `options`.

    title: `str`
    The message included at the top of the message asking for a selection to be
    made.

    indent: `int`
    How many spaces each string representation of an option should be indented
    in the message asking for a selection from `options`.

    timeout: `int`
    How long in seconds the function should wait for a selection from `options`
    before timing out and returning `None`.
    """

    message_text = ""
    if responder:
        message_text += responder.mention + " "
    if title:
        message_text += f"**{title}**\n"
    for index, item in enumerate(options):
        if title:
            message_text += " " * indent
        message_text += f"**{str(index+1)}:** {option_text_generator(item)}\n"

    if responder is not None:
        check_user_int_response = (
            lambda x: x.channel == channel
            and x.author == responder
            and x.content.isdigit()
        )
    else:
        check_user_int_response = (
            lambda x: x.channel == channel
            and x.author != client.user
            and x.content.isdigit()
        )

    msg = await channel.send(message_text)

    # Loop until a valid selection is made or the function times out waiting
    # for a selection.
    while True:
        response = None
        try:
            response = await client.wait_for(
                "message",
                check=check_user_int_response,
                timeout=timeout,
            )
        except:
            await msg.delete()
            await channel.send(
                "Error: Timed out waiting for user input.", delete_after=20
            )
            return None

        int_response = int(response.content)
        if int_response <= len(options) and int_response > 0:
            await msg.delete()
            await response.delete()
            return options[int_response - 1]
        else:
            await channel.send(
                f"Error: Option `{response.content}` is out of bounds.", delete_after=7
            )
