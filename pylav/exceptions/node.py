from __future__ import annotations

import aiohttp

from pylav.exceptions.base import PyLavException


class NodeException(PyLavException):
    """Base exception for Node errors"""


class UnsupportedNodeAPIException(NodeException):
    """Exception raised when the node version is unsupported"""


class AbortPlayerRestoreDueUnavailableNodeException(NodeException):
    """Raised when the player is aborted due to an unavailable node"""


class WebsocketNotConnectedException(NodeException):
    """Raised when the node websocket is not connected"""


class NoNodeAvailableException(NodeException):
    """Raised when no node is available"""


class NoNodeWithRequestFunctionalityAvailableException(NodeException):
    """Raised when no node with request functionality is available"""

    def __init__(self, message: str, feature: str, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.message = message
        self.feature = feature


class NodeHasNoFiltersException(NodeException):
    """Raised when a node has no filters"""

    def __init__(self, message: str, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.message = message


class ManagedLavalinkNodeException(NodeException):
    """Base Exception for Managed Lavalink Node Exceptions"""


class NodeUnhealthyException(ManagedLavalinkNodeException):
    """Exception Raised when the node health checks fail"""


class InvalidArchitectureException(ManagedLavalinkNodeException):
    """Exception thrown when the Managed Lavalink node is started on an invalid arch"""


class ManagedLavalinkAlreadyRunningException(ManagedLavalinkNodeException):
    """Exception thrown when a managed Lavalink node is already running"""


class PortAlreadyInUseException(ManagedLavalinkNodeException):
    """Exception thrown when the port is already in use"""


class ManagedLinkStartAbortedUseExternal(ManagedLavalinkNodeException):
    """Exception thrown when the managed lavalink node is started but aborted"""


class ManagedLavalinkStartFailureException(ManagedLavalinkNodeException):
    """Exception thrown when a managed Lavalink node fails to start"""


class ManagedLavalinkPreviouslyShutdownException(ManagedLavalinkNodeException):
    """Exception thrown when a managed Lavalink node already has been shutdown"""


class EarlyExitException(ManagedLavalinkNodeException):
    """some placeholder text I cannot be bothered to add a meaning message atm"""


class UnsupportedJavaException(ManagedLavalinkNodeException):
    """Exception thrown when a managed Lavalink node doesn't have a supported Java"""


class UnexpectedJavaResponseException(ManagedLavalinkNodeException):
    """Exception thrown when Java returns an unexpected response"""


class NoProcessFoundException(ManagedLavalinkNodeException):
    """Exception thrown when the managed node process is not found"""


class IncorrectProcessFoundException(ManagedLavalinkNodeException):
    """Exception thrown when the managed node process is incorrect"""


class TooManyProcessFoundException(ManagedLavalinkNodeException):
    """Exception thrown when zombie processes are suspected"""


class LavalinkDownloadFailedException(ManagedLavalinkNodeException, RuntimeError):
    """Downloading the Lavalink jar failed.

    Attributes
    ----------
    response : aiohttp.ClientResponse
        The response from the server to the failed GET request.
    should_retry : bool
        Whether the lib should retry downloading the jar.
    """

    def __init__(self, *args, response: aiohttp.ClientResponse, should_retry: bool = False) -> None:
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
