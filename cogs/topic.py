from __future__ import annotations
import discord
from discord import app_commands
from discord.ext import commands
from utils.common import configure_logging
from utils.ui import TopicView, edit_topic, ClosingModal
import utils.checks as checks
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from main import ModMailInternal


@app_commands.guild_only()
class Topic(commands.GroupCog):
    def __init__(self, bot: ModMailInternal) -> None:
        self.bot = bot
        self.log = configure_logging("topic")

    @checks.topic_whitelist()
    @app_commands.command(name="create")
    async def create_topic(
        self, interaction: discord.Interaction, topic: str, message: str
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
            name=topic,
            content=message,
            view=TopicView(self.bot, interaction.user.id, topic_id),
        )
        await first_post.pin()
        # TODO: Update priorities
        # Update database
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
                message,
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

    async def validate_thread(
        self, interaction: discord.Interaction, thread: discord.Thread = None
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

        forum_id = await self.bot.db.fetchval(
            "SELECT output_channel_id FROM settings WHERE guild_id = $1",
            interaction.guild_id,
        )
        if not forum_id:
            await interaction.response.send_message(
                "Topic forum doesn't exist. Please have an admin make one.",
                ephemeral=True,
            )
            return None
        forum = self.bot.get_channel(forum_id)
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

    @checks.topic_whitelist()
    @app_commands.command(name="edit")
    @app_commands.describe(thread="The thread of the topic you want to edit.")
    async def edit_topic(
        self, interaction: discord.Interaction, thread: discord.Thread = None
    ):
        """Edits a topic message"""
        thread = await self.validate_thread(interaction, thread)
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
        thread = await self.validate_thread(interaction, thread)
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
                "You don't have permission to use this command, you are no the orignal poster or an administrator",
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Topic(bot))
