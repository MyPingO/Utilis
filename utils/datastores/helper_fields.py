from . import fields, types

import discord
from copy import deepcopy
from typing import Generic, Optional


def Defaulted_Keyed_Field(
    *,
    default_val: types.Val_Type,
    key_encoder: types.Key_Encoder[types.Key_Type],
    key_depth: int = 1,
    version: int,
    data_encoder: types.Data_Encoder[types.Val_Type] = lambda d: d,
    data_decoder: types.Data_Decoder[types.Val_Type] = lambda d: d,
) -> fields.Keyed_Field[types.Key_Type, types.Val_Type]:
    """Creates a `Keyed_Field` that returns `default_val` if an invalid key
    if given to `Keyed_Field.get`.
    """

    def fallback(*args, **kwargs):
        return deepcopy(default_val)

    return fields.Keyed_Field(
        key_encoder=key_encoder,
        key_depth=key_depth,
        version=version,
        data_encoder=data_encoder,
        data_decoder=data_decoder,
        fallback=fallback,
    )


def Defaulted_Unkeyed_Field(
    *,
    default_val: types.Val_Type,
    version: int,
    data_encoder: types.Data_Encoder[types.Val_Type] = lambda d: d,
    data_decoder: types.Data_Decoder[types.Val_Type] = lambda d: d,
) -> fields.Unkeyed_Field[types.Val_Type]:
    """Creates an `Unkeyed_Field` that returns `default_val` if no value is
    set for the field.
    """

    def fallback(*args, **kwargs):
        return deepcopy(default_val)

    return fields.Unkeyed_Field(
        version=version,
        data_encoder=data_encoder,
        data_decoder=data_decoder,
        fallback=fallback,
    )


def _guild_key_encoder(g: discord.Guild) -> str:
    """Encodes a guild to its id as a string."""
    return str(g.id)


class Guild_Field(fields.Nested_Field, Generic[types.Val_Type]):
    """A nested field for storing guild specific values.

    Attributes
    ------------
    guild: fields.Keyed_Field[discord.Guild, types.Val_Type]
    A keyed field that stores guild specific values. `guild.get` falls back to
    `bot.get`.

    bot: fields.Unkeyed_Field[types.Val_Type]
    An unkeyed field that contains a bot-wide global default value that bot
    managers should be able to set. `bot.get` falls back to `default_val`.

    default_val: types.Val_Type
    The default return value if no bot-wide global value is set.
    """

    guild: fields.Keyed_Field[discord.Guild, types.Val_Type]
    bot: fields.Unkeyed_Field[types.Val_Type]

    def __init__(
        self,
        *,
        default_val: types.Val_Type,
        version: int,
        data_encoder: types.Data_Encoder[types.Val_Type] = lambda d: d,
        data_decoder: types.Data_Decoder[types.Val_Type] = lambda d: d,
    ):
        self._default_val = deepcopy(default_val)
        self.bot = fields.Unkeyed_Field(
            version=version,
            data_encoder=data_encoder,
            data_decoder=data_decoder,
            fallback=lambda ds, copy: ds.default_val,
        )
        self.guild = fields.Keyed_Field(
            key_encoder=_guild_key_encoder,
            key_depth=1,
            version=version,
            data_encoder=data_encoder,
            data_decoder=data_decoder,
            fallback=lambda ds, key, copy: ds.bot.get(copy=copy),
        )

    @property
    @fields.require_field_init
    def default_val(self) -> types.Val_Type:
        """The default return value if no bot-wide global value is set."""
        return self._default_val

    @fields.require_field_init
    def get(self, key: Optional[discord.Guild], copy: bool = False) -> types.Val_Type:
        """A helper method that calls `guild.get` if `key` is not `None`, or
        `bot.get` if it is.
        """
        if key is None:
            return self.bot.get(copy=copy)
        return self.guild.get(key, copy=copy)
