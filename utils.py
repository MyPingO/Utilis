from core import client

import discord
import asyncio
import math
import re
from typing import Callable, Iterable, Optional, Sequence, TypeVar

T = TypeVar("T")


def utf16_len(s: str) -> int:
    """Returns the UTF16 length of a string, which is the length Discord uses
    when checking if a message is too long.
    """
    return len(s.encode("utf_16_le", "replace")) // 2


def utf16_embed_len(e: discord.Embed) -> int:
    """Returns the UTF16 length of an embed, which is the length Discord uses
    when checking if a message is too long.
    """
    total = 0
    if isinstance(e.title, str):
        total += utf16_len(e.title)
    if isinstance(e.description, str):
        total += utf16_len(e.description)
    for field in getattr(e, "_fields", []):
        total += utf16_len(field["name"]) + utf16_len(field["value"])

    try:
        footer = e._footer
    except AttributeError:
        pass
    else:
        if isinstance(footer["text"], str):
            total += utf16_len(footer["text"])

    try:
        author = e._author
    except AttributeError:
        pass
    else:
        if isinstance(author["name"], str):
            total += utf16_len(author["name"])

    return total


def max_utf16_len_string(s: str, maxlen: int, add_ellipsis: bool = True) -> str:
    """Shortens a string to a maximum UTF16 length if it is too long.

    Parameters
    -----------
    s: str
    The string to shorten.

    maxlen: int
    The maximum UTF16 length for the string being shortened.

    add_ellipsis: bool
    Whether or not '...' should be added to the end of the string if it is
    shortened. The ellipses are included when calculating the max length.
    """
    # Common simple cases for the function
    if maxlen <= 0:
        return ""
    if utf16_len(s) <= maxlen:
        return s
    if add_ellipsis:
        if maxlen <= 3:
            return "." * maxlen

    # Tries to naively slice the string assuming that all characters within
    # maxlen have a UTF16 length of 1
    if add_ellipsis:
        naive_short = f"{s[:maxlen-3]}..."
    else:
        naive_short = s[:maxlen]
    naive_len = utf16_len(naive_short)
    if naive_len == maxlen:
        return naive_short
    # If the naive slice does not give the exact max length, use a right
    # bisection to find a point to the right of where the slice should occur.
    if naive_len < maxlen:
        low = naive_len
        high = len(s)
    else:
        low = 0
        high = naive_len
    while low < high:
        mid = (low + high) // 2
        if utf16_len(s[:mid]) <= maxlen:
            low = mid + 1
        else:
            high = mid

    # Move where the slice should occur to the left as little as possible
    # while still being within maxlen.
    if add_ellipsis:
        while utf16_len(s[:low]) > maxlen - 3:
            low -= 1
        return f"{s[:low]}..."
    else:
        while utf16_len(s[:low]) > maxlen:
            low -= 1
        return s[:low]


