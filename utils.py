from core import client

import discord
import asyncio
import math
import re
from typing import (
    Callable,
    Generic,
    Iterable,
    Iterator,
    Optional,
    overload,
    Sequence,
    TypeVar,
    Union,
)

T = TypeVar("T")


re_channel_mention = re.compile(r"<#(\d{18})>")
re_user_mention = re.compile(r"<@!?(\d{18})>")
re_role_mention = re.compile(r"<@&(\d{18})>")
re_username_and_discriminator = re.compile(r"(.+)#(\d{4})")

re_user_mention_or_id = re.compile(r"^(?:<@!?)?(\d{18})>?$")
re_channel_mention_or_id = re.compile(r"^(?:<&)?(\d{18})>?$")


def max_len_string(s: str, maxlen: int, add_ellipsis: bool = True) -> str:
    """Shortens a string to a maximum length if it is too long.

    Parameters
    -----------
    s: str
    The string to shorten.

    maxlen: int
    The maximum length for the string being shortened.

    add_ellipsis: bool
    Whether or not '...' should be added to the end of the string if it is
    shortened. The ellipses are included when calculating the max length.
    """
    if len(s) <= maxlen:
        return s
    elif add_ellipsis:
        if maxlen <= 3:
            return "." * maxlen
        else:
            return f"{s[:maxlen-3]}..."
    else:
        return s[:maxlen]


