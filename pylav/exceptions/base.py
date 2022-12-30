from __future__ import annotations

from discord.app_commands import AppCommandError
from discord.ext.commands import CommandError


class PyLavException(CommandError, AppCommandError):
    """Base exception for errors in the library"""
