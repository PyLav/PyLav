from __future__ import annotations

from pylav.exceptions.base import PyLavException
from pylav.nodes.api.responses.errors import LavalinkError


class HTTPException(PyLavException):
    """Base exception for HTTP request errors"""

    def __init__(self, response: LavalinkError):
        self.response = response


class UnauthorizedException(HTTPException):
    """Raised when a REST request fails due to an incorrect password"""
