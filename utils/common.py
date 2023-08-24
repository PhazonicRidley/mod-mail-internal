from __future__ import annotations
import os
from logzero import setup_logger
from logging import Logger
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from main import ModMailInternal


def configure_logging(filename: str) -> Logger:
    """Configure logging for main bot and each cog."""
    log_path = "data/logs/"
    if not os.path.isdir(log_path):
        os.mkdir(log_path)
    return setup_logger(
        name=filename, logfile=log_path + filename + ".log", maxBytes=100000
    )


async def set_guild(bot: ModMailInternal, guild_id: int):
    """Checks if a guild is in the settings database"""
    if not await bot.db.fetchval(
        "SELECT guild_id FROM settings WHERE guild_id = $1", guild_id
    ):
        await bot.db.execute("INSERT INTO settings (guild_id) VALUES ($1)", guild_id)
