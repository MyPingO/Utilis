import discord
import asyncio
from typing import (
    Any,
    Callable,
    Generic,
    Iterable,
    Iterator,
    Mapping,
    Optional,
    Sequence,
    TypeVar,
    Union,
)

from core import client
from .paged_message import Paged_Message
from . import errors, std_embed


_T = TypeVar("_T")


async def reply(
    member: discord.Member,
    channel: discord.TextChannel,
    message: Optional[discord.Message] = None,
    timeout: Optional[float] = 60,
    error_message: Optional[str] = None,
) -> discord.Message:
    """Waits for a reply from `member` by getting their next message sent
    in `channel` and returns it. Waiting for a response is cancelled and
    raises an error if `member` reacts to `message` with ❌.
    If no response is received in `timeout` seconds, `error_message`
    is sent to `channel` if it is not `None` and the function raises an error.

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
    from `member` before timing out and raising an error.

    error_message: Optional[str]
    The message sent to `channel` if the function times out waiting for a user
    event. Uses the default error message if `None`.
    """
    _cancel_emoji = "❌"

    events = [
        {
            "event": "message",
            "check": lambda m: m.author == member and m.channel == channel,
            "timeout": timeout,
        }
    ]

    if message is not None:
        await message.add_reaction(_cancel_emoji)
        events.append(
            {
                "event": "reaction_add",
                "check": lambda r, u: r.message == message
                and r.emoji == _cancel_emoji
                and u == member,
                "timeout": timeout,
            }
        )

    try:
        event_type, result = await client_events(events)
        # if member reacted, cancel reply request and return None
        if event_type == "reaction_add":
            await message.clear_reaction(_cancel_emoji)  # type: ignore
            raise errors.UserCancelError()
        # if member replied, return response
        elif event_type == "message":
            if message is not None:
                await message.clear_reaction(_cancel_emoji)
            return result
        else:
            raise RuntimeError(f"Unexpected event type {event_type}")
    # if function times out waiting for user
    except asyncio.TimeoutError:
        if message is not None:
            await message.clear_reaction(_cancel_emoji)
        if error_message is not None:
            raise errors.UserTimeoutError(error_message)
        else:
            raise errors.UserTimeoutError()


async def confirmation(
    member: discord.Member,
    channel: discord.TextChannel,
    msg: Optional[discord.Message] = None,
    title: Optional[str] = "Confirm or Deny",
    description: Optional[str] = None,
    timeout: Optional[float] = 60,
    delete_after: bool = False,
    error_message: Optional[str] = "Error: You took too long to respond",
    timeout_returns_false: bool = True,
) -> bool:
    """Sends an embed to the passed channel, requesting a reaction confirmation.

    Parameters
    ----------
    member: discord.Member
    The member to request verification from.

    channel: discord.TextChannel
    The channel where the embed will be sent to request verification from the member.

    msg: Optional[discord.Message]
    A discord message to prompt for confirmation. If None, a message will be created
    using 'title'

    title: Optional[str]
    The title of the embed.

    description: Optional[str]
    A descriptive message explaining what the member is being asked to
    confirm or deny.

    timeout: Optional[float]
    How long in seconds the function should wait for a reaction
    from `member` before timing out and returning `False`.

    delete_after: bool
    Determines whether or not to delete the message requesting confirmation.

    error_message: Optional[str]
    If `timeout_returns_false` is `True`, `error_message` wil be sent to
    `channel` if the function times out waiting for a user event. If
    `timeout_returns_false` is `False`, after timing out a `UserTimeoutError`
    will be raised with `error_message` as the argument.

    timeout_returns_false: bool
    If `True`, the function will return `False` after timing out waiting for
    user input. If `False`, a `UserTimeoutError` will be raised instead.
    """

    confirm_emoji = "✅"
    deny_emoji = "❌"
    if msg is None:
        # send the embed requesting confirmation and add the appropriate reactions
        msg = await std_embed.send_input(
            channel, title=title, description=description, author=member
        )
    await msg.add_reaction(confirm_emoji)
    await msg.add_reaction(deny_emoji)

    # wait for the user's reaction response
    try:
        reaction, user = await client.wait_for(
            "reaction_add",
            check=lambda r, u: r.message == msg
            and r.emoji in (confirm_emoji, deny_emoji)
            and u == member,
            timeout=timeout,
        )

        if delete_after:
            await msg.delete()
        if reaction.emoji == confirm_emoji:
            return True
        return False
    except asyncio.TimeoutError:
        if delete_after:
            await msg.delete()
        if timeout_returns_false:
            if error_message is not None:
                await std_embed.send_error(
                    channel, description=error_message, author=member
                )
            return False
        else:
            if error_message is not None:
                raise errors.UserTimeoutError(error_message)
            else:
                raise errors.UserTimeoutError()


