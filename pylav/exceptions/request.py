from pylav.exceptions.base import PyLavException


class HTTPException(PyLavException):
    """Base exception for HTTP request errors"""

    def __init__(self, response: LavalinkExceptionResponseObject):
        self.response = response


class UnauthorizedException(HTTPException):
    """Raised when a REST request fails due to an incorrect password"""
