from __future__ import annotations
import os
from logzero import setup_logger
from logging import Logger
from typing import TYPE_CHECKING
import discord


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


async def update_thread_order(
    bot: ModMailInternal,
    interaction: discord.Interaction,
    channel: discord.ForumChannel,
    *,
    new_channel_set: bool = False,
):
    if not new_channel_set:
        status_thread_id = await bot.db.fetchval(
            "SELECT status_thread_id FROM settings WHERE guild_id = $1",
            interaction.guild_id,
        )
        status_thread: discord.Thread or None = channel.get_thread(status_thread_id)
        if not status_thread:
            new_channel_set = True
    topics = await bot.db.fetch(
        "SELECT thread_id, users_in_favor FROM topics WHERE guild_id = $1",
        interaction.guild_id,
    )
    sorted_topics = sorted(topics, key=lambda x: x["users_in_favor"], reverse=True)
    output_str = "Order of threads by priority\n\n"
    for topic in sorted_topics:
        thread = channel.get_thread(topic["thread_id"])
        if not thread:
            if new_channel_set:
                await bot.db.execute(
                    "DELETE FROM topics WHERE thread_id = $1 AND guild_id = $2",
                    topic["thread_id"],
                    interaction.guild_id,
                )
            continue
        output_str += (
            f"- {thread.mention} with a priority of {len(topic['users_in_favor'])}\n"
        )

    if new_channel_set:
        new_thread = await channel.create_thread(
            name="Topic Priority", content=output_str
        )
        await new_thread.thread.edit(pinned=True)
        await bot.db.execute(
            "UPDATE settings SET status_thread_id = $1 WHERE guild_id = $2",
            new_thread.thread.id,
            interaction.guild_id,
        )
    else:
        starter_message = status_thread.starter_message
        if not starter_message:
            starter_message = await status_thread.fetch_message(status_thread.id)

        await starter_message.edit(content=output_str)
