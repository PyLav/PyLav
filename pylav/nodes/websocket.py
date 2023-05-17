from __future__ import annotations

import asyncio
import contextlib
import datetime
import typing
from typing import Any

import aiohttp
from dacite import from_dict
from packaging.version import Version

from pylav.compat import json
from pylav.constants.builtin_nodes import PYLAV_NODES
from pylav.events.node import WebSocketClosedEvent
from pylav.events.plugins import SegmentSkippedEvent, SegmentsLoadedEvent
from pylav.events.track import TrackEndEvent, TrackExceptionEvent, TrackStartEvent, TrackStuckEvent
from pylav.events.track.track_start import (
    TrackStartAppleMusicEvent,
    TrackStartBandcampEvent,
    TrackStartClypitEvent,
    TrackStartDeezerEvent,
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
)
from pylav.exceptions.node import WebsocketNotConnectedException
from pylav.exceptions.request import HTTPException
from pylav.helpers.misc import ExponentialBackoffWithReset
from pylav.helpers.time import get_now_utc
from pylav.logging import getLogger
from pylav.nodes.api.responses.plugins import SegmentSkipped, SegmentsLoaded
from pylav.nodes.api.responses.websocket import (
    Closed,
    PlayerUpdate,
    Ready,
    Stats,
    TrackEnd,
    TrackException,
    TrackStart,
    TrackStuck,
)
from pylav.nodes.utils import Stats as NodeStats
from pylav.players.tracks.obj import Track
from pylav.type_hints.dict_typing import JSON_DICT_TYPE
from pylav.utils.location import get_closest_discord_region

if typing.TYPE_CHECKING:
    from pylav.core.client import Client
    from pylav.nodes.node import Node
    from pylav.players.player import Player


