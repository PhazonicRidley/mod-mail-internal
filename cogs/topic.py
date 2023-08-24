from __future__ import annotations
import discord
from discord import app_commands
from discord.ext import commands
from utils.common import configure_logging
from utils.ui import TopicView, edit_topic, ClosingModal
import utils.checks as checks
from typing import TYPE_CHECKING
import asyncpg

if TYPE_CHECKING:
    from main import ModMailInternal


@app_commands.guild_only()
class Topic(commands.GroupCog):
    """Cog for managing topics, creation, editing, and editing"""

    def __init__(self, bot: ModMailInternal) -> None:
        self.bot = bot
        self.log = configure_logging("topic")

    @checks.topic_whitelist()
    @app_commands.command(name="create")
    @app_commands.describe(
        topic_name="The name of your topic",
        description_message="The message describing the topic",
    )
    async def create_topic(
        self,
        interaction: discord.Interaction,
        topic_name: str,
        description_message: str,
    ):
        """Creates a new topic"""
        channel = interaction.guild.get_channel(
            await self.bot.db.fetchval(
                "SELECT output_channel_id FROM settings WHERE guild_id = $1",
                interaction.guild_id,
            )
        )
        topic_id = interaction.id
        thread, first_post = await channel.create_thread(
            name=topic_name,
            content=description_message,
            view=TopicView(self.bot, interaction.user.id, topic_id),
        )
        await first_post.pin()
        # TODO: Update priorities
        # Update database
        con: asyncpg.Connection
        async with self.bot.db.acquire() as con:
            await con.execute(
                """INSERT INTO topics (
                              id, 
                              guild_id, 
                              message, 
                              priority_level, 
                              message_id, 
                              author_id, 
                              thread_id) VALUES ($1, $2, $3, $4, $5, $6, $7)""",
                topic_id,
                interaction.guild_id,
                description_message,
                1,
                first_post.id,
                interaction.user.id,
                thread.id,
            )
            await con.execute(
                "UPDATE topics SET users_in_favor = array_append(users_in_favor, $1) WHERE id = $2",
                interaction.user.id,
                topic_id,
            )
        await interaction.response.send_message(
            f"Topic added in thread {thread.mention}, You have been automatically placed in favor of this topic.",
            ephemeral=True,
        )

    @checks.topic_whitelist()
    @app_commands.command(name="edit")
    @app_commands.describe(thread="The thread of the topic you want to edit.")
    async def edit_topic(
        self, interaction: discord.Interaction, thread: discord.Thread = None
    ):
        """Edits a topic message"""
        thread = await checks.validate_thread(self.bot, interaction, thread)
        if not thread:
            return

        thread_ids = await self.bot.db.fetch(
            "SELECT thread_id FROM topics WHERE guild_id = $1 AND author_id = $2",
            interaction.guild_id,
            interaction.user.id,
        )
        thread_ids = [t["thread_id"] for t in thread_ids]
        if not thread.id in thread_ids:
            return await interaction.response.send_message(
                "You cannot edit this topic as you did not create it.", ephemeral=True
            )
        topic_id = await self.bot.db.fetchval(
            "SELECT id FROM topics WHERE thread_id = $1", thread.id
        )

        await edit_topic(self.bot, interaction, topic_id)

    @checks.topic_whitelist()
    @app_commands.command(name="close")
    @app_commands.describe(thread="The thread you wish to close.")
    async def close_topic(
        self, interaction: discord.Interaction, thread: discord.Thread = None
    ):
        """Closes a topic. Either a user's own topic or concludes a topic by an admin"""
        thread = await checks.validate_thread(self.bot, interaction, thread)
        if not thread:
            return

        topic_id, author_id = await self.bot.db.fetchrow(
            "SELECT id, author_id FROM topics WHERE guild_id = $1 AND thread_id = $2",
            interaction.guild_id,
            thread.id,
        )
        closer = None
        author = interaction.user
        if author.id == author_id:
            closer = "op"
        elif author.guild_permissions.administrator == True:
            closer = "admin"

        if closer is not None:
            try:
                await interaction.response.send_modal(
                    ClosingModal(self.bot.db, thread, topic_id, closer)
                )
            except Exception as e:
                self.log.exception("Error")
        else:
            await interaction.response.send_message(
                "You don't have permission to use this command, you are not the orignal poster or an administrator",
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Topic(bot))
