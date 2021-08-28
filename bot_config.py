import discord
from pathlib import Path

from utils import datastores


class _Bot_Config(datastores.Datastore):
    """A config storing general information about the bot.

    Attributes
    ------------
    prefix: datastores.helper_fields.Guild_Field[str]
    A field storing the prefix for the bot. Can be set per guild, or for the
    whole bot globally.

    intents:datastores.Unkeyed_Field[dict[str, bool]]
    A dictionary of overrides for the default Discord intents gotten from
    `discord.Intents.default()`
    """

    prefix: datastores.helper_fields.Guild_Field[
        str
    ] = datastores.helper_fields.Guild_Field(
        default_val="!",
        version=1,
    )

    intents: datastores.Unkeyed_Field[
        dict[str, bool]
    ] = datastores.helper_fields.Defaulted_Unkeyed_Field(
        default_val={},
        version=1,
    )


bot_config = _Bot_Config("bot_config", base_path=Path("data/cfg"))