def format_max_utf16_len_string(
    fstring: str,
    *args,
    max_total_len: Optional[int] = 2000,
    max_arg_len: Optional[int] = None,
    add_ellipsis: bool = True,
) -> str:
    """Formats a string replacing instances of `"{}"` with args while keeping
    below a maximum length.

    Examples
    -----------
    .. code-block:: python3
        format_max_utf16_len_string(
            "AB {} CD {}",
            "123",
            456,
            max_total_len=None
        ) == "AB 123 CD 456"

    .. code-block:: python3
        format_max_utf16_len_string(
            "AB {} CD",
            123456789
            max_total_len=12
        ) == "AB 123... CD"

    .. code-block:: python3
        format_max_utf16_len_string(
            "AB {} CD",
            123456789
            max_total_len=None,
            max_arg_len=6
        ) == "AB 123... CD"

    Parameters
    -----------
    fstring: str,
    The string to format. "{}" should be used as placeholders for args.

    *args
    The args to replace the placeholder "{}"s in `fstring` with. The number of
    args must be equal to the number of placeholders.

    max_total_len: Optional[int]
    The maximum UTF16 length for the return string. args will be shortened
    roughly evenly until the UTF16 length of the final string will be within
    the max length. `fstring` will not be shortened to reduce the final
    string's length.

    max_arg_len: Optional[int]
    The maximum UTF16 length for every arg. This is applied before shortening
    args to ensure that the return string's UTF16 length is also within
    `max_total_len`.

    add_ellipsis: bool
    Whether or not args that are shortened to fit either `max_total_len` or
    `max_arg_len` should have '...' at the end.
    """
    # If there's nothing to format, return the string.
    if "{}" not in fstring and len(args) == 0:
        return fstring

    split_fstring = fstring.split("{}")
    if len(split_fstring) != len(args) + 1:
        raise ValueError("Number of arguments does not match number of placeholders.")

    # Convert args to a list of strings
    if max_arg_len is not None:
        # Limit the UTF16 length of each arg to max_arg_len if it was given.
        arg_list = [
            max_utf16_len_string(str(arg), max_arg_len, add_ellipsis) for arg in args
        ]
    elif max_total_len is not None:
        # Limit the UTF16 length of each arg to max_total_len if it was given,
        # because each arg can be at most that long.
        arg_list = [
            max_utf16_len_string(str(arg), max_total_len, add_ellipsis) for arg in args
        ]
    else:
        arg_list = [str(arg) for arg in args]

    # If a max UTF16 length was given for the string, shorten args to fit it.
    if max_total_len is not None:
        # Get a list of the UTF16 length of every arg
        arg_lens = [utf16_len(arg) for arg in arg_list]

        # Get the total UTF16 lengths of the fstring and args.
        total_fstring_len = sum(utf16_len(s) for s in split_fstring)
        total_args_len = sum(arg_lens)

        # The maximum total length of all args in order to keep the return
        # string's UTF16 length within max_total_len.
        total_args_maxlen = max_total_len - total_fstring_len

        # If the fstring is too long to fit any args in, return the fstring.
        if total_args_len <= 0:
            return "".join(split_fstring)

        # Keep shortening the longest args until all args are within the total
        # length for all args.
        while total_args_len > total_args_maxlen:
            # Get the longest and second longest arg lengths.
            sorted_unique_lens = sorted(set(arg_lens))
            maxlen = sorted_unique_lens[-1]
            if len(sorted_unique_lens) > 1:
                second_maxlen = sorted_unique_lens[-2]
            else:
                second_maxlen = 0

            # Get the indecies of args to shorten. The list is reversed so
            # that the last args get shortened the most.
            max_len_indecies = [i for i, v in enumerate(arg_lens) if v == maxlen]
            max_len_indecies.reverse()

            # How much space can be saved by shortening the longest strings.
            # This can either be enough space to bring the total length of
            # args below the max length, or shortening the longest strings to
            # the length of the second largest strings, so that the second
            # largest strings will also be shortened in the next step in the
            # loop.
            total_delta = min(
                total_args_len - total_args_maxlen,
                len(max_len_indecies) * (maxlen - second_maxlen),
            )

            # Shorten the longest args.
            for index_num, index in enumerate(max_len_indecies):
                # The amount to shorten the arg. This should be as short as
                # possible.
                # The amount that each string gets shortened by gets smaller
                # as the loop continues, as total_delta will decrease and
                shorten_amount = math.ceil(
                    total_delta / (len(max_len_indecies) - index_num)
                )
                # What to shorten the arg to. Should not be shorter than the
                # second largest args.
                shorten_to = max(
                    maxlen - shorten_amount,
                    second_maxlen,
                )
                # Shorten the arg
                arg_list[index] = max_utf16_len_string(
                    arg_list[index], shorten_to, add_ellipsis
                )
                # Update the arg's UTF16 length in the list of arg UTF16 lengths
                arg_lens[index] = utf16_len(arg_list[index])
                # Decrease how much the rest of the longest args need to be
                # shortened by in order to reach the target total length.
                delta = maxlen - arg_lens[index]
                total_delta -= delta

            # Update the total arg lengths.
            total_args_len = sum(arg_lens)

    # Insert args into the fstring and return
    ret = "".join(
        fstring_part + arg_part
        for fstring_part, arg_part in zip(split_fstring, arg_list)
    )
    return ret + split_fstring[-1]


