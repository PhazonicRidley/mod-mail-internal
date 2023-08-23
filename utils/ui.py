from __future__ import annotations
from typing import Any
from discord.enums import ButtonStyle
from discord.interactions import Interaction
from discord.ui.item import Item
import discord
from discord.ui import View, Button, Modal, TextInput
import asyncpg
from typing import TYPE_CHECKING
from utils.errors import ViewError

if TYPE_CHECKING:
    from main import ModMailInternal


async def topic_generator(bot: ModMailInternal):
    for topic in await bot.db.fetch("SELECT id, author_id, message_id FROM topics"):
        yield topic


async def recreate_views(bot: ModMailInternal):
    """Recreates views on boot so they survive reboots."""
    topics = topic_generator(bot)
    async for topic in topics:
        topic_id = topic["id"]
        author_id = topic["author_id"]
        message_id = topic["message_id"]
        view = TopicView(bot, author_id, topic_id)
        bot.add_view(view, message_id=message_id)


class TopicView(View):
    """Topic view"""

    def __init__(self, bot: ModMailInternal, author_id: int, topic_id: int):
        super().__init__(timeout=None)
        self.bot = bot
        self.author_id = author_id
        self.topic_id = topic_id  # This will double as the view's ID as there should never be a view that would be separate from a topic
        self.custom_id = str(topic_id)

    async def on_error(
        self, interaction: Interaction, error: Exception, item: Item[Any]
    ) -> None:
        raise ViewError(interaction.command, error)

    @discord.ui.button(
        style=ButtonStyle.green,
        label="Give Priority",
        custom_id="add",
        emoji="\U00002b06",
    )
    async def add_priority(self, interaction: discord.Interaction, button: Button):
        """Lets a user add priority to a topic"""
        con: asyncpg.Connection
        async with self.bot.db.acquire() as con:
            users_in_favor = await con.fetchval(
                "SELECT users_in_favor FROM topics WHERE id = $1",
                self.topic_id,
            )
            if interaction.user.id in users_in_favor:
                return await interaction.response.send_message(
                    "You have already increased priority for this topic.",
                    ephemeral=True,
                )
            await con.execute(
                "UPDATE topics SET priority_level = priority_level + 1 WHERE id = $1",
                self.topic_id,
            )
            await con.execute(
                "UPDATE topics SET users_in_favor = array_append(users_in_favor, $1) WHERE id = $2",
                interaction.user.id,
                self.topic_id,
            )

        await interaction.response.send_message(
            "Increased priority for this topic.", ephemeral=True
        )

    @discord.ui.button(
        style=ButtonStyle.red,
        label="Remove Priority",
        custom_id="remove",
        emoji="\U0000274c",
    )
    async def remove_priority(self, interaction: discord.Interaction, button: Button):
        con: asyncpg.Connection
        async with self.bot.db.acquire() as con:
            users_in_favor = await con.fetchval(
                "SELECT users_in_favor FROM topics WHERE id = $1",
                self.topic_id,
            )
            if interaction.user.id not in users_in_favor:
                return await interaction.response.send_message(
                    "You have not increased priority for this topic and cannot remove yourself.",
                    ephemeral=True,
                )
            await con.execute(
                "UPDATE topics SET priority_level = priority_level - 1 WHERE id = $1",
                self.topic_id,
            )
            await con.execute(
                "UPDATE topics SET users_in_favor = array_remove(users_in_favor, $1) WHERE id = $2",
                interaction.user.id,
                self.topic_id,
            )

        await interaction.response.send_message(
            "Removed priority for this topic,", ephemeral=True
        )

    @discord.ui.button(
        style=ButtonStyle.primary, label="Edit", custom_id="edit", emoji="\U0001f4dd"
    )
    async def edit_message(self, interaction: discord.Interaction, button: Button):
        await edit_topic(self.bot, interaction, self.topic_id)


