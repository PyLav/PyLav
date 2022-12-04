from __future__ import annotations

from pylav.exceptions.base import PyLavException


class PlaylistException(PyLavException):
    """Base class for playlist related errors"""


class InvalidPlaylistException(PlaylistException):
    """Raised when a playlist is invalid"""
