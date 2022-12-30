from __future__ import annotations

from pylav.exceptions.base import PyLavException


class TrackException(PyLavException):
    """Base exception for Track errors"""


class InvalidTrackException(TrackException):
    """Raised when an invalid track was passed"""


class TrackNotFoundException(TrackException):
    """Raised when a track is not found"""