async def roles(msg: discord.Message):
    """Adds or removes specified roles from the message author.
    Multiple roles can be added/removed in one message if they are separated by commas.

    Parameters
    -----------
    msg: `discord.Message`
    The message containing the roles the author wants to assign or remove from themself.
    Roles are separated by commas.
    Role names are preceded by a `+` or `-` to specify whether they should be
    added or removed.
    """

    # split the message into a list of individual roles
    arr = msg.content.split(", ")
    for role in arr:
        # get role name
        name = role.strip()[1:]

        # determine whether the role should be assigned or removed
        if role.startswith("+"):
            try:
                r = discord.utils.get(msg.author.guild.roles, name=name)
                await msg.author.add_roles(r)
            except (discord.HTTPException, discord.Forbidden):
                print(f"no role called {role[1:]}")
        elif role.startswith("-"):
            try:
                r = discord.utils.get(msg.author.guild.roles, name=name)
                await msg.author.remove_roles(r)
            except (discord.HTTPException, discord.Forbidden):
                print(f"{msg.author} doesn't have the role {role[1:]}")


_re_user_ping = re.compile(r"<@!?(\d{18})>")
_re_user_discriminator = re.compile(r"(.+)#(\d{4})")


async def get_member(
    channel: discord.TextChannel,
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
    channel: `discord.TextChannel`
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
    user_ping = _re_user_ping.fullmatch(m)
    if user_ping:
        out = channel.guild.get_member(int(user_ping.group(1)))
        if out is not None:
            return out

    # Try to parse `m` as a full username, including the discriminator
    user_discriminator = _re_user_discriminator.fullmatch(m)
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


_re_channel_mention = re.compile(r"<#(\d{18})>")


async def get_channel(
    channel: discord.TextChannel,
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
    channel: `discord.TextChannel`
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
    channel_mention = _re_channel_mention.fullmatch(c)
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


_re_role_mention = re.compile(r"<@&(\d{18})>")


async def get_role(
    channel: discord.TextChannel,
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
    channel: `discord.TextChannel`
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
    role_mention = _re_role_mention.fullmatch(r)
    if role_mention:
        out = channel.guild.get_role(int(role_mention.group(1)))
        if out is not None:
            return out

    # Try to find roles with the name `r` (case insensitive)
    role_lower = r.casefold()
    roles = []
    for role in channel.guild.roles:
        if role.name.casefold() == role_lower:
            roles.append(role)

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
    channel: discord.TextChannel,
    options: Sequence[T],
    option_text_generator: Callable[[T], str],
    responder: discord.Member = None,
    title: str = None,
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
    channel: `discord.TextChannel`
    The channel where the `options` will be sent to be chosen from.

    options: `Sequence[T]`
    The options that will be chosen from.

    option_text_generator: `Callable[[T], str]`
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

    timeout: `int`
    How long in seconds the function should wait for a selection from `options`
    before timing out and returning `None`.
    """

    message_text = responder.mention if responder else ""
    message_embed = discord.Embed(title=title)

    choice_messages = []

    for index, item in enumerate(options):
        name = str(index + 1)
        value = option_text_generator(item)

        if utf16_embed_len(message_embed) + utf16_len(name + value) > 6000:
            choice_messages.append(
                await channel.send(message_text, embed=message_embed)
            )
            message_embed = discord.Embed(title=title)

        message_embed.add_field(name=name, value=value, inline=False)

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

    choice_messages.append(await channel.send(message_text, embed=message_embed))

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
        except asyncio.TimeoutError:
            await channel.delete_messages(choice_messages)
            await channel.send(
                "Error: Timed out waiting for user input.", delete_after=20
            )
            return None

        int_response = int(response.content)
        if int_response <= len(options) and int_response > 0:
            await channel.delete_messages(choice_messages)
            try:
                await response.delete()
            except discord.NotFound:
                pass
            return options[int_response - 1]
        else:
            error_message = format_max_utf16_len_string(
                "Error: Option `{}` is out of bounds.", response.content
            )
            await channel.send(error_message, delete_after=7)


async def wait_for_reply(
    member: discord.Member,
    channel: discord.TextChannel,
    timeout: int = 60,
    error_message: Optional[str] = "Error: You took too long to respond",
) -> Optional[str]:
    """Gets the message content of the next message sent by `member` in
    `channel`. If no response is received in `timeout` seconds, `error_message`
    is sent to `channel` if it is not `None` and the function returns `None`.
    """
    try:
        response = await client.wait_for(
            "message",
            check=lambda m: m.author == member and m.channel == channel,
            timeout=timeout,
        )
        return response.content
    except asyncio.TimeoutError:
        # if no response is given within 60 seconds
        if error_message is not None:
            await channel.send(error_message)
        return None
        # Returning .content because response == to all details of the response including date,id's etc.
        # We want just the content


_re_arg_splitter = re.compile(
    #       Match text in quotes as a single group
    #       V                          Match any number of double backslashes so that \" is a valid quote escape but \\" isn't.
    #       V                          V          Match \" within quotes
    #       V                          V          V        Match content within quotes
    #       V                          V          V        V          Match closing quote
    #       V                          V          V        V          V               Match unquoted content
    #       V                          V          V        V          V               V           End match with the end of the
    #       V                          V          V        V          V               V           string, a comma with any amount
    #       V                          V          V        V          V               V           of whitespace, or whitespace.
    #       V                          V          V        V          V               V           V
    r'\s*(?:(?:\"(?P<quoted_text>(?:(?:(?:\\\\)*)|(?:\\\")|(?:[^"]))*)\")|(?:(?P<text>[^\s,，]+)))(?P<tail>$|(?:\s*[,，]\s*)|(?:\s+))'
)
_re_remove_escaped_quote = re.compile(r'((?:[^\\]|^)(?:\\\\)*)\\"')


def split_args(args: str, treat_comma_as_space: bool = False) -> list[str]:
    """Splits a string of arguments into a list of arguments. Arguments are
    separated by spaces, unless `treat_comma_as_space` is `True` and `args`
    contains a comma not enclosed in quotes, in which case arguments are
    separated by commas. Arguments can also be grouped using quotes to include
    spaces or commas without being separated. Quotes escaped using a backslash
    can be included in quoted text. Double backslashes are also replaced with
    single backslashes.

    Examples
    -----------
    .. code-block:: python3
        split_args('A B C D') == ['A', 'B', 'C', 'D']

    .. code-block:: python3
        split_args('A B, C D', False) == ['A B', 'C D']

    .. code-block:: python3
        split_args('A B, C D', True) == ['A', 'B', 'C', 'D']

    .. code-block:: python3
        split_args('A "B C" D', False) == ['A', 'B C', 'D']

    .. code-block:: python3
        # Single escaped backslash
        split_args('A "B\\"C" D', False) == ['A', 'B"C', 'D']
    """
    comma_separated = False

    # Get matches
    matches = []
    for m in _re_arg_splitter.finditer(args):
        matches.append(m)
        comma_separated = comma_separated or (
            not treat_comma_as_space
            and m.group("tail") != ""
            and not m.group("tail").isspace()  # Checks for comma
        )

    # Matches can contain their arg in the groups "text" or "quoted_text"
    if not comma_separated:
        ret = [
            m.group("text") if m.group("text") is not None else m.group("quoted_text")
            for m in matches
        ]
    else:
        # If args are comma separated, group all matches in between commas
        # into a single string.
        ret = []

        # A list of matches that appear together before a comma
        combine: list[re.Match] = []
        for match in matches:
            if match.group("tail") and not match.group("tail").isspace():
                # If match ends with a comma, combine it with previous matches
                # without commas into one single arg.

                if match.group("text"):
                    ret.append(
                        "".join(m.group(0) for m in combine) + match.group("text")
                    )
                elif not combine:
                    # If the match contains text in quotes and there are no
                    # previous matches to combine it with, add only the text
                    # inside of the quotes to the list of arguments.
                    ret.append(match.group("quoted_text"))
                else:
                    ret.append(
                        "".join(m.group(0) for m in combine)
                        + match.group("quoted_text")
                    )
                combine = []
            else:
                combine.append(match)
        if combine:
            if len(combine) == 1 and combine[0].group("quoted_text") is not None:
                # If there is only one match that contains text in quotes add
                # only the text inside of the quotes to the list of arguments.
                last_arg = combine[0].group("quoted_text")
            else:
                # Otherwise, combine all remaining matches into one argument
                last_arg = "".join(m.group(0) for m in combine[:-1])
                # Exclude the tail of the last match
                last_match = combine[-1]
                last_arg += (
                    last_match.group("text")
                    if last_match.group("text") is not None
                    else last_match.group("quoted_text")
                )
            ret.append(last_arg)

    # Replace \" with " and \\ with \
    ret = [_re_remove_escaped_quote.sub(r'\1"', s).replace("\\\\", "\\") for s in ret]

    return ret
