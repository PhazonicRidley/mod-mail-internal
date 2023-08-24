import discord
from discord import app_commands
from discord.ext import commands
from utils.common import *
from main import ModMailInternal


@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
class Channel(
    commands.GroupCog,
    name="channel",
    description="Used to manage the channel for topics",
):
    """Cog for managing the topic forum channel"""

    def __init__(self, bot: ModMailInternal) -> None:
        self.bot = bot
        self.log = configure_logging("channel")
        super().__init__()

    @app_commands.command(name="set")
    @app_commands.describe(channel="The channel to set")
    @app_commands.default_permissions(administrator=True)
    async def channel_set(
        self, interaction: discord.Interaction, channel: discord.ForumChannel
    ):
        """Set's the active channel for a server"""
        if channel not in interaction.guild.channels:
            await interaction.response.send_message(
                "You cannot set a channel outside the channel.", ephemeral=True
            )

        await set_guild(self.bot, interaction.guild.id)
        await self.bot.db.execute(
            "UPDATE settings SET output_channel_id = $1 WHERE guild_id = $2",
            channel.id,
            interaction.guild.id,
        )
        await interaction.response.send_message(
            f"Output channel set to: {channel.mention}", ephemeral=True
        )

    @app_commands.command(name="unset")
    @app_commands.default_permissions(administrator=True)
    async def channel_unset(self, interaction: discord.Interaction):
        """Unset's the active channel for a server"""
        await set_guild(self.bot, interaction.guild.id)
        has_channel = await self.bot.db.fetchval(
            "SELECT output_channel_id FROM settings WHERE guild_id = $1",
            interaction.guild_id,
        )
        if not has_channel:
            return await interaction.response.send_message(
                f"Output channel not set", ephemeral=True
            )
        await self.bot.db.execute(
            "UPDATE settings SET output_channel_id = NULL WHERE guild_id = $1",
            interaction.guild.id,
        )
        await interaction.response.send_message(f"Output channel unset", ephemeral=True)

    @app_commands.command(name="list")
    async def channel_list(self, interaction: discord.Interaction):
        """Lists current listed channel"""
        channel_id = await self.bot.db.fetchval(
            "SELECT output_channel_id FROM settings WHERE guild_id = $1",
            interaction.guild_id,
        )
        if not channel_id:
            return await interaction.response.send_message(
                "No channel has been set", ephemeral=True
            )
        else:
            channel = interaction.guild.get_channel(channel_id)
            return await interaction.response.send_message(
                f"Channel has been set to: {channel.mention}", ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Channel(bot))
