from __future__ import annotations

from pylav.exceptions.base import PyLavException


class PyLavInvalidArgumentsException(PyLavException):
    """Base Exception for when invalid arguments are passed to a method"""


class PyLavNotInitializedException(PyLavException):
    """Raised when the library is not initialized"""


class AnotherClientAlreadyRegisteredException(PyLavException):
    """Another client has already been registered"""


class CogAlreadyRegisteredException(PyLavException):
    """Raised when a cog is already registered"""


class CogHasBeenRegisteredException(PyLavException):
    """Raised when a cog is registered"""
