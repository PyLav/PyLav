from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

import aiohttp
import ujson
from red_commons.logging import getLogger

from pylav.events import TrackEndEvent, TrackExceptionEvent, TrackStartEvent, TrackStuckEvent, WebSocketClosedEvent
from pylav.exceptions import WebsocketNotConnectedError
from pylav.location import get_closest_discord_region
from pylav.node import Stats
from pylav.tracks import AudioTrack
from pylav.utils import AsyncIter

if TYPE_CHECKING:
    from pylav.client import Client
    from pylav.node import Node

LOGGER = getLogger("red.PyLink.WebSocket")


class WebSocket:
    """Represents the WebSocket connection with Lavalink."""

    def __init__(
        self,
        *,
        node: Node,
        host: str,
        port: int,
        password: str,
        resume_key: str,
        resume_timeout: int,
        reconnect_attempts: int,
        ssl: bool,
    ):
        self._node = node
        self._client = self._node.node_manager.client

        self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30), json_serialize=ujson.dumps)
        self._ws = None
        self._message_queue = []

        self._host = host
        self._port = port
        self._password = password
        self._ssl = ssl
        self._max_reconnect_attempts = reconnect_attempts

        self._resume_key = resume_key
        self._resume_timeout = resume_timeout
        self._resuming_configured = False

        self._ws_uri = f"{self.socket_protocol}://{self._host}:{self._port}"

        self._closers = (
            aiohttp.WSMsgType.CLOSE,
            aiohttp.WSMsgType.CLOSING,
            aiohttp.WSMsgType.CLOSED,
        )

        asyncio.ensure_future(self.connect())

    @property
    def socket_protocol(self) -> str:
        """The protocol used for the socket connection."""
        return "wss" if self._ssl else "ws"

    @property
    def lib_version(self) -> str:
        """Returns the PyLink library version."""
        return self._client.lib_version

    @property
    def bot_id(self) -> str:
        """Returns the bot's ID."""
        return self._client.bot_id

    @property
    def node(self) -> Node:
        """Returns the :class:`Node` instance."""
        return self._node

    @property
    def client(self) -> Client:
        """Returns the :class:`Client` instance."""
        return self._client

    @property
    def connected(self):
        """Returns whether the websocket is connected to Lavalink."""
        return self._ws is not None and not self._ws.closed

    async def ping(self) -> None:
        """Pings the websocket."""
        if self.connected:
            await self._ws.ping()
        else:
            raise WebsocketNotConnectedError

    async def connect(self):
        """Attempts to establish a connection to Lavalink."""
        headers = {
            "Authorization": self._password,
            "User-Id": str(self.bot_id),
            "Client-Name": f"Py-Link/{self.lib_version}",
        }

        if self._resuming_configured and self._resume_key:
            headers["Resume-Key"] = self._resume_key
        self._node._region = await get_closest_discord_region(self._host)
        is_finite_retry = self._max_reconnect_attempts != -1
        max_attempts_str = "inf" if is_finite_retry else self._max_reconnect_attempts
        attempt = 0

        while not self.connected and (not is_finite_retry or attempt < self._max_reconnect_attempts):
            attempt += 1
            LOGGER.info(
                "[NODE-%s] Attempting to establish WebSocket connection (%s/%s)...",
                self._node.name,
                attempt,
                max_attempts_str,
            )

            try:
                self._ws = await self._session.ws_connect(
                    url=self._ws_uri,
                    headers=headers,
                    heartbeat=60,
                )
                await self._node.update_features()
            except (
                aiohttp.ClientConnectorError,
                aiohttp.WSServerHandshakeError,
                aiohttp.ServerDisconnectedError,
            ) as ce:
                if isinstance(ce, aiohttp.ClientConnectorError):
                    LOGGER.warning(
                        "[NODE-%s] Invalid response received; this may indicate that "
                        "Lavalink is not running, or is running on a port different "
                        "to the one you passed to `add_node`.",
                        self.node.name,
                    )
                elif isinstance(ce, aiohttp.WSServerHandshakeError):
                    if ce.status in (
                        401,
                        403,
                    ):  # Special handling for 401/403 (Unauthorized/Forbidden).
                        LOGGER.warning(
                            "[NODE-%s] Authentication failed while trying to establish a connection to the node.",
                            self.node.name,
                        )
                        # We shouldn't try to establish any more connections as correcting this particular error
                        # would require the cog to be reloaded (or the bot to be rebooted), so further attempts
                        # would be futile, and a waste of resources.
                        return

                    LOGGER.warning(
                        "[NODE-%s] The remote server returned code %s, "
                        "the expected code was 101. This usually "
                        "indicates that the remote server is a webserver "
                        "and not Lavalink. Check your ports, and try again.",
                        self.node.name,
                        ce.status,
                    )
                backoff = min(10 * attempt, 60)
                await asyncio.sleep(backoff)
            else:
                await self.node.node_manager.node_connect(self.node)
                #  asyncio.ensure_future(self._listen())

                if (
                    not self._resuming_configured
                    and self._resume_key
                    and (self._resume_timeout and self._resume_timeout > 0)
                ):
                    await self.send(
                        op="configureResuming",
                        key=self._resume_key,
                        timeout=self._resume_timeout,
                    )
                    self._resuming_configured = True

                if self._message_queue:
                    async for message in AsyncIter(self._message_queue):
                        await self.send(**message)

                    self._message_queue.clear()

                await self._listen()
                # Ensure this loop doesn't proceed if _listen returns control back to this
                # function.
                return

        LOGGER.warning(
            "[NODE-%s] A WebSocket connection could not be established within %s attempts.",
            self.node.name,
            attempt,
        )

    async def _listen(self):
        """Listens for websocket messages."""
        async for msg in self._ws:
            LOGGER.debug("[NODE-%s] Received WebSocket message: %s", self.node.name, msg.data)

            if msg.type == aiohttp.WSMsgType.TEXT:
                await self.handle_message(msg.json(loads=ujson.loads))
            elif msg.type == aiohttp.WSMsgType.ERROR:
                exc = self._ws.exception()
                LOGGER.error("[NODE-%s] Exception in WebSocket! %s.", self.node.name, exc)
                break
            elif msg.type in self._closers:
                LOGGER.debug(
                    "[NODE-%s] Received close frame with code %s.",
                    self.node.name,
                    msg.data,
                )
                await self._websocket_closed(msg.data, msg.extra)
                return
        await self._websocket_closed()

    async def _websocket_closed(self, code: int = None, reason: str = None):
        """
        Handles when the websocket is closed.

        Parameters
        ----------
        code: :class:`int`
            The response code.
        reason: :class:`str`
            Reason why the websocket was closed. Defaults to `None`
        """
        LOGGER.debug(
            "[NODE-%s] WebSocket disconnected with the following: code=%s reason=%s",
            self.node.name,
            code,
            reason,
        )
        self._ws = None
        await self.node.node_manager.node_disconnect(self.node, code, reason)
        await self.connect()

    async def handle_message(self, data: dict):
        """
        Handles the response from the websocket.

        Parameters
        ----------
        data: :class:`dict`
            The data given from Lavalink.
        """
        op = data["op"]

        if op == "stats":
            self.node.stats = Stats(self.node, data)
        elif op == "playerUpdate":
            player = self.client.player_manager.get(int(data["guildId"]))

            if not player:
                return

            await player._update_state(data["state"])  # noqa
        elif op == "event":
            await self.handle_event(data)
        else:
            LOGGER.warning("[NODE-%s] Received unknown op: %s", self.node.name, op)

    async def handle_event(self, data: dict):
        """
        Handles the event from Lavalink.

        Parameters
        ----------
        data: :class:`dict`
            The data given from Lavalink.
        """
        player = self.client.player_manager.get(int(data["guildId"]))

        if not player:
            LOGGER.warning(
                "[NODE-%s] Received event for non-existent player! Guild ID: %s",
                self.node.name,
                data["guildId"],
            )
            return

        event_type = data["type"]

        if event_type == "TrackEndEvent":
            track = AudioTrack(self.node, data["track"])
            event = TrackEndEvent(player, track, data["reason"])
        elif event_type == "TrackExceptionEvent":
            event = TrackExceptionEvent(player, player.current, data["error"])
        elif event_type == "TrackStartEvent":
            event = TrackStartEvent(player, player.current)
        elif event_type == "TrackStuckEvent":
            event = TrackStuckEvent(player, player.current, data["thresholdMs"])
        elif event_type == "WebSocketClosedEvent":
            event = WebSocketClosedEvent(player, data["code"], data["reason"], data["byRemote"])
        else:
            LOGGER.warning("[NODE-%s] Unknown event received: %s", self.node.name, event_type)
            return

        await self.client._dispatch_event(event)  # noqa

        if player:
            await player._handle_event(event)  # noqa

    async def send(self, **data: Any):
        """
        Sends a payload to Lavalink.

        Parameters
        ----------
        data: :class:`dict`
            The data sent to Lavalink.
        """
        if self.connected:
            LOGGER.debug("[NODE-%s] Sending payload %s", self.node.name, data)
            await self._ws.send_json(data)
        else:
            LOGGER.debug("[NODE-%s] Send called before WebSocket ready!", self.node.name)
            self._message_queue.append(data)
