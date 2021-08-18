import discord
import asyncio
from typing import Callable, Generic, Iterator, Optional, Sequence, TypeVar, Union

from core import client
from .paged_message import Paged_Message


_T = TypeVar("_T")


async def reply(
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
                check=lambda m: m.author == member and m.channel == channel,
                timeout=timeout,
            ),
            name="response",
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
                    and r.emoji == _cancel_emoji
                    and u == member,
                    timeout=timeout,
                ),
                name="reaction",
            )
        )

    try:
        # wait for the first task to be completed by the user
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        # get the completed task
        event = list(done)[0]
        # cancel any other pending tasks
        for task in pending:
            try:
                task.cancel()
            except asyncio.CancelledError:
                print(f"Error cancelling {task}")
        # if member reacted, cancel reply request and return None
        if event.get_name() == "reaction":
            await message.clear_reactions()
            await channel.send("Request cancelled")
            return None
        # if member replied, return response
        if event.get_name() == "response":
            response = event.result()
            return response
        print(event)
        return None
    # if function times out waiting for user
    except asyncio.TimeoutError:
        if error_message is not None:
            await channel.send(error_message)
        return None


class User_Selection_Message(Paged_Message, Generic[_T]):
    """Represents an message that can be used to prompt a user `responder` to
    select options from a list.
    """

    selection_reactions = ("1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟", "🇦", "🇧", "🇨", "🇩", "🇪", "🇫", "🇬", "🇭", "🇮", "🇯", "🇰", "🇱", "🇲", "🇳", "🇴", "🇵", "🇶", "🇷", "🇸", "🇹", "🇺", "🇻", "🇼", "🇽", "🇾", "🇿")  # fmt: skip

    auto_delete_msg: bool
    get_multiple_selections: bool

    _reaction_mapping: dict[str, _T]
    _selections: Optional[list[_T]] = None

    _check = "✅"

    def __init__(
        self,
        options: Sequence[_T],
        option_text_generator: Callable[[_T], str],
        responder: Optional[Union[discord.User, discord.Member]],
        title: Optional[str] = None,
        description: Optional[str] = None,
        get_multiple_selections: bool = False,
        auto_delete_msg: bool = True,
    ):
        """Parameters
        -----------
        options: Sequence[_T]
        The options that will be chosen from.

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

    def get_selections(self) -> Optional[list[_T]]:
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


async def selections(
    channel: discord.abc.Messageable,
    options: Sequence[_T],
    option_text_generator: Callable[[_T], str],
    responder: Optional[Union[discord.User, discord.Member]],
    title: Optional[str] = None,
    description: Optional[str] = None,
    auto_delete_msg: bool = True,
    timeout: Optional[float] = 60,
) -> Optional[list[_T]]:
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


async def selection(
    channel: discord.abc.Messageable,
    options: Sequence[_T],
    option_text_generator: Callable[[_T], str],
    responder: Optional[Union[discord.User, discord.Member]],
    title: Optional[str] = None,
    description: Optional[str] = None,
    auto_delete_msg: bool = True,
    timeout: Optional[float] = 60,
) -> Optional[_T]:
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