class WebSocket:
    """Represents the WebSocket connection with Lavalink"""

    __slots__ = (
        "_node",
        "_session",
        "_ws",
        "_host",
        "_port",
        "_password",
        "_ssl",
        "_max_reconnect_attempts",
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
        "_connecting",
        "_player_reconnect_tasks",
        "_logger",
    )

    def __init__(
        self,
        *,
        node: Node,
        host: str,
        port: int,
        password: str,
        resume_timeout: int,
        reconnect_attempts: int,
        ssl: bool,
    ):
        self._node = node
        self._logger = getLogger(f"PyLav.WebSocket-{self.node.name}")
        self._client = self._node.node_manager.client

        self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120), json_serialize=json.dumps)
        self._ws = None
        self._host = host
        self._port = port
        self._password = password
        self._ssl = ssl
        self._max_reconnect_attempts = reconnect_attempts

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
        self._connect_task.add_done_callback(self._done_callback)
        self._manual_shutdown = False
        self._connecting = False
        self._player_reconnect_tasks: dict[int : asyncio.Task] = {}

    def _done_callback(self, task: asyncio.Task) -> None:
        with contextlib.suppress(asyncio.CancelledError):
            exc = task.exception()
            if exc is not None:
                self._logger.error("Error in connect task", exc_info=exc)

    @property
    def is_ready(self) -> bool:
        """Returns whether the websocket is ready"""
        return self.ready.is_set() and self.connected

    @property
    def socket_protocol(self) -> str:
        """The protocol used for the socket connection"""
        return "wss" if self._ssl else "ws"

    @property
    def lib_version(self) -> Version:
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
    def connected(self) -> bool:
        """Returns whether the websocket is connected to Lavalink"""
        return self._ws is not None and not self._ws.closed and self.ready.is_set()

    @property
    def connecting(self) -> bool:
        """Returns whether the websocket is connecting to Lavalink"""
        return not self.ready.is_set()

    @property
    def session_id(self) -> str:
        """Returns the session ID"""
        return self._session_id

    @property
    def resumed(self) -> bool:
        """Returns whether the websocket has resumed"""
        return self._resumed

    @property
    def can_resume(self) -> bool:
        """Returns whether the websocket can resume"""
        return self._resuming_configured

    async def ping(self) -> None:
        """Pings the websocket"""
        if self.connected:
            await self._ws.ping()
        else:
            raise WebsocketNotConnectedException

    async def wait_until_ready(self, timeout: float | None = None) -> None:
        """Waits until the websocket is ready"""
        await asyncio.wait_for(self.ready.wait(), timeout=timeout)

    async def configure_resume_and_timeout(self) -> None:
        """Configures the resume and timeout"""
        payload = {"timeout": self._resume_timeout} if self._resume_timeout > 0 else {}
        payload["resuming"] = self._session_id is not None
        await self.node.patch_session(payload=payload)
        self._resuming_configured = self._session_id is not None
        self._logger.info("Node resume has been configured with sessionId: %s", self._session_id)

    async def connect(self) -> None:  # sourcery skip: low-code-quality
        """Attempts to establish a connection to Lavalink"""
        try:
            self.ready.clear()
            self.node._ready.clear()
            if self.client.is_shutting_down:
                return
            self._connecting = True
            headers = {
                "Authorization": self._password,
                "User-Id": str(self.bot_id),
                "Client-Name": f"PyLav/{self.lib_version}",
            }
            if self._node.identifier in PYLAV_NODES:
                # Since these nodes are proxied by Cloudflare - lets add a special case to properly identify them.
                self._node._region, self._node._coordinates = PYLAV_NODES[self._node.identifier]
            else:
                self._node._region, self._node._coordinates = await get_closest_discord_region(self._host)

            self._session_id = await self.node.config.fetch_session()
            is_finite_retry = self._max_reconnect_attempts != -1
            max_attempts_str = self._max_reconnect_attempts if is_finite_retry else "inf"
            attempt = 0
            backoff = ExponentialBackoffWithReset(base=3)
            while not self.connected and (not is_finite_retry or attempt < self._max_reconnect_attempts):
                if self._manual_shutdown:
                    self._connecting = False
                    return
                attempt += 1
                self._logger.info(
                    "Attempting to establish WebSocket connection (%s/%s)",
                    attempt,
                    max_attempts_str,
                )
                await self.node.fetch_api_version()
                self._api_version = self.node.api_version
                if self._api_version < 4:
                    self._logger.critical(
                        "Node %s is not running a supported Lavalink version (%s:%s - %s)",
                        self._node.identifier,
                        self._host,
                        self._port,
                        self.node.version,
                    )
                    raise OSError
                if self._session_id is not None:
                    headers["Session-Id"] = self._session_id
                ws_uri = self.node.get_endpoint_websocket()
                try:
                    self._ws = await self._session.ws_connect(url=ws_uri, headers=headers, heartbeat=60, timeout=600)
                    await self._node.update_features()
                    self._connecting = False
                    backoff.reset()
                except (
                    aiohttp.ClientConnectorError,
                    aiohttp.WSServerHandshakeError,
                    aiohttp.ServerDisconnectedError,
                ) as ce:
                    if self.client.is_shutting_down:
                        self._connecting = False
                        return
                    if isinstance(ce, aiohttp.ClientConnectorError):
                        self._logger.warning(
                            "Invalid response received; this may indicate that "
                            "Lavalink is not running, or is running on a port different "
                            "to the one you passed to `add_node` (%s - %s)",
                            ws_uri,
                            headers,
                        )
                    elif isinstance(ce, aiohttp.WSServerHandshakeError):
                        if ce.status in (
                            401,
                            403,
                        ):  # Special handling for 401/403 (Unauthorized/Forbidden).
                            self._logger.warning(
                                "Authentication failed while trying to establish a connection to the node",
                            )
                            # We shouldn't try to establish any more connections as correcting this particular error
                            # would require the cog to be reloaded (or the bot to be rebooted), so further attempts
                            # would be futile, and a waste of resources.
                            self._connecting = False
                            return

                        self._logger.warning(
                            "The remote server returned code %s, "
                            "the expected code was 101. This usually "
                            "indicates that the remote server is a webserver "
                            "and not Lavalink. Check your ports, and try again",
                            ce.status,
                        )
                    await asyncio.sleep(backoff.delay())
                else:
                    #  asyncio.ensure_future(self._listen())

                    await self.node.node_manager.node_connect(self.node)
                    await self._listen()
                    self._logger.debug("Websocket lister returned")
                    # Ensure this loop doesn't proceed if _listen returns control back to this
                    # function.
                    return

            self._logger.warning(
                "A WebSocket connection could not be established within %s attempts",
                attempt,
            )
        except OSError:
            self._connecting = False
            if self._ws and not self._ws.closed and not self._ws._closing:
                await self._ws.close(code=4014, message=b"Shutting down")
            await self._session.close()
            self.ready.set()
            self.node._ready.set()
            self._connect_task.cancel()
            return
        except Exception:  # noqa
            self._logger.exception(
                "An exception occurred while attempting to connect to the node",
            )

    async def _listen(self) -> None:
        """Listens for websocket messages"""
        try:
            async for msg in self._ws:
                if self._manual_shutdown:
                    return
                self._logger.trace("Received WebSocket message: %s", msg.data)
                if msg.type == aiohttp.WSMsgType.CLOSED:
                    self._logger.info(
                        "Received close frame with code %s",
                        msg.data,
                    )
                    await self._websocket_closed(msg.data, msg.extra)
                    return
                else:
                    await self.handle_message(msg.json(loads=json.loads))
                # elif msg.type == aiohttp.WSMsgType.ERROR and not self.client.is_shutting_down:
                #     exc = self._ws.exception()
                #     self._logger.error("Exception in WebSocket! %s", exc)
                #     break
            await self._websocket_closed()
        except Exception:  # noqa
            if not self.client.is_shutting_down:
                self._logger.exception("Exception in WebSocket!")
                await self._websocket_closed()

    async def _websocket_closed(self, code: int = None, reason: str = None) -> None:
        """
        Handles when the websocket is closed.

        Parameters
        ----------
        code: :class:`int`
            The response code.
        reason: :class:`str`
            Reason why the websocket was closed. Defaults to `None`
        """
        self._logger.info(
            "WebSocket disconnected with the following: code=%s reason=%s",
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
        self._connect_task.add_done_callback(self._done_callback)

    async def handle_message(self, data: JSON_DICT_TYPE) -> None:
        """
        Handles the response from the websocket.

        Parameters
        ----------
        data: LavalinkPlayerUpdateT|LavalinkEventT| LavalinkStatsT| LavalinkReadyT
            The data given from Lavalink.
        """
        match data["op"]:
            case "playerUpdate":
                data = from_dict(data_class=PlayerUpdate, data=data)
                await self.handle_player_update(data)
            case "stats":
                data = from_dict(data_class=Stats, data=data)
                await self.handle_stats(data)
            case "event":
                match data["type"]:
                    case "TrackStartEvent":
                        data = from_dict(data_class=TrackStart, data=data)
                    case "TrackEndEvent":
                        data = from_dict(data_class=TrackEnd, data=data)
                    case "TrackExceptionEvent":
                        data = from_dict(data_class=TrackException, data=data)
                    case "TrackStuckEvent":
                        data = from_dict(data_class=TrackStuck, data=data)
                    case "WebSocketClosedEvent":
                        data = from_dict(data_class=Closed, data=data)
                    case "SegmentsLoaded":
                        data = from_dict(data_class=SegmentsLoaded, data=data)
                    case "SegmentSkipped":
                        data = from_dict(data_class=SegmentSkipped, data=data)
                    case __:
                        self._logger.warning("Received unknown event: %s - ignoring it", data["type"])
                        return
                await self.handle_event(data)
            case "ready":
                data = from_dict(data_class=Ready, data=data)
                await self.handle_ready(data)
            case __:
                self._logger.warning("Received unknown op: %s", data["op"])

    async def handle_stats(self, data: Stats) -> None:
        """
        Handles the stats message from the websocket.

        Parameters
        ----------
        data: LavalinkStatsOpObject
            The data given from Lavalink.
        """

        self.node.stats = NodeStats(self.node, data)

    async def handle_player_update(self, data: PlayerUpdate) -> None:
        """
        Handles the player update message from the websocket.

        Parameters
        ----------
        data: LavalinkPlayerUpdateT
            The data given from Lavalink.
        """

        if player := self.client.player_manager.get(int(data.guildId)):
            if (
                (not data.state.connected)
                and player.is_active
                and self.ready.is_set()
                and player.connected_at < get_now_utc() - datetime.timedelta(minutes=5)
            ):
                if player.guild.id in self._player_reconnect_tasks:
                    self._player_reconnect_tasks[player.guild.id].cancel()
                self._player_reconnect_tasks[player.guild.id] = asyncio.create_task(self.maybe_reconnect_player(player))
                return
            await player._update_state(data.state)
        else:
            return

    async def maybe_reconnect_player(self, player: Player) -> None:
        """
        Attempts to reconnect the player if it is not connected.

        Parameters
        ----------
        player: :class:`Player`
            The player to reconnect.
        """
        await asyncio.sleep(5)
        session = await player.node.fetch_session_player(player.guild.id)
        if isinstance(session, HTTPException):
            return

        if (
            (not session.state.connected)
            and player.is_active
            and self.ready.is_set()
            and player.connected_at < get_now_utc() - datetime.timedelta(minutes=5)
        ):
            self._logger.debug("Reconnecting stalled player for %s", player.guild.id)
            await player.reconnect()
            return

    async def handle_ready(self, data: Ready) -> None:
        """
        Handles the ready message from the websocket.

        Parameters
        ----------
        data: LavalinkReadyT
            The data given from Lavalink.
        """
        self._session_id = data.sessionId
        self._resumed = data.resumed
        self.ready.set()
        self.node._ready.set()
        self._logger.info(
            "Node %s successfully and is now ready to accept commands: Session ID: %s",
            "resumed" if self._resumed else "connected",
            self._session_id,
        )
        await self.node.config.update_session(self._session_id)
        await self.configure_resume_and_timeout()

    async def handle_event(
        self,
        data: (TrackStart | TrackEnd | TrackException | TrackStuck | Closed | SegmentsLoaded | SegmentSkipped),
    ):
        """
        Handles the event message from Lavalink.

        Parameters
        ----------
        data: LavalinkEventT
            The data given from Lavalink.
        """
        if self.client.is_shutting_down:
            return
        player = self.client.player_manager.get(int(data.guildId))
        if not player:
            await asyncio.sleep(3)
            player = self.client.player_manager.get(int(data.guildId))
        if not player:
            self._logger.debug(
                "Received event for non-existent player! Guild ID: %s",
                data.guildId,
            )
            return
        track = await self._get_track(data, player)
        match data.type:
            case "TrackEndEvent":
                data = typing.cast(TrackEnd, data)
                event = TrackEndEvent(
                    player,
                    track,
                    self.node,
                    event_object=data,
                )
                await player._handle_event(event)
            case "TrackExceptionEvent":
                if self.node.identifier == player.node.identifier:
                    data = typing.cast(TrackException, data)
                    event = TrackExceptionEvent(player, track, node=self.node, event_object=data)
                    await player._handle_event(event)
                    self.client.dispatch_event(event)
                return
            case "TrackStartEvent":
                data = typing.cast(TrackStart, data)
                new_track = await player.update_current_duration()
                if new_track:
                    track = new_track
                event = TrackStartEvent(player, track, self.node, event_object=data)
                await self._process_track_event(player, track, self.node, data)
            case "TrackStuckEvent":
                data = typing.cast(TrackStuck, data)
                event = TrackStuckEvent(player, track, self.node, event_object=data)
                await player._handle_event(event)
            case "WebSocketClosedEvent":
                data = typing.cast(Closed, data)
                event = WebSocketClosedEvent(player, self.node, player.channel, event_object=data)
                if self.node.identifier == player.node.identifier:
                    await player._handle_event(event)
            case "SegmentsLoaded":
                data = typing.cast(SegmentsLoaded, data)
                event = SegmentsLoadedEvent(player, self.node, event_object=data)
            case "SegmentSkipped":
                data = typing.cast(SegmentSkipped, data)
                event = SegmentSkippedEvent(player, node=self.node, event_object=data)
            case __:
                self._logger.warning("Received unknown event: %s", data.type)
                return

        self.client.dispatch_event(event)

    async def _get_track(self, data, player) -> Track | None:
        if not isinstance(data, (TrackStart, TrackEnd, TrackException, TrackStuck)):
            return
        requester = None
        if player.current and player.current.encoded == data.track.encoded:
            requester = player.current.requester
        return await Track.build_track(
            data=data.track,
            requester=requester.id if requester else self._client.bot.user.id,
            query=None,
            node=self.node,
            player_instance=player,
        )

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
            self._logger.trace("Sending payload %s", data)
            try:
                await self._ws.send_json(data, dumps=json.dumps)
            except ConnectionResetError:
                self._logger.debug("Send called before WebSocket ready!")
        else:
            self._logger.debug("Send called before WebSocket ready!")

    async def _process_track_event(self, player: Player, track: Track, node: Node, event_object: TrackStart) -> None:
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
                if query.source == "Local" or (
                    query._special_local and (query.is_m3u or query.is_pls or query.is_pylav)
                ):
                    event = TrackStartLocalFileEvent(player, track, node, event_object)
                else:
                    event = TrackStartEvent(player, track, node, event_object)
        self.client.dispatch_event(event)

    async def close(self) -> None:
        """Closes the websocket connection."""
        self._connect_task.cancel()
        if self._ws and not self._ws.closed and not self._ws._closing:
            await self._ws.close(code=4014, message=b"Shutting down")
        await self._session.close()

    async def manual_closure(self, managed_node: bool = False) -> None:
        """Triggers a manual closure of the websocket connection."""
        self._manual_shutdown = managed_node
        if self._ws and not self._ws.closed and not self._ws._closing:
            with contextlib.suppress(Exception):
                await self._ws.close(code=4014, message=b"Shutting down")
        await self._websocket_closed(202, "Manual websocket shutdown requested")
