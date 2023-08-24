from __future__ import annotations
import discord
from discord import app_commands
import asyncpg
from . import errors
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from main import ModMailInternal


def topic_whitelist():
    async def wrapper(interaction: discord.Interaction):
        """Verifies an topic command can be used"""
        # Get data from settings table in db
        con: asyncpg.Connection
        bot: ModMailInternal = interaction.client
        async with bot.db.acquire() as con:
            role_ids = await con.fetchval(
                "SELECT allowed_role_ids FROM settings WHERE guild_id = $1",
                interaction.guild_id,
            )
            channel_id = await con.fetchval(
                "SELECT output_channel_id FROM settings WHERE guild_id = $1",
                interaction.guild_id,
            )
            channel: discord.ForumChannel = interaction.guild.get_channel(channel_id)

        if not channel:
            bot.log.warning(
                f"No channel set for guild {interaction.guild.name} ({interaction.guild_id})"
            )
            raise errors.NoChannelError("No channel set or channel has been deleted")

        if interaction.user.guild_permissions.administrator == True:
            return True

        if not role_ids:
            raise errors.NoRolesError(
                "No roles set, please have an admin set a role to use these commands"
            )
        roles = [
            interaction.guild.get_role(rid)
            for rid in role_ids
            if interaction.guild.get_role(rid) is not None
        ]
        set_intersection = set(roles) & set(interaction.user.roles)
        if not set_intersection:
            raise errors.NotWhitelistedError("You cannot use this command.")

        return True

    return app_commands.check(wrapper)


async def validate_thread(
    bot: ModMailInternal,
    interaction: discord.Interaction,
    thread: discord.Thread = None,
) -> Optional[discord.Thread]:
    """Validates a thread exists and is valid. If it isn't returns None. if it is, returns the thread."""
    if not thread:
        thread = interaction.channel
        if not isinstance(thread, discord.Thread):
            await interaction.response.send_message(
                "This can only be used inside a topic thread you created.",
                ephemeral=True,
            )
            return None

    forum_id = await bot.db.fetchval(
        "SELECT output_channel_id FROM settings WHERE guild_id = $1",
        interaction.guild_id,
    )
    if not forum_id:
        await interaction.response.send_message(
            "Topic forum doesn't exist. Please have an admin make one.",
            ephemeral=True,
        )
        return None
    forum = interaction.guild.get_channel(forum_id)
    if not forum:
        return await interaction.response.send_message(
            "Topic forum doesn't exist or was deleted. Please have an admin remake one.",
            ephemeral=True,
        )

    if thread not in forum.threads:
        await interaction.response.send_message(
            "This thread is not a topic thread. Please select a valid thread",
            ephemeral=True,
        )
        return None
    return thread
