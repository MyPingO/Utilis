import discord
import logging
import datetime
from pathlib import Path

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

client = discord.Client(intents=discord.Intents.all())
