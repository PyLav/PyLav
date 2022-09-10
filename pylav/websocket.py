from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING, Any

import aiohttp
import ujson

from pylav._logging import getLogger
from pylav.constants import PYLAV_NODES
from pylav.events import (
    SegmentSkippedEvent,
    SegmentsLoadedEvent,
    TrackEndEvent,
    TrackExceptionEvent,
    TrackStartAppleMusicEvent,
    TrackStartBandcampEvent,
    TrackStartClypitEvent,
    TrackStartEvent,
    TrackStartGCTTSEvent,
    TrackStartGetYarnEvent,
    TrackStartHTTPEvent,
    TrackStartLocalFileEvent,
    TrackStartMixCloudEvent,
    TrackStartNicoNicoEvent,
    TrackStartOCRMixEvent,
    TrackStartPornHubEvent,
    TrackStartRedditEvent,
    TrackStartSoundCloudEvent,
    TrackStartSoundgasmEvent,
    TrackStartSpeakEvent,
    TrackStartSpotifyEvent,
    TrackStartTikTokEvent,
    TrackStartTwitchEvent,
    TrackStartVimeoEvent,
    TrackStartYouTubeEvent,
    TrackStartYouTubeMusicEvent,
    TrackStuckEvent,
    WebSocketClosedEvent,
)
from pylav.exceptions import WebsocketNotConnectedError
from pylav.location import get_closest_discord_region
from pylav.node import Stats
from pylav.utils import AsyncIter, ExponentialBackoffWithReset

if TYPE_CHECKING:
    from pylav.client import Client
    from pylav.node import Node
    from pylav.player import Player
    from pylav.tracks import Track

LOGGER = getLogger("PyLav.WebSocket")


def _done_callback(task: asyncio.Task) -> None:
    with contextlib.suppress(asyncio.CancelledError):
        exc = task.exception()
        if exc is not None:
            LOGGER.error("Error in connect task", exc_info=exc)


