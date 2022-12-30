from __future__ import annotations

from pylav.exceptions.base import PyLavException


class SQLException(PyLavException):
    """Base exception for errors in SQL"""


class EntryNotFoundException(SQLException):
    """Raised when an entry is not found"""