async def edit_topic(
    bot: ModMailInternal,
    interaction: discord.Interaction,
    topic_id: int,
    *,
    thread: discord.Thread = None,
):
    """Edits a topic message"""
    if not thread:
        con: asyncpg.Connection
        async with bot.db.acquire() as con:
            author_id = await con.fetchval(
                "SELECT author_id FROM topics WHERE id = $1", topic_id
            )
            if author_id != interaction.user.id:
                return await interaction.response.send_message(
                    "You are not the author of this topic and cannot use this.",
                    ephemeral=True,
                )

            thread_id = await con.fetchval(
                "SELECT thread_id FROM topics WHERE id = $1", topic_id
            )
            message_id = await con.fetchval(
                "SELECT message_id FROM topics WHERE id = $1", topic_id
            )

        thread: discord.Thread = interaction.guild.get_channel_or_thread(thread_id)
        if not thread:
            raise ValueError("This shouldn't happen. Thread doesn't exist")

    partial_message = thread.get_partial_message(message_id)
    model = EditingModal(bot.db, thread, partial_message, topic_id)
    await interaction.response.send_modal(model)


class MMIModal(Modal):
    # TODO: Better error handling
    async def on_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        raise ViewError(interaction.command, error)


class EditingModal(MMIModal):
    topic_title = TextInput(label="Topic Title", required=False)
    topic_message = TextInput(
        label="Topic Message", style=discord.TextStyle.paragraph, required=False
    )

    def __init__(
        self,
        db: asyncpg.Pool,
        topic_thread: discord.Thread,
        message: discord.PartialMessage,
        topic_id: int,
    ):
        self.db = db
        self.topic_thread = topic_thread
        self.message = message
        self.topic_id = topic_id
        super().__init__(title="Editing topic", timeout=None)

    async def on_submit(self, interaction: discord.Interaction):
        if not self.topic_title.value.isspace():
            await self.topic_thread.edit(name=self.topic_title)

        if not self.topic_message.value.isspace():
            await self.message.edit(content=self.topic_message)
            await self.db.execute(
                "UPDATE topics SET message = $1 WHERE id = $2",
                str(self.topic_message),
                self.topic_id,
            )

        if (
            not self.topic_title.value.isspace()
            or not self.topic_message.value.isspace()
        ):
            await self.message.reply("Topic has been updated by original poster.")
            await interaction.response.send_message("Edited message.", ephemeral=True)
        else:
            await interaction.response.send_message("Cancelled", ephemeral=True)


class ClosingModal(MMIModal):
    """UI to handle closing a topic"""

    conclusion_text = TextInput(
        label="Closing remarks", style=discord.TextStyle.paragraph
    )

    def __init__(
        self, db: asyncpg.Pool, topic_thread: discord.Thread, topic_id: int, closer: str
    ) -> None:
        self.db = db
        self.topic_id = topic_id
        self.topic_thread = topic_thread
        self.closer = closer
        if closer not in ("op", "admin"):
            raise AttributeError("Invalid closer type.")
        super().__init__(title="Closing topic", timeout=None)

    async def on_submit(self, interaction: Interaction) -> None:
        topic_entry = await self.db.fetchrow(
            "SELECT priority_level, message_id FROM topics WHERE id = $1",
            self.topic_id,
        )

        if self.closer == "op":
            emb_description = "This topic was closed by the original poster."
        else:
            emb_description = "This topic was closed by an administrator."

        result_embed = discord.Embed(
            title="Topic closed", description=emb_description, color=discord.Color.red()
        )
        result_embed.add_field(
            name="Closure's remarkers", value=self.conclusion_text, inline=False
        )
        result_embed.set_footer(text=f"Priority level: {topic_entry['priority_level']}")
        message = self.topic_thread.get_partial_message(topic_entry["message_id"])
        await message.reply(embed=result_embed)
        # lock and archive thread.
        await self.topic_thread.edit(
            locked=True, archived=True, reason="Topic closed by " + self.closer
        )

        await self.db.execute(
            "DELETE FROM topics WHERE id = $1 AND guild_id = $2",
            self.topic_id,
            interaction.guild_id,
        )
        await interaction.response.defer()
