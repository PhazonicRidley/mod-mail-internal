from __future__ import annotations
import discord
from discord import app_commands
from discord.ext import commands
from utils.common import *
from main import ModMailInternal


@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
class Role(
    commands.GroupCog,
    name="role",
    description="Used to manage approved roles to make topics",
):
    def __init__(self, bot: ModMailInternal) -> None:
        self.bot = bot
        self.log = configure_logging("settings")
        super().__init__()

    @app_commands.command(name="add")
    @app_commands.describe(role="The role to be added to make a new topic")
    async def role_add(self, interaction: discord.Interaction, role: discord.Role):
        """Sets a role to be allowed to make a new topic"""
        await set_guild(self.bot, interaction.guild_id)
        role_id_data = await self.bot.db.fetchval(
            "SELECT allowed_role_ids FROM settings WHERE guild_id = $1",
            interaction.guild_id,
        )
        if not role_id_data or role.id not in role_id_data:
            await self.bot.db.execute(
                "UPDATE settings SET allowed_role_ids = array_append(allowed_role_ids, $1) WHERE guild_id = $2",
                role.id,
                interaction.guild_id,
            )
            await interaction.response.send_message(
                f"Users with role `{role.name}` can now make topics.", ephemeral=True
            )

        else:
            await interaction.response.send_message(
                "Role already added to database", ephemeral=True
            )

    @app_commands.command(name="remove")
    @app_commands.describe(role="The role to remove")
    async def role_remove(self, interaction: discord.Interaction, role: discord.Role):
        """Removes a role for the topic whitelist."""
        await set_guild(self.bot, interaction.guild_id)
        role_id_data = await self.bot.db.fetchval(
            "SELECT allowed_role_ids FROM settings WHERE guild_id = $1",
            interaction.guild_id,
        )
        if not role_id_data or not role.id in role_id_data:
            await interaction.response.send_message(
                "Role not on whitelist.", ephemeral=True
            )

        else:
            await self.bot.db.execute(
                "UPDATE settings SET allowed_role_ids = array_remove(allowed_role_ids, $1) WHERE guild_id = $2",
                role.id,
                interaction.guild_id,
            )
            await interaction.response.send_message(
                f"`{role.name}` removed from whitelist.", ephemeral=True
            )

    @app_commands.command(name="list")
    async def role_list(self, interaction: discord.Interaction):
        """Lists all whitelisted roles that can make topics"""
        await set_guild(self.bot, interaction.guild_id)
        role_id_data = await self.bot.db.fetchval(
            "SELECT allowed_role_ids FROM settings WHERE guild_id = $1",
            interaction.guild_id,
        )
        output_str = ""
        if not role_id_data:
            return await interaction.response.send_message(
                "No roles saved.", ephemeral=True
            )
        for rid in role_id_data:
            role = interaction.guild.get_role(rid)
            if role:
                output_str += f"- `{role.name}` ({role.id})\n"
            else:
                output_str += f":warning: Role ID ({rid}) no longer exists in server, please remove.\n"

        await interaction.response.send_message(output_str, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Role(bot))