class User_Selection_Message(Paged_Message, Generic[_T]):
    """Represents an message that can be used to prompt a user `responder` to
    select options from a list.
    """

    default_selection_reactions: tuple[str, ...] = ("1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟", "🇦", "🇧", "🇨", "🇩", "🇪", "🇫", "🇬", "🇭", "🇮", "🇯", "🇰", "🇱", "🇲", "🇳", "🇴", "🇵", "🇶", "🇷", "🇸", "🇹", "🇺", "🇻", "🇼", "🇽", "🇾", "🇿")  # fmt: skip

    auto_delete_msg: bool
    get_multiple_selections: bool

    _reaction_mapping: Mapping[str, _T]
    _selections: list[_T]

    _check = "✅"

    def __init__(
        self,
        options: Union[Mapping[str, _T], Sequence[_T]],
        option_text_generator: Callable[[_T], str],
        responder: Optional[Union[discord.User, discord.Member]],
        title: Optional[str] = None,
        description: Optional[str] = None,
        get_multiple_selections: bool = False,
        auto_delete_msg: bool = True,
        color: Optional[Union[discord.Color, int]] = std_embed.Colors.INPUT,
    ):
        """Parameters
        -----------
        options: [Mapping[str, _T], Sequence[_T]],
        The options that will be chosen from. Can either be a mapping of
        emojis to items, or a list of items. If a list of items is passed,
        reaction emojis will be automatically assigned from
        `default_selection_reactions`.

        option_text_generator: Callable[[_T], str]
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
        self._selections = []

        # Make sure options list is valid.
        if not options:
            raise ValueError(f"options can not be empty.")
        if isinstance(options, Sequence):
            if len(options) > len(self.default_selection_reactions):
                raise ValueError(
                    "options list may have a maximum of "
                    f"{len(self.default_selection_reactions)}"
                    " elements."
                )

        # If no description provided, use a default description.
        if description is None:
            if get_multiple_selections:
                description = f"React to choose the items you wish to select.\nReact with {self._check} once you are done."
            else:
                description = "React to choose an item."
        elif not description:
            description = None

        options_list: Iterable[_T]
        if isinstance(options, Sequence):
            options_list = options
            # Use a generator to create option embeds.
            def sequence_field_generator() -> Iterator[tuple[str, str, bool]]:
                for option, emoji in zip(options, self.default_selection_reactions):
                    yield emoji, option_text_generator(option), True

            fg = sequence_field_generator()
        elif isinstance(options, Mapping):
            options_list = options.values()
            # Use a generator to create option embeds.
            def mapping_field_generator() -> Iterator[tuple[str, str, bool]]:
                for emoji, option in options.items():
                    yield emoji, option_text_generator(option), True

            fg = mapping_field_generator()
        else:
            raise ValueError(
                "options must be a sequence of items or a mapping of emojis to items."
            )

        embeds = self.embed_list_from_items(
            options_list,
            lambda pg: title,
            lambda i: description,
            lambda option: next(fg),
            responder,
            color=color,
        )

        super().__init__(embeds, responder, embed_editor=None)

        self.auto_delete_msg = auto_delete_msg
        self.get_multiple_selections = get_multiple_selections
        if isinstance(options, Mapping):
            self._reaction_mapping = options
        else:
            self._reaction_mapping = {
                emoji: opt
                for emoji, opt in zip(self.default_selection_reactions, options)
            }

    async def send(
        self,
        channel: discord.abc.Messageable,
        timeout: float = 180,
        blocking: bool = True,
    ) -> None:
        """Sends the message so that the user can make a selection. If no
        response is made within `timeout` seconds, an error is raised.

        Parameters
        -----------
        channel: discord.abc.Messageable
        The channel where the `options` will be sent to be chosen from.

        timeout: float
        How many seconds the message can go without a valid reaction before
        the message times out and raises an error.

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

    def get_selections(self) -> list[_T]:
        """Return a list of the selections made by `responder`."""
        return self._selections

    async def _find_all_selections(self) -> None:
        if self.msg is None:
            return

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
                self._selections.append(self._reaction_mapping[reaction.emoji])
                return False

        has_check = any(
            await asyncio.gather(*(check_reaction(r) for r in self.msg.reactions))
        )
        if self.get_multiple_selections:
            # If `responder` made valid selections but timed out without
            # confirming their choices with a check, raise an error
            if not has_check:
                await self.delete()
                raise errors.UserTimeoutError()
        else:
            if not self._selections:
                # If no selections were made, raise an error
                await self.delete()
                raise errors.UserTimeoutError()

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
        if not self.get_multiple_selections and not self._selections:
            raise errors.UserTimeoutError()