class WebSocket:
    """Represents the WebSocket connection with Lavalink"""

    __slots__ = (
        "_node",
        "_session",
        "_ws",
        "_message_queue",
        "_host",
        "_port",
        "_password",
        "_ssl",
        "_max_reconnect_attempts",
        "_resume_key",
        "_resume_timeout",
        "_resuming_configured",
        "_ws_uri",
        "_closers",
        "_client",
        "ready",
        "_connect_task",
        "_manual_shutdown",
    )

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

        self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120), json_serialize=ujson.dumps)
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
        self.ready = asyncio.Event()
        self._connect_task = asyncio.ensure_future(self.connect())
        self._connect_task.add_done_callback(_done_callback)
        self._manual_shutdown = False

    @property
    def is_ready(self) -> bool:
        """Returns whether the websocket is ready"""
        return self.ready.is_set() and self.connected

    @property
    def socket_protocol(self) -> str:
        """The protocol used for the socket connection"""
        return "wss" if self._ssl else "ws"

    @property
    def lib_version(self) -> str:
        """Returns the PyLav library version"""
        return self._client.lib_version

    @property
    def bot_id(self) -> str:
        """Returns the bot's ID"""
        return self._client.bot_id

    @property
    def node(self) -> Node:
        """Returns the :class:`Node` instance"""
        return self._node

    @property
    def client(self) -> Client:
        """Returns the :class:`Client` instance"""
        return self._client

    @property
    def connected(self):
        """Returns whether the websocket is connected to Lavalink"""
        return self._ws is not None and not self._ws.closed and self.ready.is_set()

    @property
    def connecting(self):
        """Returns whether the websocket is connecting to Lavalink"""
        return not self.ready.is_set()

    async def ping(self) -> None:
        """Pings the websocket"""
        if self.connected:
            await self._ws.ping()
        else:
            raise WebsocketNotConnectedError

    async def wait_until_ready(self, timeout: float | None = None):
        await asyncio.wait_for(self.ready.wait(), timeout=timeout)

    async def connect(self):  # sourcery no-metrics
        """Attempts to establish a connection to Lavalink"""
        try:
            self.ready.clear()
            self.node._ready.clear()
            headers = {
                "Authorization": self._password,
                "User-Id": str(self.bot_id),
                "Client-Name": f"PyLav/{self.lib_version}",
            }

            if self.client.is_shutting_down:
                return
            if self._resuming_configured and self._resume_key:
                headers["Resume-Key"] = self._resume_key
            if self._node.identifier in PYLAV_NODES:
                # Since these nodes are proxied by Cloudflare - lets add a special case to properly identify them.
                self._node._region, self._node._coordinates = PYLAV_NODES[self._node.identifier]
            else:
                self._node._region, self._node._coordinates = await get_closest_discord_region(self._host)

            is_finite_retry = self._max_reconnect_attempts != -1
            max_attempts_str = self._max_reconnect_attempts if is_finite_retry else "inf"
            attempt = 0
            backoff = ExponentialBackoffWithReset(base=3)
            while not self.connected and (not is_finite_retry or attempt < self._max_reconnect_attempts):
                if self._manual_shutdown:
                    return
                attempt += 1
                LOGGER.info(
                    "[NODE-%s] Attempting to establish WebSocket connection (%s/%s)",
                    self._node.name,
                    attempt,
                    max_attempts_str,
                )

                try:
                    self._ws = await self._session.ws_connect(
                        url=self._ws_uri, headers=headers, heartbeat=60, timeout=600
                    )
                    await self._node.update_features()
                    self.ready.set()
                    self.node._ready.set()
                    backoff.reset()
                except (
                    aiohttp.ClientConnectorError,
                    aiohttp.WSServerHandshakeError,
                    aiohttp.ServerDisconnectedError,
                ) as ce:
                    if self.client.is_shutting_down:
                        return
                    if isinstance(ce, aiohttp.ClientConnectorError):
                        LOGGER.warning(
                            "[NODE-%s] Invalid response received; this may indicate that "
                            "Lavalink is not running, or is running on a port different "
                            "to the one you passed to `add_node` (%s - %s)",
                            self.node.name,
                            self._ws_uri,
                            headers,
                        )
                    elif isinstance(ce, aiohttp.WSServerHandshakeError):
                        if ce.status in (
                            401,
                            403,
                        ):  # Special handling for 401/403 (Unauthorized/Forbidden).
                            LOGGER.warning(
                                "[NODE-%s] Authentication failed while trying to establish a connection to the node",
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
                            "and not Lavalink. Check your ports, and try again",
                            self.node.name,
                            ce.status,
                        )
                    await asyncio.sleep(backoff.delay())
                else:
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
                    await self.node.node_manager.node_connect(self.node)
                    if self._message_queue:
                        async for message in AsyncIter(self._message_queue):
                            await self.send(**message)

                        self._message_queue.clear()
                    await self._listen()
                    LOGGER.debug("[NODE-%s] _listen returned", self.node.name)
                    # Ensure this loop doesn't proceed if _listen returns control back to this
                    # function.
                    return

            LOGGER.warning(
                "[NODE-%s] A WebSocket connection could not be established within %s attempts",
                self.node.name,
                attempt,
            )
        except Exception:
            LOGGER.exception(
                "[NODE-%s] An exception occurred while attempting to connect to the node",
                self.node.name,
            )

    async def _listen(self):
        """Listens for websocket messages"""
        try:
            async for msg in self._ws:
                if self._manual_shutdown:
                    return
                LOGGER.trace("[NODE-%s] Received WebSocket message: %s", self.node.name, msg.data)
                if msg.type == aiohttp.WSMsgType.CLOSED:
                    LOGGER.info(
                        "[NODE-%s] Received close frame with code %s",
                        self.node.name,
                        msg.data,
                    )
                    await self._websocket_closed(msg.data, msg.extra)
                    return
                else:
                    await self.handle_message(msg.json(loads=ujson.loads))
                # elif msg.type == aiohttp.WSMsgType.ERROR and not self.client.is_shutting_down:
                #     exc = self._ws.exception()
                #     LOGGER.error("[NODE-%s] Exception in WebSocket! %s", self.node.name, exc)
                #     break
            await self._websocket_closed()
        except Exception:
            if not self.client.is_shutting_down:
                LOGGER.exception("[NODE-%s] Exception in WebSocket!", self.node.name)
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
        LOGGER.info(
            "[NODE-%s] WebSocket disconnected with the following: code=%s reason=%s",
            self.node.name,
            code,
            reason,
        )
        self._ws = None
        await self.node.node_manager.node_disconnect(self.node, code, reason)
        if not self._connect_task.cancelled():
            self._connect_task.cancel()
        if self._manual_shutdown:
            await self.close()
            return
        self._connect_task = asyncio.ensure_future(self.connect())
        self._connect_task.add_done_callback(_done_callback)

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
            if player := self.client.player_manager.get(int(data["guildId"])):
                await player._update_state(data["state"])
            else:
                return

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
        if self.client.is_shutting_down:
            return
        player = self.client.player_manager.get(int(data["guildId"]))
        if not player:
            LOGGER.debug(
                "[NODE-%s] Received event for non-existent player! Guild ID: %s",
                self.node.name,
                data["guildId"],
            )
            return

        event_type = data["type"]
        if event_type == "TrackEndEvent":
            from pylav.query import Query
            from pylav.tracks import Track

            requester = None
            track = None
            if player.current and player.current.track == data["track"]:
                player.current.timestamp = 0
                requester = player.current.requester
                track = player.current

            event = TrackEndEvent(
                player,
                track
                or Track(
                    data=data["track"],
                    requester=requester.id if requester else self._client.bot.user.id,
                    query=await Query.from_base64(data["track"]),
                    node=self.node,
                ),
                data["reason"],
                self.node,
            )

            await player._handle_event(event)
        elif event_type == "TrackExceptionEvent":
            event = TrackExceptionEvent(player, player.current, data["error"], node=self.node)
            if self.node.identifier == player.node.identifier:
                await player._handle_event(event)
        elif event_type == "TrackStartEvent":
            track = player.current
            event = TrackStartEvent(player, track, self.node)
            await self._process_track_event(player, track, self.node)
        elif event_type == "TrackStuckEvent":
            event = TrackStuckEvent(player, player.current, data["thresholdMs"], self.node)
            await player._handle_event(event)
        elif event_type == "WebSocketClosedEvent":
            event = WebSocketClosedEvent(
                player, data["code"], data["reason"], data["byRemote"], self.node, player.channel
            )
        elif event_type == "SegmentsLoaded":
            event = SegmentsLoadedEvent(player, data["segments"], self.node)
        elif event_type == "SegmentSkipped":
            event = SegmentSkippedEvent(player, node=self.node, **data["segment"])
        else:
            LOGGER.warning("[NODE-%s] Unknown event received: %s", self.node.name, event_type)
            return

        self.client.dispatch_event(event)

    async def send(self, **data: Any):
        """
        Sends a payload to Lavalink.

        Parameters
        ----------
        data: :class:`dict`
            The data sent to Lavalink.
        """
        if self._manual_shutdown:
            return
        if self.connected:
            LOGGER.trace("[NODE-%s] Sending payload %s", self.node.name, data)
            try:
                await self._ws.send_json(data)
            except ConnectionResetError:
                LOGGER.debug("[NODE-%s] Send called before WebSocket ready!", self.node.name)
                self._message_queue.append(data)
        else:
            LOGGER.debug("[NODE-%s] Send called before WebSocket ready!", self.node.name)
            self._message_queue.append(data)

    async def _process_track_event(self, player: Player, track: Track, node: Node) -> None:
        # sourcery no-metrics
        if await track.is_youtube_music():
            event = TrackStartYouTubeMusicEvent(player, track, node)
        elif await track.is_spotify():
            event = TrackStartSpotifyEvent(player, track, node)
        elif await track.is_apple_music():
            event = TrackStartAppleMusicEvent(player, track, node)
        elif await track.is_local():
            event = TrackStartLocalFileEvent(player, track, node)
        elif await track.is_http():
            event = TrackStartHTTPEvent(player, track, node)
        elif await track.is_speak():
            event = TrackStartSpeakEvent(player, track, node)
        elif await track.is_youtube():
            event = TrackStartYouTubeEvent(player, track, node)
        elif await track.is_clypit():
            event = TrackStartClypitEvent(player, track, node)
        elif await track.is_getyarn():
            event = TrackStartGetYarnEvent(player, track, node)
        elif await track.is_twitch():
            event = TrackStartTwitchEvent(player, track, node)
        elif await track.is_vimeo():
            event = TrackStartVimeoEvent(player, track, node)
        elif await track.is_mixcloud():
            event = TrackStartMixCloudEvent(player, track, node)
        elif await track.is_ocremix():
            event = TrackStartOCRMixEvent(player, track, node)
        elif await track.is_pornhub():
            event = TrackStartPornHubEvent(player, track, node)
        elif await track.is_reddit():
            event = TrackStartRedditEvent(player, track, node)
        elif await track.is_soundgasm():
            event = TrackStartSoundgasmEvent(player, track, node)
        elif await track.is_tiktok():
            event = TrackStartTikTokEvent(player, track, node)
        elif await track.is_bandcamp():
            event = TrackStartBandcampEvent(player, track, node)
        elif await track.is_soundcloud():
            event = TrackStartSoundCloudEvent(player, track, node)
        elif await track.is_gctts():
            event = TrackStartGCTTSEvent(player, track, node)
        elif await track.is_niconico():
            event = TrackStartNicoNicoEvent(player, track, node)
        else:  # This should never happen
            event = TrackStartEvent(player, track, node)
        self.client.dispatch_event(event)

    async def close(self):
        self._connect_task.cancel()
        if self._ws and not self._ws.closed and not self._ws._closing:
            await self._ws.close(code=4014, message=b"Shutting down")
        await self._session.close()

    async def manual_closure(self, managed_node: bool = False):
        self._manual_shutdown = managed_node
        if self._ws and not self._ws.closed and not self._ws._closing:
            with contextlib.suppress(Exception):
                await self._ws.close(code=4014, message=b"Shutting down")
        await self._websocket_closed(202, "Manual websocket shutdown requested")
