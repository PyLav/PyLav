from __future__ import annotations

from typing import Literal

from pylav.exceptions.base import PyLavException
from pylav.nodes.api.responses.errors import LavalinkError


class HTTPException(PyLavException):
    """Base exception for HTTP request errors"""

    loadType: Literal["apiError"] = "apiError"
    data: None = None

    def __init__(self, response: LavalinkError):
        self.response = response

    def __bool__(self):
        return False


class UnauthorizedException(HTTPException):
    """Raised when a REST request fails due to an incorrect password"""

    def __bool__(self):
        return False
