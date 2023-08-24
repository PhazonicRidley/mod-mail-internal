from discord.app_commands.errors import AppCommandError, CommandInvokeError
from discord.app_commands import Command, ContextMenu


class MMIError(AppCommandError):
    def __init__(self, message: str, *args: object) -> None:
        self.message = message
        super().__init__(*args)


NoChannelError = MMIError
NoRolesError = MMIError
NotWhitelistedError = MMIError


class ViewError(CommandInvokeError):
    def __init__(self, command: Command | ContextMenu, e: Exception) -> None:
        super().__init__(command, e)
