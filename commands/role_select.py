import discord
import asyncio
import datetime
import re

from typing import Literal, Optional, Union

from core import client
from db import db
from bot_cmd import Bot_Command, bot_commands, Bot_Command_Category
from utils import errors, find, fmt, get, paged_message, std_embed

from main import bot_prefix
from commands.cmd_help import help_cmd


EmojiType = Union[str, discord.PartialEmoji, discord.Emoji]


class Role_Select_Command(Bot_Command):
    category = Bot_Command_Category.MODERATION
    name = "role_select"
    short_help = "Creates messages for letting people assign their own roles."
    long_help = long_help = f"""Creates messages for letting people assign their own roles.
    Usage:
    `{bot_prefix}role_select create` - Create a new role selection message.
    `{bot_prefix}role_select list (channel)` - List existing role selection messages. Specify a channel to only show messages in that channel.
    """

    message_ids: set[int] = set()

    _re_custom_emoji = re.compile(r"<:(?P<name>[A-Za-z_\d~]{2,32}):(?P<id>\d{18})>")

    def __init__(self):
        self._handling_messages = False

        with db.cursor() as cursor:
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS role_select_messages (
                    message_id BIGINT NOT NULL,
                    channel_id BIGINT NOT NULL,
                    guild_id BIGINT NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    description VARCHAR(2000),
                    allow_multiple_selections BIT(1),
                    creator_id BIGINT NOT NULL,
                    created_on DATETIME NOT NULL,
                    PRIMARY KEY (message_id)
                );"""
            )
            # The largest emoji I could find is 🏴󠁧󠁢󠁷󠁬󠁳󠁿, which fits in a VARCHAR(7)
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS role_select_reactions (
                    message_id BIGINT NOT NULL,
                    emoji VARCHAR(7) NOT NULL,
                    role_id BIGINT NOT NULL,
                    FOREIGN KEY (message_id)
                        REFERENCES role_select_messages(message_id)
                        ON DELETE CASCADE
                );"""
            )
            db.commit()

    def can_run(self, location, member):
        if not isinstance(location, (discord.Guild, discord.TextChannel)):
            return False
        return member is not None and member.guild_permissions.administrator

    async def run(self, msg: discord.Message, args: str):
        if not args:
            await help_cmd.get_command_info(self, msg.channel, msg.author)
        else:
            arg_list = args.split(" ", 1)
            first_arg = arg_list[0].casefold()
            remaining_args = arg_list[1] if len(arg_list) > 1 else None
            if first_arg == "create":
                if remaining_args is not None:
                    raise errors.InvalidInputError(
                        f"`{self.name} create` does not take any arguments"
                    )
                await self.create_new_selector(msg.channel, msg.author)  # type: ignore
            elif first_arg == "list":
                await self.list_selectors(
                    msg.channel, msg.author, remaining_args
                )  # type:ignore
            else:
                raise errors.InvalidInputError(
                    fmt.format_maxlen(
                        "Invalid arguments `{}` for " f"`{self.name}`",
                        args,
                    )
                )

    async def on_ready(self):
        # TODO: Check if roles still exist
        # TODO: Check if emojis still exist
        await self._check_all_messages()
        if not self._handling_messages:
            self._handling_messages = True
            await self._handle_reactions()

    async def create_new_selector(
        self, channel: discord.TextChannel, creator: discord.Member
    ):
        # Check to see what role selection messages still exist in the guild.
        # This allows admins to delete a role selection message and then
        # replace it with a new one that is now able
        await self._check_guild_messages(channel.guild.id)

        prompt_title = "Create role selector"

        message = await std_embed.send_input(
            channel,
            title=prompt_title,
            author=creator,
            description="Enter a title for the role selection message",
        )
        name = (await get.reply(creator, channel)).content
        while not name or 100 < len(name):
            message = await std_embed.send_reinput(
                channel,
                title=prompt_title,
                author=creator,
                description="Title must be between 1 and 100 characters. "
                "Enter a title for the role selection message",
            )
            name = (await get.reply(creator, channel)).content

        message = await std_embed.send_input(
            channel,
            title=prompt_title,
            author=creator,
            description="Enter a description for the role selection message "
            "or react with ❌ to not have a description",
        )
        description: Optional[str]
        try:
            description = (await get.reply(creator, channel, message)).content
            while len(description) > 2000:
                message = await std_embed.send_input(
                    channel,
                    title=prompt_title,
                    author=creator,
                    description="Description must be 2000 characters or less. "
                    "Enter a description for the role selection message "
                    "or react with ❌ to not have a description",
                )
                description = (await get.reply(creator, channel, message)).content
                if not description:
                    # Check to see if an empty message was sent for the description
                    description = None
        except errors.UserCancelError:
            description = None

        emojis_to_roles: dict[str, list[discord.Role]] = {}

        # TODO: Stop collecting emojis once max reaction count is hit
        getting_roles = True
        while getting_roles:
            emoji = await self._get_emoji(
                channel,
                creator,
                prompt_title,
                "Send or react with an emoji to assign roles to",
                emojis_to_roles,
            )
            roles = await self._get_roles(
                channel, creator, prompt_title, f"Choose roles to assign to {emoji}"
            )
            emojis_to_roles[emoji] = roles

            getting_roles = await get.confirmation(
                creator,
                channel,
                title=prompt_title,
                description="Keep adding emojis?",
                timeout_returns_false=False,
            )

        allow_multiple_selections: Optional[bool]
        if len(emojis_to_roles) > 1:
            allow_multiple_selections = await get.confirmation(
                creator,
                channel,
                title=prompt_title,
                description="Allow multiple roles to be selected from the message?",
                timeout_returns_false=False,
            )
        else:
            allow_multiple_selections = None

        send_channel = await self._get_channel(
            channel,
            creator,
            prompt_title,
            "Choose a channel to send the selection message in",
        )
        # TODO: Add a confirmation message

        selector_embed = std_embed.get_success(title=name, description=description)
        for emoji in emojis_to_roles.keys():
            selector_embed.add_field(
                name=emoji,
                value=", ".join((r.mention for r in emojis_to_roles[emoji])),
                inline=False,
            )
        selector_message = await send_channel.send(embed=selector_embed)
        for emoji in emojis_to_roles.keys():
            await selector_message.add_reaction(emoji)

        with db.cursor() as c:
            c.execute(
                """INSERT INTO role_select_messages VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s
                );""",
                (
                    selector_message.id,
                    send_channel.id,
                    send_channel.guild.id,
                    name,
                    description,
                    allow_multiple_selections,
                    creator.id,
                    datetime.datetime.utcnow(),
                ),
            )
            emoji_to_role_info = [
                (
                    selector_message.id,
                    e,
                    r.id,
                )
                for e, roles in emojis_to_roles.items()
                for r in roles
            ]
            c.executemany(
                """INSERT INTO role_select_reactions VALUES (
                    %s, %s, %s
                );""",
                emoji_to_role_info,
            )
            db.commit()
        self.message_ids.add(selector_message.id)
        await std_embed.send_success(
            channel,
            title="Created role selection message!",
            description="[Created new role selection message in "
            f"{send_channel.mention}]({selector_message.jump_url})",
            author=creator,
        )

    async def list_selectors(
        self,
        channel: discord.TextChannel,
        requester: discord.Member,
        list_channel_name: Optional[str],
    ):
        await self._check_guild_messages(channel.guild.id)
        if list_channel_name is None:
            with db.cursor() as c:
                c.execute(
                    """SELECT message_id, channel_id, name FROM role_select_messages
                    WHERE guild_id = %s;""",
                    (channel.guild.id,),
                )
                links = [
                    (
                        name,
                        f"[Link]"
                        f"({channel.guild.get_channel(c_id).get_partial_message(m_id).jump_url})",
                    )
                    for m_id, c_id, name in c.fetchall()
                ]
        else:
            list_channel = await find.channel(
                channel, list_channel_name, requester, channel_types=discord.TextChannel
            )
            if list_channel is None:
                raise errors.InvalidInputError(
                    fmt.format_maxlen("No channel {} found", list_channel_name)
                )
            with db.cursor() as c:
                c.execute(
                    """SELECT message_id, name FROM role_select_messages
                    WHERE channel_id = %s AND guild_id = %s;""",
                    (list_channel.id, channel.guild.id),
                )
                links = [
                    (name, f"[Link]({list_channel.get_partial_message(m_id).jump_url})")
                    for m_id, name in c.fetchall()
                ]

        title = "Role selection messages"
        if list_channel_name is not None:
            title += f" | {list_channel.name.upper()}"
        if not links:
            await std_embed.send_info(
                channel,
                title=title,
                description="No role selection messages in "
                f"{list_channel.mention if list_channel_name is not None else channel.guild}",
                author=requester,
            )
        else:
            description = (
                f"Role selection messages in "
                f"{channel.guild if list_channel_name is None else list_channel.mention}"
            )
            embeds = paged_message.Paged_Message.embed_list_from_items(
                links,
                lambda pg: title,
                lambda pg: description,
                lambda link: (link[0], link[1], True),
                requester,
                footer_generator=paged_message.get_paged_footer,
                color=std_embed.Colors.INFO,
            )
            embed_editor = lambda e: e.set_footer(
                text=paged_message.get_paged_footer(1, 1, requester)
            )
            await paged_message.Paged_Message(
                embeds, requester, embed_editor if len(embeds) > 1 else None
            ).send(channel)

    async def _check_all_messages(self):
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT message_id, channel_id, guild_id FROM role_select_messages;"
            )
            results = cursor.fetchall()

        valid_message_ids: set[int] = set()
        invalid_message_ids: list[tuple[int]] = []
        for message_id, channel_id, guild_id in results:
            if await self._check_message_exists(guild_id, channel_id, message_id):
                valid_message_ids.add(message_id)
            else:
                invalid_message_ids.append((message_id,))
        self.message_ids = valid_message_ids
        if invalid_message_ids:
            with db.cursor() as cursor:
                cursor.executemany(
                    "DELETE FROM role_select_messages WHERE message_id = %s;",
                    invalid_message_ids,
                )
                db.commit()

    async def _check_guild_messages(self, guild_id: int):
        with db.cursor() as cursor:
            cursor.execute(
                """SELECT message_id, channel_id FROM role_select_messages
                WHERE guild_id = %s;""",
                (guild_id,),
            )
            results = cursor.fetchall()
        valid_message_ids = set()
        invalid_message_ids = set()
        for message_id, channel_id in results:
            if await self._check_message_exists(guild_id, channel_id, message_id):
                valid_message_ids.add(message_id)
            else:
                invalid_message_ids.add(message_id)
        # Update message id cache
        self.message_ids.update(valid_message_ids)
        self.message_ids.difference_update(invalid_message_ids)
        # Remove messages that no longer exist from SQL tables
        if invalid_message_ids:
            with db.cursor() as cursor:
                cursor.executemany(
                    "DELETE FROM role_select_messages WHERE message_id = %s;",
                    [(m_id,) for m_id in invalid_message_ids],
                )
                db.commit()

    async def _check_message_exists(
        self, guild_id: int, channel_id: int, message_id: int
    ) -> bool:
        try:
            if (guild := client.get_guild(guild_id)) is not None:
                bot_member = guild.get_member(client.user.id)
                if not bot_member.guild_permissions.administrator:
                    # If the bot is not an administrator, assume that the
                    # message is still valid and will be re-admined
                    # eventually
                    return True
                if (channel := guild.get_channel(channel_id)) is not None:
                    try:
                        await channel.fetch_message(message_id)
                    except discord.NotFound:
                        pass
                    else:
                        # If the message was found, mark it as valid
                        return True
        except Exception as e:
            self.log.error(fmt.format_error(e))
            # When in doubt, assume the message is valid
            return True
        # If guild, channel or message was not found, the message does not exist
        return False

    async def _handle_reactions(self):
        self._handling_reactions = True
        while self._handling_reactions:
            try:
                event, result = await get.client_events(
                    [
                        {
                            "event": "raw_reaction_add",
                            "check": self._reaction_check,
                            "timeout": None,
                        },
                        {
                            "event": "raw_reaction_remove",
                            "check": self._reaction_check,
                            "timeout": None,
                        },
                    ]
                )
                asyncio.ensure_future(self._handle_reaction_event(result))
            except Exception as e:
                Role_Select_Command.log.error(fmt.format_error(e))

    def _reaction_check(self, payload: discord.RawReactionActionEvent) -> bool:
        return (
            payload.message_id in self.message_ids and payload.user_id != client.user.id
        )

    async def _handle_reaction_event(self, payload: discord.RawReactionActionEvent):
        # Remove/ignore custom emoji
        if payload.emoji.is_custom_emoji():
            if payload.event_type == "REACTION_ADD":
                # Remove invalid reactions
                channel = client.get_channel(payload.channel_id)
                message = channel.get_partial_message(payload.message_id)
                await message.remove_reaction(payload.emoji, member)
            return

        emoji = str(payload.emoji)
        # Try to get the role ids corresponding to the reaction
        with db.cursor() as c:
            c.execute(
                """SELECT role_id FROM role_select_reactions
                WHERE message_id = %s AND emoji = %s;""",
                (payload.message_id, emoji),
            )
            reaction_role_ids = {r[0] for r in c.fetchall()}
            c.execute(
                """SELECT allow_multiple_selections FROM role_select_messages
                WHERE message_id = %s;""",
                (payload.message_id,),
            )
            allow_multiple_selections = c.fetchone()[0]

        # Handle the reaction if there are no corresponding roles
        if not reaction_role_ids:
            if payload.event_type == "REACTION_ADD":
                # Remove invalid reactions
                channel = client.get_channel(payload.channel_id)
                message = channel.get_partial_message(payload.message_id)
                await message.remove_reaction(payload.emoji, member)
            return

        # Handle valid reactions
        guild = client.get_guild(payload.guild_id)
        message = await guild.get_channel(payload.channel_id).fetch_message(
            payload.message_id
        )

        # Get member who added/removed the reaction
        if payload.member is not None:
            member = payload.member
        else:
            member = guild.get_member(payload.user_id)

        try:
            # TODO: Add reasons
            if payload.event_type == "REACTION_ADD":
                # allow_multiple_selections can be None or 1 is having
                # multiple selections is allowed, or 0 if it is dissallowed
                if allow_multiple_selections == 0:
                    # Removes all other reactions the use has. Thie will
                    # automatically remove any roles provided by those
                    # reactions.
                    await asyncio.gather(
                        *(
                            r.remove(member)
                            for r in message.reactions
                            if r.emoji != emoji
                        )
                    )
                add_roles = (guild.get_role(r_id) for r_id in reaction_role_ids)
                await member.add_roles(
                    *add_roles,
                    reason="Automatically added using role select from message "
                    f"{message.jump_url}",
                )
            else:
                keep_emojis = set()

                async def check(
                    keep_emojis: set[str], reaction: discord.Reaction, user_id: int
                ):
                    if (
                        self._is_unicode_emoji(reaction.emoji)
                        and str(reaction.emoji) != emoji
                        and (await reaction.users().get(id=user_id)) is not None
                    ):
                        keep_emojis.add(str(reaction.emoji))

                await asyncio.gather(
                    *(check(keep_emojis, r, payload.user_id) for r in message.reactions)
                )
                keep_role_ids = set()
                if keep_emojis:
                    with db.cursor() as c:
                        # Try to get the role ids corresponding to the reaction
                        for e in keep_emojis:
                            c.execute(
                                """SELECT role_id FROM role_select_reactions
                                WHERE message_id = %s AND emoji = %s;""",
                                (payload.message_id, e),
                            )
                            keep_role_ids.update((r[0] for r in c.fetchall()))

                remove_roles = (
                    guild.get_role(r_id)
                    for r_id in reaction_role_ids.difference(keep_role_ids)
                )

                await member.remove_roles(
                    *remove_roles,
                    reason="Automatically removed using role select from message "
                    f"{message.jump_url}",
                )
        except Exception as e:
            print(fmt.format_error(e))

    async def _get_channel(
        self,
        channel: discord.TextChannel,
        responder: discord.Member,
        title: str,
        description_prompt: str,
    ) -> discord.TextChannel:
        description = f"{description_prompt}, or react with ❌ to cancel"
        message = await std_embed.send_input(
            channel, title=title, description=description, author=responder
        )
        while True:
            get_channel_name = (await get.reply(responder, channel, message)).content
            get_channel = await find.channel(channel, get_channel_name, responder)
            if get_channel is not None:
                return get_channel
            message = await std_embed.send_reinput(
                channel,
                title=title,
                description=fmt.format_maxlen(
                    "Could not find channel `{}`" f". {description}", get_channel_name
                ),
                author=responder,
            )

    async def _get_roles(
        self,
        channel: discord.TextChannel,
        responder: discord.Member,
        title: str,
        description: str,
    ) -> list[discord.Role]:
        roles = channel.guild.roles
        # Remove @everyone and any roles higher than the bot's highest role
        highest_bot_role = channel.guild.get_member(client.user.id).roles[-1]
        roles = roles[1 : roles.index(highest_bot_role)]
        # Remove bot managed roles
        roles = [r for r in roles if not r.is_bot_managed()]
        # Remove roles managed by other messages
        guild_id = channel.guild.id
        with db.cursor() as c:
            c.execute(
                """SELECT role_select_reactions.role_id
                FROM role_select_messages
                JOIN role_select_reactions
                ON role_select_messages.message_id = role_select_reactions.message_id
                WHERE role_select_messages.guild_id = %s;""",
                (guild_id,),
            )
            managed_role_ids = {r[0] for r in c.fetchall()}
        roles = [r for r in roles if r.id not in managed_role_ids]
        # List highest roles first
        roles.reverse()
        ret = await get.selections(
            channel,
            roles,
            lambda r: r.mention,
            responder=responder,
            title=title,
            description=description,
        )
        while not ret:
            # If no selections were made, keep asking for roles to be selected
            ret = await get.selections(
                channel,
                roles,
                lambda r: r.mention,
                responder=responder,
                title=title,
                description=f"You must select roles. {description}",
            )
        return ret

    def _is_unicode_emoji(self, emoji: EmojiType):
        if isinstance(emoji, discord.Emoji):
            return False
        elif isinstance(emoji, discord.PartialEmoji):
            return emoji.is_unicode_emoji()
        else:
            return self._re_custom_emoji.fullmatch(emoji) is None

    async def _get_emoji(
        self,
        channel: discord.TextChannel,
        submitter: discord.Member,
        title: str,
        description_prompt: str,
        emojis_to_roles: dict[str, list[discord.Role]],
    ) -> str:
        # TODO: Prevent using emojis from other servers
        description = description_prompt
        is_reinput = False
        message = await std_embed.send_input(
            channel,
            title=title,
            description=description,
            author=submitter,
        )
        while True:
            emoji = await self._wait_for_emoji_from_reply_or_reaction(
                message, submitter
            )
            if not self._is_unicode_emoji(emoji):
                reinput_prompt = (
                    "Custom emojis can not be used in role "
                    f"selection messages. {description_prompt}"
                )
            else:
                str_emoji = str(emoji)
                if str_emoji not in emojis_to_roles.keys():
                    try:
                        await message.add_reaction(str_emoji)
                        return str_emoji
                    except discord.HTTPException:
                        reinput_prompt = fmt.format_maxlen(
                            f"`{{}}` is not a valid emoji. {description_prompt}",
                            str_emoji,
                        )
                else:
                    reinput_prompt = fmt.format_maxlen(
                        "{} has already been assigned to the "
                        + ("roles" if len(emojis_to_roles[str_emoji]) > 1 else "role")
                        + ", ".join(r.mention for r in emojis_to_roles[str_emoji])
                        + f". {description_prompt}",
                        str_emoji,
                    )
            message = await std_embed.send_reinput(
                channel,
                title=title,
                description=reinput_prompt,
                author=submitter,
            )

    async def _wait_for_emoji_from_reply_or_reaction(
        self, msg: discord.Message, member: discord.Member
    ) -> EmojiType:
        try:
            event, response = await get.client_events(
                [
                    {
                        "event": "reaction_add",
                        "check": lambda r, u: r.message.id == msg.id
                        and u.id == member.id,
                        "timeout": 60,
                    },
                    {
                        "event": "message",
                        "check": lambda m: m.author.id == member.id
                        and m.channel.id == msg.channel.id,
                        "timeout": 60,
                    },
                ]
            )
        except asyncio.TimeoutError:
            raise errors.UserTimeoutError()
        else:
            if event == "reaction_add":
                return response[0].emoji
            else:
                return response.content


bot_commands.add_command(Role_Select_Command())
