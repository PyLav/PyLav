from __future__ import annotations

import aiohttp
from discord.app_commands import AppCommandError
from discord.ext.commands import CommandError

__all__ = (
    "PyLavError",
    "NodeError",
    "WebsocketNotConnectedError",
    "TrackError",
    "ManagedLavalinkNodeError",
    "HTTPError",
    "Unauthorized",
    "InvalidTrack",
    "NodeUnhealthy",
    "InvalidArchitectureError",
    "ManagedLavalinkAlreadyRunningError",
    "PortAlreadyInUseError",
    "ManagedLavalinkStartFailure",
    "ManagedLavalinkPreviouslyShutdownError",
    "EarlyExitError",
    "UnsupportedJavaError",
    "UnexpectedJavaResponseError",
    "NoProcessFound",
    "IncorrectProcessFound",
    "TooManyProcessFound",
    "LavalinkDownloadFailed",
    "TrackNotFound",
    "CogAlreadyRegistered",
    "CogHasBeenRegistered",
    "AnotherClientAlreadyRegistered",
    "NoNodeAvailable",
    "SQLError",
    "EntryNotFoundError",
    "PyLavNotInitialized",
    "PlaylistError",
    "InvalidPlaylist",
    "ManagedLinkStartAbortedUseExternal",
    "AbortPlayerRestoreDueUnavailableNode",
    "NoNodeWithRequestFunctionalityAvailable",
)


class PyLavError(CommandError, AppCommandError):
    """Base exception for errors in the library"""


class PyLavInvalidArguments(PyLavError):
    """Base Exception for when invalid arguments are passed to a method"""


class PyLavNotInitialized(PyLavError):
    """Raised when the library is not initialized"""


class SQLError(PyLavError):
    """Base exception for errors in SQL"""


class EntryNotFoundError(SQLError):
    """Raised when an entry is not found"""


class AnotherClientAlreadyRegistered(PyLavError):
    """Another client has already been registered"""


class NodeError(PyLavError):
    """Base exception for Node errors"""


class AbortPlayerRestoreDueUnavailableNode(NodeError):
    """Raised when the player is aborted due to an unavailable node"""


class WebsocketNotConnectedError(NodeError):
    """Raised when the node websocket is not connected"""


class TrackError(PyLavError):
    """Base exception for Track errors"""


class ManagedLavalinkNodeError(NodeError):
    """Base Exception for Managed Lavalink Node Exceptions"""


class HTTPError(PyLavError):
    """Base exception for HTTP request errors"""


class Unauthorized(HTTPError):
    """Raised when a REST request fails due to an incorrect password"""


class InvalidTrack(TrackError):
    """Raised when an invalid track was passed"""


class NodeUnhealthy(ManagedLavalinkNodeError):
    """Exception Raised when the node health checks fail"""


class InvalidArchitectureError(ManagedLavalinkNodeError):
    """Error thrown when the Managed Lavalink node is started on an invalid arch"""


class ManagedLavalinkAlreadyRunningError(ManagedLavalinkNodeError):
    """Exception thrown when a managed Lavalink node is already running"""


class PortAlreadyInUseError(ManagedLavalinkNodeError):
    """Exception thrown when the port is already in use"""


class ManagedLinkStartAbortedUseExternal(ManagedLavalinkNodeError):
    """Exception thrown when the managed lavalink node is started but aborted"""


class ManagedLavalinkStartFailure(ManagedLavalinkNodeError):
    """Exception thrown when a managed Lavalink node fails to start"""


class ManagedLavalinkPreviouslyShutdownError(ManagedLavalinkNodeError):
    """Exception thrown when a managed Lavalink node already has been shutdown"""


class EarlyExitError(ManagedLavalinkNodeError):
    """some placeholder text I cannot be bothered to add a meaning message atm"""


class UnsupportedJavaError(ManagedLavalinkNodeError):
    """Exception thrown when a managed Lavalink node doesn't have a supported Java"""


class UnexpectedJavaResponseError(ManagedLavalinkNodeError):
    """Exception thrown when Java returns an unexpected response"""


class NoProcessFound(ManagedLavalinkNodeError):
    """Exception thrown when the managed node process is not found"""


class IncorrectProcessFound(ManagedLavalinkNodeError):
    """Exception thrown when the managed node process is incorrect"""


class TooManyProcessFound(ManagedLavalinkNodeError):
    """Exception thrown when zombie processes are suspected"""


class LavalinkDownloadFailed(ManagedLavalinkNodeError, RuntimeError):
    """Downloading the Lavalink jar failed.

    Attributes
    ----------
    response : aiohttp.ClientResponse
        The response from the server to the failed GET request.
    should_retry : bool
        Whether the lib should retry downloading the jar.
    """

    def __init__(self, *args, response: aiohttp.ClientResponse, should_retry: bool = False):
        super().__init__(*args)
        self.response = response
        self.should_retry = should_retry

    def __repr__(self) -> str:
        str_args = [*map(str, self.args), self._response_repr()]
        return f"LavalinkDownloadFailed({', '.join(str_args)}"

    def __str__(self) -> str:
        return f"{super().__str__()} {self._response_repr()}"

    def _response_repr(self) -> str:
        return f"[{self.response.status} {self.response.reason}]"


class TrackNotFound(TrackError):
    """Raised when a track is not found"""


class CogAlreadyRegistered(PyLavError):
    """Raised when a cog is already registered"""


class CogHasBeenRegistered(PyLavError):
    """Raised when a cog is registered"""


class NoNodeAvailable(NodeError):
    """Raised when no node is available"""


class NoNodeWithRequestFunctionalityAvailable(NodeError):
    """Raised when no node with request functionality is available"""

    def __init__(self, message: str, feature: str, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.message = message
        self.feature = feature


class PlaylistError(PyLavError):
    """Base class for playlist related errors"""


class InvalidPlaylist(PlaylistError):
    """Raised when a playlist is invalid"""