async def selections(
    channel: discord.abc.Messageable,
    options: Union[Mapping[str, _T], Sequence[_T]],
    option_text_generator: Callable[[_T], str],
    responder: Optional[Union[discord.User, discord.Member]],
    title: Optional[str] = None,
    description: Optional[str] = None,
    auto_delete_msg: bool = True,
    timeout: Optional[float] = None,
) -> list[_T]:
    """Sends a message to `channel` prompting `responder` to choose multiple
    selections from `options` using reactions. Returns a list of the selected
    options, or raises an error if the function times out waiting for the user
    to respond. See `User_Selection_Message` for more details on the arguments.
    """
    selection_embed = User_Selection_Message(
        options,
        option_text_generator,
        responder,
        title=title,
        description=description,
        get_multiple_selections=True,
        auto_delete_msg=auto_delete_msg,
    )
    if timeout is not None:
        await selection_embed.send(channel, timeout=timeout)
    else:
        await selection_embed.send(channel)

    return selection_embed.get_selections()


async def selection(
    channel: discord.abc.Messageable,
    options: Union[Mapping[str, _T], Sequence[_T]],
    option_text_generator: Callable[[_T], str],
    responder: Optional[Union[discord.User, discord.Member]],
    title: Optional[str] = None,
    description: Optional[str] = None,
    auto_delete_msg: bool = True,
    timeout: Optional[float] = None,
) -> _T:
    """Sends a message to `channel` prompting `responder` to choose a
    selection from `options` using reactions. Returns a the selected option,
    or raises an error if the function times out waiting for the user to
    respond. See `User_Selection_Message` for more details on the arguments.
    """
    selection_embed = User_Selection_Message(
        options,
        option_text_generator,
        responder,
        title=title,
        description=description,
        get_multiple_selections=False,
        auto_delete_msg=auto_delete_msg,
    )
    if timeout is not None:
        await selection_embed.send(channel, timeout=timeout)
    else:
        await selection_embed.send(channel)

    selections = selection_embed.get_selections()
    if selections is not None:
        return selections[0]
    return selections


async def client_events(events: list[dict[str, Any]]) -> tuple[str, Any]:
    """Takes a list of client events and returns the name and result of the
    first client event to finish.

    Parameters
    -----------
    events: list[dict[str, Any]]
    A list of arguments to be passed to `client.wait_for`. The keys and values
    should be parameters and arguments for `client.wait_for`, with `"event"`
    being a required key/parameter.
    """
    tasks = [asyncio.create_task(client.wait_for(**e), name=e["event"]) for e in events]
    done, pending = await asyncio.wait(
        tasks,
        return_when=asyncio.FIRST_COMPLETED,
    )
    for task in pending:
        try:
            task.cancel()
        except asyncio.CancelledError as e:
            print(f"Error cancelling task {task}: {e}")
    e = done.pop()
    return e.get_name(), e.result()