# TODO: Optimize algorithm
# TODO: Add kwargs support
def format_max_len_string(
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
        format_max_len_string(
            "AB {} CD {}",
            "123",
            456,
            max_total_len=None
        ) == "AB 123 CD 456"

    .. code-block:: python3
        format_max_len_string(
            "AB {} CD",
            123456789
            max_total_len=12
        ) == "AB 123... CD"

    .. code-block:: python3
        format_max_len_string(
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
    The maximum length for the return string. args will be shortened roughly
    evenly until the length of the final string will be within the max length.
    `fstring` will not be shortened to reduce the final string's length.

    max_arg_len: Optional[int]
    The maximum length for every arg. This is applied before shortening args
    to ensure that the return string's length is also within `max_total_len`.

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
        # Limit the length of each arg to max_arg_len if it was given.
        arg_list = [max_len_string(str(arg), max_arg_len, add_ellipsis) for arg in args]
    elif max_total_len is not None:
        # Limit the length of each arg to max_total_len if it was given,
        # because each arg can be at most that long.
        arg_list = [
            max_len_string(str(arg), max_total_len, add_ellipsis) for arg in args
        ]
    else:
        arg_list = [str(arg) for arg in args]

    # If a max length was given for the string, shorten args to fit it.
    if max_total_len is not None:
        # Get a list of the length of every arg
        arg_lens = [len(arg) for arg in arg_list]

        # Get the total lengths of the fstring and args.
        total_fstring_len = sum(len(s) for s in split_fstring)
        total_args_len = sum(arg_lens)

        # The maximum total length of all args in order to keep the return
        # string's length within max_total_len.
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
                arg_list[index] = max_len_string(
                    arg_list[index], shorten_to, add_ellipsis
                )
                # Update the arg's length in the list of arg lengths
                arg_lens[index] = len(arg_list[index])
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
    msg: discord.Message
    The message containing the roles the author wants to assign or remove from themself.
    Roles are separated by commas.
    Role names are preceded by a `+` or `-` to specify whether they should be
    added or removed.
    """

    if not isinstance(msg.author, discord.Member):
        raise TypeError("msg.author must be a member.")

    # split the message into a list of individual roles
    arr = msg.content.split(", ")
    for role in arr:
        # get role name
        name = role.strip()[1:]

        # determine whether the role should be assigned or removed
        if role.startswith("+"):
            try:
                r = discord.utils.get(msg.author.guild.roles, name=name)
                if r is not None:
                    await msg.author.add_roles(r)
                    return
            except (discord.HTTPException, discord.Forbidden):
                pass
            print(f"no role called {role[1:]}")
        elif role.startswith("-"):
            try:
                r = discord.utils.get(msg.author.guild.roles, name=name)
                if r is not None:
                    await msg.author.remove_roles(r)
                    return
            except (discord.HTTPException, discord.Forbidden):
                pass
            print(f"{msg.author} doesn't have the role {role[1:]}")


# TODO: Split into get_member and get_all_members
async def get_member(
    channel: discord.TextChannel,
    m: str,
    responder: Optional[discord.Member] = None,
    *,
    allow_multiple_matches: bool = True,
    timeout: Optional[float] = None,
) -> Optional[discord.Member]:
    """Gets a member in `channel`'s guild from the string `m`.
    If there are multiple members that match the string `m` and
    `allow_multiple_matches` is `True`, then a message will be sent asking for
    one of the matching members to be chosen in `channel`.
    If no member is found, `None` is returned.

    Parameters
    -----------
    channel: discord.TextChannel
    A channel from the guild you want to search for the member `m` in. If
    multiple members that match `m` are found and `allow_multiple_matches` is
    `True`, a message will be sent to this channel asking for one of the
    matching members to be chosen.

    m: str
    The member you want to get. Can be a member mention, member id, username or
    user nickname (both case insensitive), or full username with the
    discriminator (ex. name#1234; case sensitive)

    responder: Optional[discord.Member]
    If a message asking for one of multiple members matching `m` to be chosen
    is sent to `channel` and `responder` is not `None`, only the member `responder`
    can reply with a selection. Otherwise, anyone in `channel` can select a
    member matching `m` from the list.

    allow_multiple_matches: bool
    Whether or not a message should be sent to `channel` asking for a matching
    member to be chosen in the event that multiple members matching `m` are
    found. If multiple members matching `m` are found and
    `allow_multiple_matches` is `False`, the function will return `None`.

    timeout: Optional[float]
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
    user_ping = re_user_mention.fullmatch(m)
    if user_ping:
        out = channel.guild.get_member(int(user_ping.group(1)))
        if out is not None:
            return out

    # Try to parse `m` as a full username, including the discriminator
    username_discriminator = re_username_and_discriminator.fullmatch(m)
    if username_discriminator:
        out = channel.guild.get_member_named(m)
        if out is not None:
            return out
        for member in channel.guild.members:
            if member.name.casefold() == username_discriminator.group(
                1
            ).casefold() and member.discriminator == username_discriminator.group(2):
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

    # FIXME: incompatible type "Callable[[Member], str]"; expected "Callable[[Optional[Member]], str]"
    def member_option_generator(member: discord.Member) -> str:
        return member.mention

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


# FIXME: Base return typehint off of channel_types
# TODO: Split into get_channel and get_all_channels
async def get_channel(
    channel: discord.TextChannel,
    c: str,
    responder: Optional[discord.Member] = None,
    *,
    channel_types: Union[
        type[discord.abc.GuildChannel], tuple[type[discord.abc.GuildChannel], ...]
    ] = discord.abc.GuildChannel,
    include_hidden_channels: bool = False,
    allow_multiple_matches: bool = True,
    timeout: Optional[float] = None,
) -> Optional[discord.abc.GuildChannel]:
    """Gets a channel in `channel`'s guild from the string `c`.
    If there are multiple channels that match the string `c` and
    `allow_multiple_matches` is `True`, then a message will be sent asking for
    one of the matching channels to be chosen in `channel`.

    Parameters
    -----------
    channel: discord.TextChannel
    A channel from the guild you want to search for the channel `c` in. If
    multiple channels that match `c` are found and `allow_multiple_matches` is `True`, a
    message will be sent to this channel asking for one of the matching channels
    to be chosen.

    c: str
    The channel you want to get. Can be a channel mention, channel id, or channel name
    (case insensitive).

    responder: Optional[discord.Member]
    If a message asking for one of multiple channels matching `c` to be chosen
    is sent to `channel` and `responder` is not `None`, only the member
    `responder` can reply with a selection. Otherwise, anyone in `channel` can
    select a channel matching `c` from the list.

    channel_types: Union[
        type[discord.abc.GuildChannel], tuple[type[discord.abc.GuildChannel], ...]
    ]
    The types of channels to search for. For example, to search for only text
    and voice channels pass `(discord.TextChannel, discord.VoiceChannel)`. By
    default includes all guild channels.

    include_hidden_channels: bool
    If `responder` is not `None`, and `include_hidden_channels` is `True`, then
    only channels visible to `responder` will be checked to see if they match
    `c`.

    allow_multiple_matches: bool
    Whether or not a message should be sent to `channel` asking for a matching
    channel to be chosen in the event that multiple channels matching `c` are
    found. If multiple channels matching `c` are found and
    `allow_multiple_matches` is `False`, the function will return `None`.

    timeout: Optional[float]
    If multiple matching channels are found for `c` and `allow_multiple_matches`
    is `True`, `timeout` controls how long in seconds it should take for the
    message asking for a matching channel to be chosen to time out and make the
    function return `None`. If `timeout` is `None`, the default timeout length
    will be used.
    """
    if include_hidden_channels or responder is None:
        include_channel = lambda channel: isinstance(channel, channel_types)
    else:
        include_channel = lambda channel: channel.permissions_for(
            responder
        ).view_channel and isinstance(channel, channel_types)

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


# TODO: Split into get_role and get_all_roles
async def get_role(
    channel: discord.TextChannel,
    r: str,
    responder: Optional[discord.Member] = None,
    *,
    allow_multiple_matches: bool = True,
    timeout: Optional[float] = None,
) -> Optional[discord.Role]:
    """Gets a role in `channel`'s guild from the string `r`.
    If there are multiple roles that match the string `r` and
    `allow_multiple_matches` is `True`, then a message will be sent asking for
    one of the matching roles to be chosen in `channel`.

    Parameters
    -----------
    channel: discord.TextChannel
    A channel from the guild you want to search for the role `r` in. If
    multiple roles that match `r` are found and `allow_multiple_matches` is
    `True`, a message will be sent to this channel asking for one of the
    matching roles to be chosen.

    r: str
    The role you want to get. Can be a role mention, role id, or role name
    (case insensitive).

    responder: Optional[discord.Member
    If a message asking for one of multiple roles matching `r` to be chosen is
    sent to `channel` and `responder` is not `None`, only the member `responder`
    can reply with a selection. Otherwise, anyone in `channel` can select a
    role matching `r` from the list.

    allow_multiple_matches: bool
    Whether or not a message should be sent to `channel` asking for a matching
    role to be chosen in the event that multiple roles matching `r` are
    found. If multiple roles matching `r` are found and `allow_multiple_matches`
    is `False`, the function will return `None`.

    timeout: Optional[float]
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

    # FIXME: incompatible type "Callable[[Role], str]"; expected "Callable[[Optional[Role]], str]"
    def role_option_generator(role: discord.Role) -> str:
        ret = f"{role.mention} ({len(role.members)} member"
        if len(role.members) != 1:
            ret += 's'
        ret += f") [{role.id}]"
        return ret

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


async def wait_for_reply(
    member: discord.Member,
    channel: discord.TextChannel,
    message: Optional[discord.Message] = None,
    timeout: Optional[float] = 60,
    error_message: Optional[str] = "Error: You took too long to respond",
) -> Optional[str]:
    """Waits for a reply from `member` by getting their next message sent
    in `channel` and returns it. Waiting for a response is cancelled and
    `None` is returned if `member` reacts to `message` with ❌.
    If no response is received in `timeout` seconds, `error_message`
    is sent to `channel` if it is not `None` and the function returns `None`.

    Parameters
    ----------
    member: discord.Member
    The member to wait for a reply or reaction from.

    channel: discord.TextChannel
    The channel where the `options` will be sent to be chosen from.

    message: Optional[discord.Message]
    The message that `member` should react to in order to cancel reply request.
    If `message` is `None`, the reply request cannot be cancelled and will only
    wait for a message.

    timeout: Optional[float]
    How long in seconds the function should wait for a message or reaction 
    from `member` before timing out and returning `None`.

    error_message: Optional[str]
    The message sent to `channel` if the function times out waiting for a user event.
    """

    tasks = [
        asyncio.create_task(
            client.wait_for(
                "message",
                check=lambda m: m.author == member
                and m.channel == channel,
                timeout=timeout
            ), 
            name="response"
        )
    ]

    if message is not None:
        _cancel_emoji = "❌"
        await message.add_reaction(_cancel_emoji)
        tasks.append(
            asyncio.create_task(
                client.wait_for(
                    "reaction_add",
                    check=lambda r, u: r.message == message
                    and r.emoji == _cancel_emoji and u == member,
                    timeout=timeout
                ),
                name="reaction"
            )
        )

    try:
        #wait for the first task to be completed by the user
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        #get the completed task
        event = list(done)[0]
        #cancel any other pending tasks
        for task in pending:
            try:
                task.cancel()
            except asyncio.CancelledError:
                print(f"Error cancelling {task}")
        #if member reacted, cancel reply request and return None
        if event.get_name() == "reaction":
            await message.clear_reactions()
            await channel.send("Request cancelled")
            return None
        #if member replied, return response
        if event.get_name() == "response":
            response = event.result()
            return response
        print(event)
        return None
    #if function times out waiting for user
    except asyncio.TimeoutError:
        if error_message is not None:
            await channel.send(error_message)
        return None


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


# to delete empty directories when empty folders are not needed
def delete_empty_directories(directory, base_path):
    # base_path is the inner-most directory that acts as a stopping point
    # in the case that you accidentally delete a folder that's needed even if it's empty
    if directory == base_path:
        return
    # base case: if there is something in the current directory, return
    if any(directory.iterdir()):
        return
    # delete directort if it's empty
    directory.rmdir()
    # set the directory to it's parent i.e the directory before the current directory ---> folder1/folder2/folder3
    # where folder3 is current directory and folder2 is the parent file
    directory = directory.parent
    # run the recursive function with new directory
    delete_empty_directories(directory, base_path)


def paged_footer_generator(
    pg: int, total_pgs: int, pg_turner: Optional[Union[discord.User, discord.Member]]
) -> Optional[str]:
    """A function that generates footers for every embeds that are part of a
    paged set. Returns a string to set the footer to, or `None` if there
    should not be a footer.

    Parameters
    -----------
    pg: int
    The current page number.

    total_pgs: int
    The total number of pages.

    pg_turner: Optional[Union[discord.User, discord.Member]]
    The user that can turn pages (or `None` if any user can turn pages).
    """
    ret = ""
    if pg_turner is not None:
        ret += f" Requested by {pg_turner.name}#{pg_turner.discriminator}"
        if total_pgs > 1:
            ret += " | "
    if total_pgs > 1:
        ret += f"Page {pg}/{total_pgs}. React with ⬅️ or ➡️ to turn the pages."
    return ret if ret else None


class Multi_Page_Embed_Message:
    """A class representing an embed with multiple pages that can be cycled
    using reactions.

    Attributes
    ------------
    page: Optional[int]
    The current page the multi page embed message is on. `None` if the multi
    page embed message has not been sent yet.

    pages: list[discord.Embed]
    The embeds in the multi page embed.

    msg: Optional[discord.Message]
    The message that the multi page embed was sent to. `None` if the message
    has not been sent yet. May also be `None` if the message has been deleted.

    responder: Optional[Union[discord.User, discord.Member]]
    The user that can turn the pages of the embed. If `responder` is `None`
    then any user can turn the pages.
    """

    page: Optional[int]
    pages: list[discord.Embed]
    msg: Optional[discord.Message]
    responder: Optional[Union[discord.User, discord.Member]]
    _continue: bool = False

    _larrow = "⬅️"
    _rarrow = "➡️"

    def __init__(
        self,
        embeds: list[discord.Embed],
        responder: Optional[Union[discord.User, discord.Member]],
        embed_editor: Optional[
            Callable[
                [discord.Embed, "Multi_Page_Embed_Message"], Optional[discord.Embed]
            ]
        ] = None,
    ):
        """Takes a list of embeds to be sent as a single message that can have
        its embeds cycled using reactions.

        Parameters
        -----------
        embeds: list[discord.Embed]
        The embeds to cycle between in the message.

        responder: Optional[Union[discord.User, discord.Member]]
        The user that can turn pages in the embed. If `responder` is
        `None` then any user can turn pages.

        embed_editor: Optional[
            Callable[[discord.Embed, Multi_Page_Embed_Message], Optional[discord.Embed]]
        ]
        A function called once the multi page embed message times out an can
        no longer have its pages cycled. It takes the last embed displayed and
        the multi page embed message as parameters and returns a new embed to
        display in the image. If `embed_editor` is or returns `None` then no
        changes will be made to the message after it becomes inactive.
        """
        self.responder = responder
        self.page = 0
        self.msg = None
        self.pages = embeds
        self._embed_editor = embed_editor

    async def send(
        self,
        channel: discord.abc.Messageable,
        timeout: float = 180,
        blocking: bool = False,
    ) -> None:
        """Sends the multi page embed to `channel`.

        Parameters
        -----------
        channel: discord.abc.Messageable
        The channel to send the multi page embed to.

        timeout: float
        How long in seconds until the multi page embed's pages can no longer
        be cycled. Turning a page resets the timer to `timeout`
        again.

        blocking: bool
        Whether or not the method should block execution until the multi page
        embed's pages can no longer be cycled.
        """
        if self.pages:
            self.page = 0
            self.msg = await channel.send(embed=self.pages[self.page])
            if len(self.pages) > 1:
                self._continue = True
                if blocking:
                    await self._main_loop(timeout)
                else:
                    asyncio.ensure_future(self._main_loop(timeout))
            else:
                self._continue = False

    async def delete(self) -> None:
        if self.msg is not None:
            await self.msg.delete()

    @staticmethod
    def embed_list_from_items(
        items: Iterable[T],
        title_generator: Optional[Callable[[int], Optional[str]]],
        description_generator: Optional[Callable[[int], Optional[str]]],
        field_generator: Callable[[T], tuple[str, str, bool]],
        responder: Optional[Union[discord.User, discord.Member]],
        *,
        description_on_every_page: bool = True,
        max_field_count: int = 25,
        max_embed_len: int = 6000,
        footer_generator: Optional[
            Callable[
                [int, int, Optional[Union[discord.User, discord.Member]]], Optional[str]
            ]
        ] = paged_footer_generator,
    ) -> list[discord.Embed]:
        """Creates a list of `discord.Embed`s from with one field per item
        from `items` with as many fields on one embed as possible.

        Parameters
        -----------
        items: Iterable[T]
        The items to display in the embeds. These will be converted into
        fields to insert into the embeds using `field_generator`.

        title_generator: Optional[Callable[[int], Optional[str]]]
        The function that creates titles for every embed. The current embed
        number is passed to the function. If `title_generator` returns `None`
        then the embed will not be titled. If `title_generator` is `None`,
        then all embeds will not be given titles.

        description_generator: Optional[Callable[[int], Optional[str]]]
        The function that creates descriptions for embeds. The current embed
        number is passed to the function. If `description_generator` returns
        `None`, then the embed will not have a description. If
        `description_generator` is `None`, then all embeds will not be given descriptions.

        field_generator: Callable[[T], tuple[str, str, bool]]
        A function that takes an item from `items` and returns a tuple that
        contains the information used to create a field based on that item.
        The first two elements in the tuple should be strings deciding the
        field's name and value. The third element in the tuple should be a
        boolean controlling whether or not the field should be inline.

        responder: Optional[Union[discord.User, discord.Member]]
        The user that can turn pages in the embed. If `responder` is
        `None` then any user can turn pages.

        max_field_count: int
        The maximum number of fields an embed can have.

        max_embed_len: int
        The maximum length of every embed.

        footer_generator: Optional[
            Callable[[int, int, Optional[Union[discord.User, discord.Member]]], str]
        ]
        A function that generates footers for every embed. Its arguments are
        the current page, the total number of pages, and the user that can
        turn pages (or `None` if any user can turn pages). The function is
        called for every embed once when filling in the embeds. If
        `footer_generator` returns `None` then the embed will not be given a
        footer. If `footer_generator` is `None` then all embeds will not be
        given footers.
        """

        # Tries to estimate the longest possible length for a footer to so
        # that the code can try to keep the length of each embed within
        # max_embed_len. This may not be an accurate estimate, and footers
        # that exceed the length of this estimate will be shortened to keep
        # the length of embeds within max_embed_len
        sample_footer_len = (
            len(footer_generator(999, 999, responder) or "")
            if footer_generator is not None
            else 0
        )

        # Create the first embed
        embed = discord.Embed()
        if title_generator is not None:
            title = title_generator(0)
            if title is not None:
                embed.title = title
        if description_generator is not None:
            description = description_generator(0)
            if description is not None:
                embed.description = description

        embeds = [embed]

        # Fill in embeds
        for item in items:
            # Generate info for item's field
            name, value, inline = field_generator(item)
            if (
                max_embed_len
                <= (len(embed) + len(name) + len(value) + sample_footer_len)
                or len(embed.fields) >= max_field_count
            ):
                # If the field can not fit in the embed, insert it into a new
                # embed.
                embed = discord.Embed()
                if title_generator is not None:
                    title = title_generator(len(embeds))
                    if title is not None:
                        embed.title = title
                if description_generator is not None:
                    description = description_generator(len(embeds))
                    if description is not None:
                        embed.description = description
                embeds.append(embed)

            # Add item's field
            embed.add_field(name=name, value=value, inline=inline)

        # Add footers to embeds
        if footer_generator is not None:
            for index, page in enumerate(embeds):
                max_footer_len = max_embed_len - len(page)
                page_num = index + 1

                footer_text = footer_generator(page_num, len(embeds), responder)

                if footer_text is not None:
                    page.set_footer(
                        text=max_len_string(
                            footer_text,
                            maxlen=max_footer_len,
                            add_ellipsis=False,
                        )
                    )

        return embeds

    async def _update_msg(self):
        """Re-fetches the sent message in order to get an updated list of its
        reactions and to ensure that it still exists.
        """
        if self.msg is not None:
            try:
                self.msg = await self.msg.channel.fetch_message(self.msg.id)
            except discord.HTTPException:
                self.msg = None

    def _reaction_check(
        self,
        reaction: discord.Reaction,
        reactor: Union[discord.User, discord.Member],
    ) -> bool:
        """Returns whether or not the embed handles a reaction."""
        return (
            reaction.message == self.msg
            and reaction.emoji in (self._larrow, self._rarrow)
            and reactor != client.user
        )

    async def _await_reaction(
        self, timeout: Optional[float]
    ) -> tuple[discord.Reaction, Union[discord.User, discord.Member]]:
        return await client.wait_for(
            "reaction_add",
            check=self._reaction_check,
            timeout=timeout,
        )

    async def _handle_reaction(
        self,
        reaction: discord.Reaction,
        reactor: Union[discord.User, discord.Member],
    ) -> None:
        """Handles reactions for turning pages."""

        if self.msg is None:
            return
        if self.responder is None or reactor == self.responder:
            # Make sure that the reactor is someone who can turn
            # the page.
            if self.page is None:
                self.page = 0

            if reaction.emoji == self._larrow:
                # Turn page left
                self.page -= 1
                if self.page < 0:
                    # Loop to the last page
                    self.page = len(self.pages) - 1
                await self.msg.edit(embed=self.pages[self.page])
            else:
                # Turn page right
                self.page += 1
                if self.page >= len(self.pages):
                    # Loop to the first page
                    self.page = 0
                await self.msg.edit(embed=self.pages[self.page])

        # Delete reaction whether page turn was successful or not
        await reaction.remove(reactor)

    def _get_initial_reactions(self) -> list[str]:
        """Returns the reactions that the bot should add to the message
        initially.
        """
        return [self._larrow, self._rarrow]

    async def _setup(self):
        # Add reactions for user selection in non-blocking future so that the
        # bot can begin waiting for and handling reactions without waiting for
        # every reaction to be added.
        async def add_reaction(emoji: str):
            if self.msg is not None and self._continue:
                await self.msg.add_reaction(emoji)

        async def add_reactions(reactions: list[str]):
            if self.msg is None or not self._continue:
                return
            try:
                await asyncio.gather(*(add_reaction(emoji) for emoji in reactions))
            except discord.HTTPException:
                return

        asyncio.ensure_future(add_reactions(self._get_initial_reactions()))

    async def _cleanup(self):
        # After timing out waiting for a page to be cycled remove reactions,
        # update the message's embed and return.

        # Make sure the message still exists.
        await self._update_msg()
        if self.msg is not None:
            # Remove arrow reactions
            for arrow in (self._larrow, self._rarrow):
                try:
                    await self.msg.clear_reaction(arrow)
                except discord.HTTPException:
                    pass

            if self._embed_editor is not None and self.page is not None:
                new_embed = self._embed_editor(self.pages[self.page], self)
                if new_embed is not None:
                    await self.msg.edit(embed=new_embed)

    async def _main_loop(self, timeout: float):
        # Handles turning the multi page embed's pages with reactions.
        self.page = 0

        if self.msg is None:
            return

        await self._setup()
        # Keep turning pages until the function times out waiting for a
        # page to be cycled or an exception is thrown.
        while self._continue:
            try:
                reaction, reactor = await self._await_reaction(timeout)
                await self._handle_reaction(reaction, reactor)
            except asyncio.TimeoutError:
                self._continue = False

        await self._cleanup()


class User_Selection_Message(Multi_Page_Embed_Message, Generic[T]):
    """Represents an message that can be used to prompt a user `responder` to
    select options from a list.
    """

    selection_reactions = ("1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟", "🇦", "🇧", "🇨", "🇩", "🇪", "🇫", "🇬", "🇭", "🇮", "🇯", "🇰", "🇱", "🇲", "🇳", "🇴", "🇵", "🇶", "🇷", "🇸", "🇹", "🇺", "🇻", "🇼", "🇽", "🇾", "🇿")  # fmt: skip

    auto_delete_msg: bool
    get_multiple_selections: bool

    _reaction_mapping: dict[str, T]
    _selections: Optional[list[T]] = None

    _check = "✅"

    def __init__(
        self,
        options: Sequence[T],
        option_text_generator: Callable[[T], str],
        responder: Optional[Union[discord.User, discord.Member]],
        title: Optional[str] = None,
        description: Optional[str] = None,
        get_multiple_selections: bool = False,
        auto_delete_msg: bool = True,
    ):
        """Parameters
        -----------
        options: Sequence[T]
        The options that will be chosen from.

        option_text_generator: Callable[[T], str]
        A function to convert an option from `options` to a string
        representation that can be sent in a message to `channel` to be chosen
        by a user.

        responder: Optional[Union[discord.User, discord.Member]]
        If `responder` is not `None`, then `responder` will be mentioned in
        the message asking for a selection to be made from `options`, and only
        `responder` will be able to make a selection. If `responder` is `None`,
        anyone who can send messages in `channel` will be able to make a selection
        from `options`.

        title: Optional[str]
        The title for the embeds selection, or no title if `None`.

        description: Optional[str]
        The description for the embeds being sent. If `None`, a default
        description will be used.

        get_multiple_selections: bool
        Whether or not the message should stop waiting for reactions after
        getting one. If `True`, the message will wait for a check emoji to be
        added before stopping message collection.

        auto_delete_msg: bool
        Whether or not the message should be removed from `channel` once
        `responder` makes their selection(s).
        """
        # Make sure options list is valid.
        if not options:
            raise ValueError(f"options list can not be empty.")
        if len(options) > len(self.selection_reactions):
            raise ValueError(
                f"options list may have a maximum of {len(self.selection_reactions)} elements."
            )

        # If no description provided, use a default description.
        if description is None:
            if get_multiple_selections:
                description = f"React to choose the items you wish to select.\nReact with {self._check} once you are done."
            else:
                description = "React to choose an item."
        elif not description:
            description = None

        # Use a generator to create option embeds.
        def field_generator() -> Iterator[tuple[str, str, bool]]:
            for option, emoji in zip(options, self.selection_reactions):
                yield emoji, option_text_generator(option), True

        fg = field_generator()

        embeds = self.embed_list_from_items(
            options,
            lambda pg: title,
            lambda i: description,
            lambda option: next(fg),
            responder,
        )

        super().__init__(embeds, responder, embed_editor=None)

        self.auto_delete_msg = auto_delete_msg
        self.get_multiple_selections = get_multiple_selections
        self._reaction_mapping = {
            emoji: opt for emoji, opt in zip(self.selection_reactions, options)
        }

    async def send(
        self,
        channel: discord.abc.Messageable,
        timeout: float = 180,
        blocking: bool = True,
    ) -> None:
        """Parameters
        -----------TODO
        channel: discord.abc.Messageable
        The channel where the `options` will be sent to be chosen from.

        timeout: float
        How long the message can go without a valid reaction before the
        message times out and returns `None`. Measured in seconds.

        blocking: bool
        Must remain `True`.
        """
        if not blocking:
            # TODO: Add support for non-blocking user list selection
            raise NotImplementedError(
                "Non-blocking user list selection not implemented."
            )

        if self.pages:
            self.page = 0
            self.msg = await channel.send(embed=self.pages[self.page])
            self._continue = True
            await self._main_loop(timeout)

    def get_selections(self) -> Optional[list[T]]:
        """Return a list of the selections made by `responder`, or `None` if
        the message timed out waiting for a response.
        """
        return self._selections

    async def _find_all_selections(self) -> None:
        if self.msg is None:
            return
        self._selections = []

        async def check_reaction(reaction) -> bool:
            # Adds valid selections to `self._selections` and returns whether
            # or not the reaction was a checkmark from `responder`.

            # Check to see if emoji is valid
            if (
                reaction.emoji != self._check
                and reaction.emoji not in self._reaction_mapping.keys()
            ):
                return False

            # Check to see if reactor is valid
            if self.responder is not None:
                if await reaction.users().get(id=self.responder.id) is None:
                    return False
            else:
                if await reaction.users().find(lambda u: u != client.user) is not None:
                    return False

            # Handle reaction
            if reaction.emoji == self._check:
                return True
            else:
                if self._selections is None:
                    self._selections = []
                self._selections.append(self._reaction_mapping[reaction.emoji])
                return False

        has_check = any(
            await asyncio.gather(*(check_reaction(r) for r in self.msg.reactions))
        )
        if self.get_multiple_selections:
            # If `responder` made valid selections but timed out without
            # confirming their choices with a check, set selections to `None`
            if not has_check:
                self._selections = None
        else:
            if not self._selections:
                # If no selections were made, set `self._selections` to `None`
                self._selections = None

    def _reaction_check(
        self,
        reaction: discord.Reaction,
        reactor: Union[discord.User, discord.Member],
    ) -> bool:
        return (
            reaction.message == self.msg
            and reactor != client.user
            and (
                reaction.emoji in (self._larrow, self._rarrow, self._check)
                or reaction.emoji in self._reaction_mapping.keys()
            )
        )

    async def _handle_reaction(
        self,
        reaction: discord.Reaction,
        reactor: Union[discord.User, discord.Member],
    ) -> None:
        # Handle page turns
        if len(self.pages) > 1 and super()._reaction_check(reaction, reactor):
            await super()._handle_reaction(reaction, reactor)
            return

        if self.responder is None or reactor == self.responder:
            # Handle checks and selections from responders
            if self.get_multiple_selections and reaction.emoji == self._check:
                self._continue = False
                return
            if reaction.emoji in self._reaction_mapping.keys():
                if not self.get_multiple_selections:
                    self._continue = False
                    self._selections = [self._reaction_mapping[reaction.emoji]]  # type: ignore
                return

        # Delete reaction if it was invalid
        await reaction.remove(reactor)

    def _get_initial_reactions(self) -> list[str]:
        if len(self.pages) > 1:
            # Add arrows if pages can be turned
            ret = super()._get_initial_reactions()
        else:
            ret = []
        if self.get_multiple_selections:
            ret.append(self._check)
        ret += list(self._reaction_mapping.keys())[:10]
        return ret

    async def _cleanup(self):
        await self._update_msg()
        if self.get_multiple_selections:
            await self._find_all_selections()
        if self.auto_delete_msg:
            await self.delete()


async def user_select_multiple_from_list(
    channel: discord.abc.Messageable,
    options: Sequence[T],
    option_text_generator: Callable[[T], str],
    responder: Optional[Union[discord.User, discord.Member]],
    title: Optional[str] = None,
    description: Optional[str] = None,
    auto_delete_msg: bool = True,
    timeout: Optional[float] = 60,
) -> Optional[list[T]]:
    """Sends a message to `channel` prompting `responder` to choose multiple
    selections from `options` using reactions. Returns a list of the selected
    options, or `None` if the function times out waiting for the user to
    respond. See `User_Selection_Message` for more details on the arguments.
    """
    selection_embed = User_Selection_Message(
        options,
        option_text_generator,
        responder,
        title=title,
        description=None,
        get_multiple_selections=True,
        auto_delete_msg=auto_delete_msg,
    )
    if timeout:
        await selection_embed.send(channel, timeout=timeout)
    else:
        await selection_embed.send(channel)

    return selection_embed.get_selections()


async def user_select_from_list(
    channel: discord.abc.Messageable,
    options: Sequence[T],
    option_text_generator: Callable[[T], str],
    responder: Optional[Union[discord.User, discord.Member]],
    title: Optional[str] = None,
    description: Optional[str] = None,
    auto_delete_msg: bool = True,
    timeout: Optional[float] = 60,
) -> Optional[T]:
    """Sends a message to `channel` prompting `responder` to choose a
    selection from `options` using reactions. Returns a the selected option,
    or `None` if the function times out waiting for the user to respond. See
    `User_Selection_Message` for more details on the arguments.
    """
    selection_embed = User_Selection_Message(
        options,
        option_text_generator,
        responder,
        title=title,
        description=None,
        get_multiple_selections=False,
        auto_delete_msg=auto_delete_msg,
    )
    if timeout:
        await selection_embed.send(channel, timeout=timeout)
    else:
        await selection_embed.send(channel)

    selections = selection_embed.get_selections()
    if selections is not None:
        return selections[0]
    return selections
