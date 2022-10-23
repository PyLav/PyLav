from __future__ import annotations

import asyncio
import contextlib
import datetime
import typing
from typing import TYPE_CHECKING, Any

import aiohttp
import ujson
from dacite import from_dict
from discord.utils import utcnow

from pylav._logging import getLogger
from pylav.constants import PYLAV_NODES
from pylav.endpoints.response_objects import LavalinkEventOpObjects, TrackStartEventOpObject
from pylav.events import (
    SegmentSkippedEvent,
    SegmentsLoadedEvent,
    TrackEndEvent,
    TrackExceptionEvent,
    TrackStartAppleMusicEvent,
    TrackStartBandcampEvent,
    TrackStartClypitEvent,
    TrackStartDeezerEvent,
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
    TrackStartYandexMusicEvent,
    TrackStartYouTubeEvent,
    TrackStartYouTubeMusicEvent,
    TrackStuckEvent,
    WebSocketClosedEvent,
)
from pylav.exceptions import WebsocketNotConnectedError
from pylav.location import get_closest_discord_region
from pylav.node import Stats
from pylav.types import (
    LavalinkEventT,
    LavalinkPlayerUpdateT,
    LavalinkReadyT,
    LavalinkStatsT,
    SegmentSkippedT,
    SegmentsLoadedEventT,
    TrackEndEventT,
    TrackExceptionEventT,
    TrackStartEventT,
    TrackStuckEventT,
    WebSocketClosedEventT,
)
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
        "_closers",
        "_client",
        "ready",
        "_connect_task",
        "_manual_shutdown",
        "_session_id",
        "_resumed",
        "_api_version",
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
        self._session_id: str | None = None
        self._resumed: bool | None = None
        self._api_version: int | None = None

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

    @property
    def session_id(self) -> str:
        """Returns the session ID"""
        return self._session_id

    async def ping(self) -> None:
        """Pings the websocket"""
        if self.connected:
            await self._ws.ping()
        else:
            raise WebsocketNotConnectedError

    async def wait_until_ready(self, timeout: float | None = None):
        await asyncio.wait_for(self.ready.wait(), timeout=timeout)

    async def configure_resume_and_timeout(self):
        if not self._resuming_configured and self._resume_key and (self._resume_timeout and self._resume_timeout > 0):
            await self.node.patch_session(payload={"resumingKey": self._resume_key, "timeout": self._resume_timeout})
            self._resuming_configured = True
            LOGGER.info("[NODE-%s] Node resume has been configured with key: %s", self.node.name, self._resume_key)

    async def connect(self):  # sourcery no-metrics
        """Attempts to establish a connection to Lavalink"""
        try:
            self.ready.clear()
            self.node._ready.clear()
            if self.client.is_shutting_down:
                return
            headers = {
                "Authorization": self._password,
                "User-Id": str(self.bot_id),
                "Client-Name": f"PyLav/{self.lib_version}",
            }

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
                    self._api_version = await self.node.fetch_api_version()
                    ws_uri = self.node.get_endpoint_websocket()
                    self._ws = await self._session.ws_connect(url=ws_uri, headers=headers, heartbeat=60, timeout=600)
                    await self._node.update_features()
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
                            ws_uri,
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

    async def handle_message(self, data: LavalinkPlayerUpdateT | LavalinkEventT | LavalinkStatsT | LavalinkReadyT):
        """
        Handles the response from the websocket.

        Parameters
        ----------
        data: LavalinkPlayerUpdateT|LavalinkEventT| LavalinkStatsT| LavalinkReadyT
            The data given from Lavalink.
        """
        op = data["op"]

        match op:
            case "playerUpdate":
                await self.handle_player_update(data)
            case "stats":
                await self.handle_stats(data)
            case "event":
                await self.handle_event(data)
            case "ready":
                await self.handle_ready(data)
            case __:
                LOGGER.warning("[NODE-%s] Received unknown op: %s", self.node.name, op)

    async def handle_stats(self, data: LavalinkStatsT):
        """
        Handles the stats message from the websocket.

        Parameters
        ----------
        data: LavalinkStatsT
            The data given from Lavalink.
        """

        self.node.stats = Stats(self.node, data)

    async def handle_player_update(self, data: LavalinkPlayerUpdateT):
        """
        Handles the player update message  from the websocket.

        Parameters
        ----------
        data: LavalinkPlayerUpdateT
            The data given from Lavalink.
        """

        if player := self.client.player_manager.get(int(data["guildId"])):
            if (
                (not data["state"]["connected"])
                and player.is_playing
                and self.ready.is_set()
                and player.connected_at < utcnow() - datetime.timedelta(minutes=15)
            ):
                await player.reconnect()
                return
            await player._update_state(data["state"])
        else:
            return

    async def handle_ready(self, data: LavalinkReadyT):
        """
        Handles the ready message from the websocket.

        Parameters
        ----------
        data: LavalinkReadyT
            The data given from Lavalink.
        """
        self._session_id = data["sessionId"]
        self._resumed = data.get("resumed", False)
        self.ready.set()
        self.node._ready.set()
        LOGGER.info("[NODE-%s] Node connected successfully and is now ready to accept commands", self.node.name)
        await self.configure_resume_and_timeout()

    async def handle_event(self, data: LavalinkEventT):
        """
        Handles the event message from Lavalink.

        Parameters
        ----------
        data: LavalinkEventT
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
        event_object = from_dict(data_class=LavalinkEventOpObjects, data=data)
        match data["type"]:
            case "TrackEndEvent":
                data = typing.cast(TrackEndEventT, data)
                from pylav.query import Query
                from pylav.tracks import Track

                requester = None
                track = None
                if player.current and player.current.encoded == data["encodedTrack"]:
                    player.current.timestamp = 0
                    requester = player.current.requester
                    track = player.current

                event = TrackEndEvent(
                    player,
                    track
                    or Track(
                        data=data["encodedTrack"],
                        requester=requester.id if requester else self._client.bot.user.id,
                        query=await Query.from_base64(data["encodedTrack"]),
                        node=self.node,
                    ),
                    self.node,
                    event_object=event_object,
                )
                await player._handle_event(event)
            case "TrackExceptionEvent":
                if self.node.identifier == player.node.identifier:
                    data = typing.cast(TrackExceptionEventT, data)
                    event = TrackExceptionEvent(player, player.current, node=self.node, event_object=event_object)
                    await player._handle_event(event)
                    self.client.dispatch_event(event)
                return
            case "TrackStartEvent":
                data = typing.cast(TrackStartEventT, data)
                track = player.current
                event = TrackStartEvent(player, track, self.node, event_object=event_object)
                await self._process_track_event(player, track, self.node, event_object)
            case "TrackStuckEvent":
                data = typing.cast(TrackStuckEventT, data)
                event = TrackStuckEvent(player, player.current, self.node, event_object=event_object)
                await player._handle_event(event)
            case "WebSocketClosedEvent":
                data = typing.cast(WebSocketClosedEventT, data)
                event = WebSocketClosedEvent(player, self.node, player.channel, event_object=event_object)
            case "SegmentsLoaded":
                data = typing.cast(SegmentsLoadedEventT, data)
                event = SegmentsLoadedEvent(player, self.node, event_object=event_object)
            case "SegmentSkipped":
                data = typing.cast(SegmentSkippedT, data)
                event = SegmentSkippedEvent(player, node=self.node, event_object=event_object)
            case __:
                LOGGER.warning("[NODE-%s] Received unknown event: %s", self.node.name, data["type"])
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

    async def _process_track_event(
        self, player: Player, track: Track, node: Node, event_object: TrackStartEventOpObject
    ) -> None:
        # sourcery no-metrics
        query = await track.query()

        match query.source:
            case "YouTube Music":
                event = TrackStartYouTubeMusicEvent(player, track, node, event_object)
            case "YouTube":
                event = TrackStartYouTubeEvent(player, track, node, event_object)
            case "Spotify":
                event = TrackStartSpotifyEvent(player, track, node, event_object)
            case "Deezer":
                event = TrackStartDeezerEvent(player, track, node, event_object)
            case "Apple Music":
                event = TrackStartAppleMusicEvent(player, track, node, event_object)
            case "HTTP":
                event = TrackStartHTTPEvent(player, track, node, event_object)
            case "SoundCloud":
                event = TrackStartSoundCloudEvent(player, track, node, event_object)
            case "Clyp.it":
                event = TrackStartClypitEvent(player, track, node, event_object)
            case "Twitch":
                event = TrackStartTwitchEvent(player, track, node, event_object)
            case "Bandcamp":
                event = TrackStartBandcampEvent(player, track, node, event_object)
            case "Vimeo":
                event = TrackStartVimeoEvent(player, track, node, event_object)
            case "speak":
                event = TrackStartSpeakEvent(player, track, node, event_object)
            case "GetYarn":
                event = TrackStartGetYarnEvent(player, track, node, event_object)
            case "Mixcloud":
                event = TrackStartMixCloudEvent(player, track, node, event_object)
            case "OverClocked ReMix":
                event = TrackStartOCRMixEvent(player, track, node, event_object)
            case "Pornhub":
                event = TrackStartPornHubEvent(player, track, node, event_object)
            case "Reddit":
                event = TrackStartRedditEvent(player, track, node, event_object)
            case "SoundGasm":
                event = TrackStartSoundgasmEvent(player, track, node, event_object)
            case "TikTok":
                event = TrackStartTikTokEvent(player, track, node, event_object)
            case "Google TTS":
                event = TrackStartGCTTSEvent(player, track, node, event_object)
            case "Niconico":
                event = TrackStartNicoNicoEvent(player, track, node, event_object)
            case "Yandex Music":
                event = TrackStartYandexMusicEvent(player, track, node, event_object)
            case __:
                if query.source == "Local Files" or (
                    query._special_local and (query.is_m3u or query.is_pls or query.is_pylav)
                ):
                    event = TrackStartLocalFileEvent(player, track, node, event_object)
                else:
                    event = TrackStartEvent(player, track, node, event_object)
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
