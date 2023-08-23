from __future__ import annotations
from traceback import format_exception
import asyncpg
import discord
import sys
from discord.app_commands.errors import *
from discord.ext import commands
import yaml
import asyncio
from utils.common import configure_logging
from logging import Logger
from typing import Literal, Optional
from utils.ui import recreate_views
import utils.errors as errors


def read_config(config: str) -> str:
    try:
        with open("data/config.yml", "r") as f:
            loadedYml = yaml.safe_load(f)
            return loadedYml[config]
    except FileNotFoundError:
        print("Cannot find config.yml. Does it exist?")
        sys.exit(1)


async def create_pool():
    return await asyncpg.create_pool(read_config("db"))


class MMITree(discord.app_commands.CommandTree):
    async def on_error(
        self, interaction: discord.Interaction, error: AppCommandError
    ) -> None:
        if isinstance(error, MissingPermissions):
            await interaction.response.send_message(
                "You don't have permission to use this command", ephemeral=True
            )

        elif isinstance(error, errors.MMIError):
            await interaction.response.send_message(error.message, ephemeral=True)

        else:
            command = interaction.command
            if command:
                await interaction.response.send_message(
                    f"An error occurred while processing the `{command.name}` app command.",
                    ephemeral=True,
                )
                print(
                    "Ignoring exception in command {0.command} in {0.message.channel}".format(
                        interaction
                    )
                )
            try:
                log_msg = "Exception occurred in `{0.command}` in {0.message.channel.mention}".format(
                    interaction
                )
                self.client.log.info(
                    f"COMMAND: {interaction.command.name}, GUILD: {interaction.guild.name} CHANNEL: {interaction.channel.name}"
                )
            except Exception:
                log_msg = (
                    "Exception occurred in `{0.command}` in DMs with a user".format(
                        interaction
                    )
                )
            tb = format_exception(type(error), error, error.__traceback__)
            print("".join(tb))
            self.client.log.error(log_msg + "".join(tb) + "\n\n")


class ModMailInternal(commands.Bot):
    """A bot for bringing up discussions anonymously by team members for other team members"""

    def __init__(self):
        self.db: asyncpg.Pool
        self.log = configure_logging("bot")
        super().__init__(
            command_prefix=read_config("prefix"),
            description="The bot to handle suggestions from all members of a team!",
            allow_mentions=discord.AllowedMentions(
                everyone=False, users=False, roles=False
            ),
            intents=discord.Intents().all(),
            help_command=commands.MinimalHelpCommand(),
            activity=discord.Activity(
                name=read_config("activity"), type=discord.ActivityType.listening
            ),
            tree_cls=MMITree,
        )

    async def setup_hook(self) -> None:
        """Async initialization"""
        try:
            self.db = await create_pool()
            self.log.info("Database pool has started!")
        except Exception as e:
            self.log.exception(
                "An error has occured with connecting to the database and creating a databse pool"
            )
            exit(-1)
            # self.log.exception(f"Traceback: {format_exception(type(e), e, e.__traceback__)}")

        await self.prepare_db()
        self.log.info("Schema configured")
        modules = ["channel", "topic", "role"]
        await self.load_extension("jishaku")
        for module in modules:
            try:
                await self.load_extension("cogs." + module)
                self.log.info(f"{module} loaded")
            except commands.errors.ExtensionError:
                self.log.exception(f"Unable to load {module}, quitting")
                exit(-1)

        await recreate_views(self)

    async def prepare_db(self):
        """Prepares schema for usage"""
        async with self.db.acquire() as conn:
            try:
                with open("schema.sql", "r") as schema:
                    try:
                        await conn.execute(schema.read())
                    except asyncpg.PostgresError:
                        self.log.exception(
                            "A SQL error has occurred while running the schema"
                        )
                        sys.exit(-1)

            except FileNotFoundError:
                self.log.error(
                    "Schema file not found, please check your files, remember to rename schema.sql.example to schema.sql when you would like to use it."
                )
                sys.exit(-1)

    async def on_command_error(self, ctx, error):
        """Handles errors"""
        # handles errors for commands that do not exist
        if isinstance(error, commands.errors.CommandNotFound):
            return

        # handles all uncaught http connection failures.
        elif isinstance(error, commands.CommandInvokeError) and isinstance(
            error.original, discord.HTTPException
        ):
            await ctx.send(
                f"An HTTP {error.original.status} error has occurred for the following reason: `{error.original.text}`"
            )

        # handles all bad command usage
        elif isinstance(
            error,
            (
                commands.MissingRequiredArgument,
                commands.BadArgument,
                commands.BadUnionArgument,
                commands.TooManyArguments,
            ),
        ):
            await ctx.send_help(ctx.command)

        # handles commands that are attempted to be used outside a guild.
        elif isinstance(error, commands.errors.NoPrivateMessage):
            await ctx.send("You cannot use this command outside of a server!")

        elif isinstance(error, commands.PrivateMessageOnly):
            await ctx.send("You cannot use this command outside of DMs with the bot!")

        elif isinstance(error, commands.MissingPermissions):
            await ctx.send(error.args[0])

        else:
            await ctx.send(
                f"An error occurred while processing the `{ctx.command.name}` command."
            )
            print(
                "Ignoring exception in command {0.command} in {0.message.channel}".format(
                    ctx
                )
            )
            try:
                log_msg = "Exception occurred in `{0.command}` in {0.message.channel.mention}".format(
                    ctx
                )
                self.log.info(
                    f"COMMAND: {ctx.command.name}, GUILD: {ctx.guild.name} CHANNEL: {ctx.channel.name}"
                )
            except Exception:
                log_msg = (
                    "Exception occurred in `{0.command}` in DMs with a user".format(ctx)
                )
            tb = format_exception(type(error), error, error.__traceback__)
            print("".join(tb))
            self.log.error(log_msg + "".join(tb) + "\n\n")

    async def on_ready(self):
        """Runs on connection to discord's API"""
        self.log.info(f"Bot has started! Logged in as {self.user.name}")


bot = ModMailInternal()


# Credit to AbstractUmbra https://about.abstractumbra.dev/discord.py/2023/01/29/sync-command-example.html
@bot.command()
@commands.guild_only()
@commands.is_owner()
async def sync(
    ctx: commands.Context,
    guilds: commands.Greedy[discord.Object],
    spec: Optional[Literal["~", "*", "^"]] = None,
) -> None:
    if not guilds:
        if spec == "~":
            synced = await ctx.bot.tree.sync(guild=ctx.guild)
        elif spec == "*":
            ctx.bot.tree.copy_global_to(guild=ctx.guild)
            synced = await ctx.bot.tree.sync(guild=ctx.guild)
        elif spec == "^":
            ctx.bot.tree.clear_commands(guild=ctx.guild)
            await ctx.bot.tree.sync(guild=ctx.guild)
            synced = []
        else:
            synced = await ctx.bot.tree.sync()

        await ctx.send(
            f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}"
        )
        return

    ret = 0
    for guild in guilds:
        try:
            await ctx.bot.tree.sync(guild=guild)
        except discord.HTTPException:
            pass
        else:
            ret += 1

    await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")


async def main():
    async with bot:
        await bot.start(read_config("token"))


if __name__ == "__main__":
    asyncio.run(main())
