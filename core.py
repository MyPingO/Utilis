import discord
import logging
import datetime
from pathlib import Path

from bot_config import bot_config

log_dir = Path(f"data/bot/logs/")
log_dir.mkdir(parents=True, exist_ok=True)

_datetime_str = str(datetime.datetime.now().replace(microsecond=0)).replace(":", ".")
log_path = log_dir / f"{_datetime_str}.log"

logging.basicConfig(
    filename=log_path,
    filemode="w",
    level=logging.INFO,
    format="%(asctime)s:%(levelname)s:%(name)s: %(message)s",
)

_intents_dict = {k: v for k, v in discord.Intents.default()}
_intents_dict.update(bot_config.intents.get())
intents = discord.Intents(**_intents_dict)
client = discord.Client(intents=intents)
