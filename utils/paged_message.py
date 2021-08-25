import discord
import asyncio

from typing import Callable, Iterable, Optional, TypeVar, Union

from . import fmt
from core import client

_T = TypeVar("_T")


def get_paged_footer(
    pg: int,
    total_pgs: int,
    pg_turner: Optional[Union[discord.User, discord.Member]],
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


class Paged_Message:
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
            Callable[[discord.Embed, "Paged_Message"], Optional[discord.Embed]]
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
            Callable[[discord.Embed, Paged_Message], Optional[discord.Embed]]
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

    # TODO: Split method to support generators
    @staticmethod
    def embed_list_from_items(
        items: Iterable[_T],
        title_generator: Optional[Callable[[int], Optional[str]]],
        description_generator: Optional[Callable[[int], Optional[str]]],
        field_generator: Callable[[_T], tuple[str, str, bool]],
        responder: Optional[Union[discord.User, discord.Member]],
        *,
        description_on_every_page: bool = True,
        max_field_count: int = 25,
        max_embed_len: int = 6000,
        footer_generator: Optional[
            Callable[
                [int, int, Optional[Union[discord.User, discord.Member]]], Optional[str]
            ]
        ] = get_paged_footer,
        color: Optional[Union[discord.Color, int]] = None,
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

        color: Optional[Union[discord.Color, int]]
        The color of every embed. Left at the default color if `None`.
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
        if color is not None:
            embed.color = color

        if responder is not None:
            # Set the author to the responder, if there is one. The author's
            # name is later replaced with the title if there is one.
            embed.set_author(
                name=responder.name, icon_url=responder.avatar_url_as(format="png")
            )

        if title_generator is not None:
            title = title_generator(0)
            if title is not None:
                if responder is not None:
                    # If there is a responder, put the title where author
                    # name should go instead to keep the title next to the
                    # responder's icon.
                    embed.set_author(
                        name=title, icon_url=responder.avatar_url_as(format="png")
                    )
                else:
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
                if color is not None:
                    embed.color = color
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
                        text=fmt.bound_str(
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
