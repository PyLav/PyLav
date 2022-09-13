from __future__ import annotations

import asyncio
import collections
import contextlib
import datetime
import pathlib
import random
import re
import time
from collections.abc import Coroutine
from typing import TYPE_CHECKING, Any, Literal

import asyncstdlib
import discord
from discord import VoiceProtocol
from discord.abc import Messageable
from discord.utils import utcnow

from pylav._logging import getLogger
from pylav.constants import REGION_TO_COUNTRY_COORDINATE_MAPPING
from pylav.events import (
    FiltersAppliedEvent,
    NodeChangedEvent,
    PlayerDisconnectedEvent,
    PlayerMovedEvent,
    PlayerPausedEvent,
    PlayerRepeatEvent,
    PlayerRestoredEvent,
    PlayerResumedEvent,
    PlayerStoppedEvent,
    PlayerUpdateEvent,
    PlayerVolumeChangedEvent,
    QueueEndEvent,
    QueueShuffledEvent,
    QueueTrackPositionChangedEvent,
    QueueTracksRemovedEvent,
    QuickPlayEvent,
    TrackAutoPlayEvent,
    TrackEndEvent,
    TrackExceptionEvent,
    TrackPreviousRequestedEvent,
    TrackResumedEvent,
    TrackSeekEvent,
    TrackSkippedEvent,
    TracksRequestedEvent,
    TrackStuckEvent,
)
from pylav.exceptions import EntryNotFoundError, NoNodeWithRequestFunctionalityAvailable, TrackNotFound
from pylav.filters import (
    ChannelMix,
    Distortion,
    Echo,
    Equalizer,
    Karaoke,
    LowPass,
    Rotation,
    Timescale,
    Vibrato,
    Volume,
)
from pylav.filters.tremolo import Tremolo
from pylav.query import Query
from pylav.sql.models import PlayerModel, PlayerStateModel, PlaylistModel
from pylav.tracks import Track
from pylav.types import BotT, InteractionT
from pylav.utils import AsyncIter, PlayerQueue, SegmentCategory, TrackHistoryQueue, format_time, get_time_string

if TYPE_CHECKING:
    from pylav.client import Client
    from pylav.node import Node
    from pylav.player_manager import PlayerManager
    from pylav.radio import RadioBrowser

try:
    from redbot.core.i18n import Translator

    _ = Translator("PyLavPlayer", pathlib.Path(__file__))
except ImportError:
    _ = lambda x: x

LOGGER = getLogger("PyLav.Player")

ENDPONT_REGEX = re.compile(r"^(?P<region>.*?)\d+.discord.media:\d+$")


def _done_callback(task: asyncio.Task) -> None:
    with contextlib.suppress(asyncio.CancelledError):
        exc = task.exception()
        if exc is not None:
            LOGGER.error("Error in task %s", task.get_name(), exc_info=exc)


class Player(VoiceProtocol):
    __slots__ = (
        "ready",
        "bot",
        "client",
        "guild_id",
        "_channel",
        "channel_id",
        "node",
        "player_manager",
        "_original_node",
        "_voice_state",
        "_region",
        "_coordinates",
        "_connected",
        "connected_at",
        "paused",
        "_config",
        "stopped",
        "_last_update",
        "_last_position",
        "position_timestamp",
        "_ping",
        "queue",
        "history",
        "current",
        "_post_init_completed",
        "_autoplay_playlist",
        "_restored",
        "_effect_enabled",
        "_volume",
        "_equalizer",
        "_karaoke",
        "_timescale",
        "_tremolo",
        "_vibrato",
        "_rotation",
        "_distortion",
        "_lowpass",
        "_echo",
        "_channelmix",
        "_extras",
        "_last_alone_paused_check",
        "_was_alone_paused",
        "_last_alone_dc_check",
        "_last_empty_queue_check",
        "_waiting_for_node",
        "last_track",
        "next_track",
        "_global_config",
        "_lavalink",
    )
    _config: PlayerModel
    _global_config: PlayerModel
    _lavalink: Client

    def __init__(
        self,
        client: BotT,
        channel: discord.channel.VocalGuildChannel,
        *,
        node: Node = None,
    ):
        self.ready = asyncio.Event()
        self.bot = self.client = client
        self.guild_id = str(channel.guild.id)
        self._channel = None
        self.channel = channel
        self.channel_id = channel.id
        self.node: Node = node
        self.player_manager: PlayerManager = None  # type: ignore
        self._original_node: Node = None  # type: ignore
        self._voice_state = {}
        self._region = channel.rtc_region or "unknown_pylav"
        self._coordinates = REGION_TO_COUNTRY_COORDINATE_MAPPING.get(self._region, (0, 0))
        self._connected = False
        self.connected_at = utcnow()
        self.last_track = None
        self.next_track = None

        self._user_data = {}

        self.paused = False
        self.stopped = False
        self._last_update = 0
        self._last_position = 0
        self.position_timestamp = 0
        self._ping = 0
        self.queue: PlayerQueue[Track] = PlayerQueue()
        self.history: TrackHistoryQueue[Track] = TrackHistoryQueue(maxsize=100)
        self.current: Track | None = None
        self._post_init_completed = False
        self._autoplay_playlist: PlaylistModel = None  # type: ignore
        self._restored = False

        # Filters
        self._effect_enabled: bool = False
        self._volume: Volume = Volume.default()
        self._equalizer: Equalizer = Equalizer.default()
        self._karaoke: Karaoke = Karaoke.default()
        self._timescale: Timescale = Timescale.default()
        self._tremolo: Tremolo = Tremolo.default()
        self._vibrato: Vibrato = Vibrato.default()
        self._rotation: Rotation = Rotation.default()
        self._distortion: Distortion = Distortion.default()
        self._echo: Echo = Echo.default()
        self._low_pass: LowPass = LowPass.default()
        self._channel_mix: ChannelMix = ChannelMix.default()

        self._config = None  # type: ignore
        self._extras = {}

        self._last_alone_paused_check = 0
        self._was_alone_paused = False
        self._last_alone_dc_check = 0
        self._last_empty_queue_check = 0

        self._waiting_for_node = asyncio.Event()

    def __repr__(self):
        return (
            f"<Player id={self.guild.id} "
            f"channel={self.channel.id} "
            f"playing={self.is_playing} "
            f"queue={self.queue.size()} "
            f"node={self.node}>"
        )

    async def post_init(
        self,
        node: Node,
        player_manager: PlayerManager,
        config: PlayerModel,
        pylav: Client,
        requester: discord.Member = None,
    ) -> None:
        # sourcery no-metrics
        if self._post_init_completed:
            return
        self._lavalink = pylav
        self.player_manager = player_manager
        self.node = node
        self._config = config
        self._global_config = player_manager.global_config
        self._extras = await config.fetch_extras()
        self._post_init_completed = True

        player_state = await self.player_manager.client.player_state_db_manager.fetch_player(self.channel.guild.id)
        if player_state:
            await self.restore(player=player_state, requester=requester or self.guild.me)
            await self.player_manager.client.player_state_db_manager.delete_player(self.channel.guild.id)
            LOGGER.info("Player restored in postinit - %s", self)
        else:
            self._volume = Volume(await player_manager.client.player_config_manager.get_volume(self.guild.id))
            effects = await config.fetch_effects()
            if (v := effects.get("volume", None)) and (f := Volume.from_dict(v)) and f.changed:
                self._volume = f
            if (eq := effects.get("equalizer", None)) and (f := Equalizer.from_dict(eq)) and f.changed:
                self._equalizer = f
            if (k := effects.get("karaoke", None)) and (f := Karaoke.from_dict(k)) and f.changed:
                self._karaoke = f
            if (ts := effects.get("timescale", None)) and (f := Timescale.from_dict(ts)) and f.changed:
                self._timescale = f
            if (tr := effects.get("tremolo", None)) and (f := Tremolo.from_dict(tr)) and f.changed:
                self._tremolo = f
            if (vb := effects.get("vibrato", None)) and (f := Vibrato.from_dict(vb)) and f.changed:
                self._vibrato = f
            if (ro := effects.get("rotation", None)) and (f := Rotation.from_dict(ro)) and f.changed:
                self._rotation = f
            if (di := effects.get("distortion", None)) and (f := Distortion.from_dict(di)) and f.changed:
                self._distortion = f
            if (lo := effects.get("lowpass", None)) and (f := LowPass.from_dict(lo)) and f.changed:
                self._low_pass = f
            if (ch := effects.get("channel_mix", None)) and (f := ChannelMix.from_dict(ch)) and f.changed:
                self._channel_mix = f
            if (echo := effects.get("echo", None)) and (f := Echo.from_dict(echo)) and f.changed:
                self._echo = f
            if await asyncstdlib.any(
                f.changed
                for f in [
                    self.equalizer,
                    self.karaoke,
                    self.timescale,
                    self.tremolo,
                    self.vibrato,
                    self.rotation,
                    self.distortion,
                    self.low_pass,
                    self.channel_mix,
                    self.echo,
                ]
            ):
                await self.node.filters(
                    guild_id=self.channel.guild.id,
                    equalizer=self.equalizer,
                    karaoke=self.karaoke,
                    timescale=self.timescale,
                    tremolo=self.tremolo,
                    vibrato=self.vibrato,
                    rotation=self.rotation,
                    distortion=self.distortion,
                    low_pass=self.low_pass,
                    channel_mix=self.channel_mix,
                    echo=self.echo,
                )

            if self.volume_filter.changed:
                await self.node.send(op="volume", guildId=self.guild_id, volume=self.volume)

        now_time = utcnow()
        self.player_manager.client.scheduler.add_job(
            self.auto_dc_task,
            trigger="interval",
            seconds=5,
            max_instances=1,
            id=f"{self.bot.user.id}-{self.guild.id}-auto_dc_task",
            replace_existing=True,
            coalesce=True,
            next_run_time=now_time + datetime.timedelta(seconds=3),
        )

        self.player_manager.client.scheduler.add_job(
            self.auto_empty_queue_task,
            trigger="interval",
            seconds=5,
            max_instances=1,
            id=f"{self.bot.user.id}-{self.guild.id}-auto_empty_queue_task",
            replace_existing=True,
            coalesce=True,
            next_run_time=now_time + datetime.timedelta(seconds=2),
        )
        self.player_manager.client.scheduler.add_job(
            self.auto_pause_task,
            trigger="interval",
            seconds=5,
            max_instances=1,
            id=f"{self.bot.user.id}-{self.guild.id}-auto_pause_task",
            replace_existing=True,
            coalesce=True,
            next_run_time=now_time + datetime.timedelta(seconds=1),
        )
        self.player_manager.client.scheduler.add_job(
            self.auto_resume_task,
            trigger="interval",
            seconds=5,
            max_instances=1,
            id=f"{self.bot.user.id}-{self.guild.id}-auto_resume_task",
            replace_existing=True,
            coalesce=True,
            next_run_time=now_time + datetime.timedelta(seconds=4),
        )

        self.player_manager.client.scheduler.add_job(
            self.auto_save_task,
            trigger="interval",
            seconds=10,
            max_instances=1,
            id=f"{self.bot.user.id}-{self.guild.id}-auto_save_task",
            replace_existing=True,
            coalesce=True,
            next_run_time=now_time + datetime.timedelta(seconds=10),
        )
        self.ready.set()

    @property
    def channel(self) -> discord.channel.VocalGuildChannel:
        return self._channel

    @channel.setter
    def channel(self, value: discord.channel.VocalGuildChannel) -> None:
        if isinstance(value, (discord.VoiceChannel, discord.StageChannel)):
            self._channel = value
            self._region = value.rtc_region or "unknown_pylav"
            self._coordinates = REGION_TO_COUNTRY_COORDINATE_MAPPING.get(self._region, (0, 0))

    @property
    def coordinates(self) -> tuple[int, int]:
        return self._coordinates

    @property
    def ping(self) -> int:
        return self._ping

    @property
    def region(self) -> str | None:
        return self._region

    @property
    def config(self) -> PlayerModel:
        return self._config

    @property
    def lavalink(self) -> Client:
        return self._lavalink

    @property
    def pylav(self) -> Client:
        return self._lavalink

    @property
    def radio(self) -> RadioBrowser:
        return self.lavalink.radio_browser

    def vote_node_down(self) -> int:
        return -1 if (self.node is None or not self.is_playing) else self.node.down_vote(self)

    def voted(self) -> bool:
        return self.node.voted(self)

    def unvote_node_down(self) -> int:
        return -1 if (self.node is None or not self.is_playing) else not self.node.down_unvote(self)

    async def text_channel(self) -> discord.abc.MessageableChannel:
        return self.guild.get_channel_or_thread(await self.config.fetch_text_channel_id())

    async def set_text_channel(self, value: discord.abc.MessageableChannel) -> None:
        await self.config.update_text_channel_id(text_channel_id=value.id if value else 0)

    async def notify_channel(self) -> discord.abc.MessageableChannel:
        return self.guild.get_channel_or_thread(await self.config.fetch_notify_channel_id())

    async def set_notify_channel(self, value: discord.abc.MessageableChannel) -> None:
        await self.config.update_notify_channel_id(notify_channel_id=value.id if value else 0)

    async def forced_vc(self) -> discord.abc.MessageableChannel:
        return self.guild.get_channel_or_thread(await self.config.fetch_forced_channel_id())

    async def set_forced_vc(self, value: discord.abc.MessageableChannel) -> None:
        await self.config.update_forced_channel_id(forced_channel_id=value.id)

    async def self_deaf(self) -> bool | None:
        return (
            await self.player_manager.client.player_config_manager.get_self_deaf(self.guild.id)
            if self.player_manager
            else None
        )

    async def is_repeating(self) -> bool:
        """Whether the player is repeating tracks"""
        if await self.config.fetch_repeat_queue() is True:
            return True
        return await self.config.fetch_repeat_current()

    async def autoplay_enabled(self) -> bool:
        """Whether autoplay is enabled"""
        return bool(
            await self.player_manager.client.player_config_manager.get_auto_play(self.guild.id) is True
            and await self.get_auto_playlist() is not None
        )

    @property
    def volume(self) -> int:
        """
        The current volume.
        """
        return self._volume.get_int_value()

    @property
    def volume_filter(self) -> Volume:
        """The currently applied Volume filter"""
        return self._volume

    @property
    def equalizer(self) -> Equalizer:
        """The currently applied Equalizer filter"""
        return self._equalizer

    @property
    def karaoke(self) -> Karaoke:
        """The currently applied Karaoke filter"""
        return self._karaoke

    @property
    def timescale(self) -> Timescale:
        """The currently applied Timescale filter"""
        return self._timescale

    @property
    def tremolo(self) -> Tremolo:
        """The currently applied Tremolo filter"""
        return self._tremolo

    @property
    def vibrato(self) -> Vibrato:
        """The currently applied Vibrato filter"""
        return self._vibrato

    @property
    def rotation(self) -> Rotation:
        """The currently applied Rotation filter"""
        return self._rotation

    @property
    def distortion(self) -> Distortion:
        """The currently applied Distortion filter"""
        return self._distortion

    @property
    def echo(self) -> Echo:
        """The currently applied Echo filter"""
        return self._echo

    @property
    def low_pass(self) -> LowPass:
        """The currently applied Low Pass filter"""
        return self._low_pass

    @property
    def channel_mix(self) -> ChannelMix:
        """The currently applied Channel Mix filter"""
        return self._channel_mix

    @property
    def has_effects(self):
        return self._effect_enabled

    @property
    def guild(self) -> discord.Guild:
        return self.channel.guild

    @property
    def is_playing(self) -> bool:
        """Returns the player's track state"""
        return self.is_connected and self.current is not None

    @property
    def is_connected(self) -> bool:
        """Returns whether the player is connected to a voice-channel or not"""
        return self.channel_id is not None

    @property
    def is_empty(self) -> bool:
        """Returns whether the player is empty or not"""
        return sum(not i.bot for i in self.channel.members) == 0

    @property
    def position(self) -> float:
        """Returns the position in the track, adjusted for Lavalink's 5-second stats' interval"""
        if not self.is_playing:
            return 0

        if self.paused:
            return min(self._last_position, self.current.duration)

        difference = time.time() * 1000 - self._last_update
        return min(self._last_position + difference, self.current.duration)

    async def auto_pause_task(self):
        with contextlib.suppress(
            asyncio.exceptions.CancelledError,
        ):
            if not self.ready.is_set():
                return
            if not self.is_connected:
                LOGGER.trace(
                    "Auto Pause task for %s fired while player is not connected to a voice channel - discarding",
                    self,
                )
                return
            if (
                (not self.paused)
                and self.is_empty
                and (
                    feature := await self.player_manager.client.player_config_manager.get_alone_pause(
                        guild_id=self.guild.id
                    )
                ).enabled
            ):
                if not self._last_alone_paused_check:
                    LOGGER.verbose(
                        "Auto Pause task for %s - Player is alone - starting countdown",
                        self,
                    )
                    self._last_alone_paused_check = time.time()
                if (self._last_alone_paused_check + feature.time) <= time.time():
                    LOGGER.info(
                        "Auto Pause task for %s - Player in an empty channel for longer than %s seconds - Pausing",
                        self,
                        feature.time,
                    )
                    await self.set_pause(pause=True, requester=self.guild.me)
                    self._was_alone_paused = True
                    self._last_alone_paused_check = 0
            else:
                self._last_alone_paused_check = 0

    async def auto_resume_task(self):
        with contextlib.suppress(
            asyncio.exceptions.CancelledError,
        ):
            if not self.ready.is_set():
                return
            if not self._was_alone_paused:
                LOGGER.trace(
                    "Auto Resume task for %s fired while player is auto paused - discarding",
                    self,
                )
                return
            if (
                self.paused
                and not self.is_empty
                and (
                    feature := await self.player_manager.client.player_config_manager.get_alone_pause(
                        guild_id=self.guild.id
                    )
                ).enabled
            ):
                LOGGER.info(
                    "Auto Resume task for %s - Player in an non-empty channel - Resuming",
                    self,
                    feature.time,
                )
                await self.set_pause(pause=False, requester=self.guild.me)
                self._was_alone_paused = False

    async def auto_dc_task(self):
        with contextlib.suppress(
            asyncio.exceptions.CancelledError,
        ):
            if not self.ready.is_set():
                return
            if not self.is_connected:
                LOGGER.trace(
                    "Auto Disconnect task for %s fired while player is not connected to a voice channel - discarding",
                    self,
                )
                return
            if (
                self.is_empty
                and (
                    feature := await self.player_manager.client.player_config_manager.get_alone_dc(
                        guild_id=self.guild.id
                    )
                ).enabled
            ):
                if not self._last_alone_dc_check:
                    LOGGER.verbose(
                        "Auto Disconnect task for %s - Player is alone - starting countdown",
                        self,
                    )
                    self._last_alone_dc_check = time.time()
                if (self._last_alone_dc_check + feature.time) <= time.time():
                    LOGGER.info(
                        "Auto Disconnect task for %s - Player in an empty channel for longer than %s seconds "
                        "- Disconnecting",
                        self,
                        feature.time,
                    )
                    await self.disconnect(requester=self.guild.me)
                    self._last_alone_dc_check = 0
            else:
                self._last_alone_dc_check = 0

    async def auto_empty_queue_task(self):
        with contextlib.suppress(
            asyncio.exceptions.CancelledError,
        ):
            if not self.ready.is_set():
                return
            if not self.is_connected:
                LOGGER.trace(
                    "Auto Empty Queue task for %s fired while player is not connected to a voice channel - discarding",
                    self,
                )
                return
            if self.current:
                LOGGER.trace("Auto Empty Queue task for %s - Current track is not empty - discarding", self)
                return
            if (
                self.queue.empty()
                and (
                    feature := await self.player_manager.client.player_config_manager.get_empty_queue_dc(
                        guild_id=self.guild.id
                    )
                ).enabled
            ):
                if not self._last_empty_queue_check:
                    LOGGER.verbose(
                        "Auto Empty Queue task for %s - Queue is empty - starting countdown",
                        self,
                    )
                    self._last_empty_queue_check = time.time()
                if (self._last_empty_queue_check + feature.time) <= time.time():
                    LOGGER.info(
                        "Auto Empty Queue task for %s - Queue is empty for longer than %s seconds "
                        "- Stopping and disconnecting",
                        self,
                        feature.time,
                    )
                    await self.stop(requester=self.guild.me)
                    await self.disconnect(requester=self.guild.me)
                    self._last_empty_queue_check = 0
            else:
                self._last_empty_queue_check = 0

    async def auto_save_task(self):
        with contextlib.suppress(
            asyncio.exceptions.CancelledError,
        ):
            if not self.is_connected:
                LOGGER.trace(
                    "Auto save task for %s fired while player is not connected to a voice channel - discarding",
                    self,
                )
                return
            if self.stopped:
                LOGGER.trace(
                    "Auto save task for %s fired while player that has been stopped - discarding",
                    self,
                )
                return
            LOGGER.trace("Auto save task for %s - Saving the player at %s", self, utcnow())
            await self.save()

    async def change_to_best_node(self, feature: str = None, ops: bool = True) -> Node | None:
        """
        Returns the best node to play the current track.
        Returns
        -------
        :class:`Node`
        """
        if feature is None and self.current:
            feature = await self.current.requires_capability()
        node = await self.node.node_manager.find_best_node(
            region=self.region, feature=feature, coordinates=self.coordinates
        )
        if not node:
            LOGGER.warning("No node with %s functionality available - Waiting for one to become available!", feature)
            node = await self.node.node_manager.find_best_node(
                region=self.region, feature=feature, coordinates=self.coordinates, wait=True
            )

        if feature and not node:
            LOGGER.warning("No node with %s functionality available after one temporarily became available!", feature)
            raise NoNodeWithRequestFunctionalityAvailable(f"No node with {feature} functionality available", feature)
        if node != self.node or not ops:
            await self.change_node(node, ops=ops)
            return node

    async def change_to_best_node_diff_region(self, feature: str = None, ops: bool = True) -> Node | None:
        """
        Returns the best node to play the current track in a different region.
        Returns
        -------
        :class:`Node`
        """
        if feature is None and self.current:
            feature = await self.current.requires_capability()
        node = await self.node.node_manager.find_best_node(
            not_region=self.region, feature=feature, coordinates=self.coordinates
        )
        if not node:
            LOGGER.warning("No node with %s functionality available - Waiting for one to become available!", feature)
            node = await self.node.node_manager.find_best_node(
                region=self.region, feature=feature, coordinates=self.coordinates, wait=True
            )

        if feature and not node:
            LOGGER.warning("No node with %s functionality available after one temporarily became available!", feature)
            raise NoNodeWithRequestFunctionalityAvailable(f"No node with {feature} functionality available", feature)

        if node != self.node or not ops:
            await self.change_node(node, ops=ops)
            return node

    def store(
        self,
        key: str,
        value: Any,
    ) -> None:
        """
        Stores a value in the player's memory storage.
        Parameters
        ----------
        value: Any
            The value to store.
        key: str
            The key to store the value under.
        """
        self._user_data[key] = value

    def fetch(self, key: object, default: Any = None) -> Any:
        """
        Retrieves the related value from the stored user data.
        Parameters
        ----------
        key: :class:`object`
            The key to fetch.
        default: Optional[:class:`any`]
            The object that should be returned if the key doesn't exist. Defaults to `None`.
        Returns
        -------
        :class:`any`
        """
        return self._user_data.get(key, default)

    def delete(self, key: object) -> None:
        """
        Removes an item from the stored user data.
        Parameters
        ----------
        key: :class:`object`
            The key to delete.
        """
        with contextlib.suppress(KeyError):
            del self._user_data[key]

    async def on_voice_server_update(self, data: dict) -> None:
        self._voice_state.update({"event": data})
        if "endpoint" in data:
            if match := ENDPONT_REGEX.match(data["endpoint"]):
                self._region = match.group("region").replace("-", "_")
                self._coordinates = REGION_TO_COUNTRY_COORDINATE_MAPPING.get(self._region, (0, 0))
            await self._dispatch_voice_update()

    async def on_voice_state_update(self, data: dict) -> None:
        """|coro|

        An abstract method that is called when the client's voice state
        has changed. This corresponds to ``VOICE_STATE_UPDATE``.

        Parameters
        ------------
        data: :class:`dict`
            The raw :ddocs:`voice state payload <resources/voice#voice-state-object>`.
        """
        self._voice_state.update({"sessionId": data["session_id"]})
        self.channel_id = data["channel_id"]
        if not self.channel_id:  # We're disconnecting
            self._voice_state.clear()
            return
        self.channel = self.guild.get_channel(int(self.channel_id))
        await self._dispatch_voice_update()

    async def _dispatch_voice_update(self) -> None:
        if {"sessionId", "event"} == self._voice_state.keys():
            await self.node.send(op="voiceUpdate", guildId=self.guild_id, **self._voice_state)

    async def _query_to_track(
        self,
        requester: int,
        track: Track | dict | str | None,
        query: Query = None,
    ) -> Track:
        if not isinstance(track, Track):
            track = Track(node=self.node, data=track, query=query, requester=requester)
        else:
            track._requester = requester
        return track

    async def add(
        self,
        requester: int,
        track: Track | dict | str | None,
        index: int = None,
        query: Query = None,
    ) -> None:
        """
        Adds a track to the queue.

        Parameters
        ----------
        requester: :class:`int`
            The ID of the user who requested the track.
        track: Union[:class:`Track`, :class:`dict`]
            The track to add. Accepts either an Track or
            a dict representing a track returned from Lavalink.
        index: Optional[:class:`int`]
            The index at which to add the track.
            If index is left unspecified, the default behaviour is to append the track. Defaults to `None`.
        query: Optional[:class:`Query`]
            The query that was used to search for the track.

        Returns
        -------
        :class:`None`
        """

        at = await self._query_to_track(requester, track, query)
        self.queue.put_nowait([at], index=index)
        if index is None and (
            await self.player_manager.client.player_config_manager.get_auto_shuffle(self.guild.id) is True
        ):
            await self.maybe_shuffle_queue(requester=requester)
        self.next_track = None if self.queue.empty() else self.queue.raw_queue.popleft()
        self.node.dispatch_event(TracksRequestedEvent(self, self.guild.get_member(requester), [at]))

    async def bulk_add(
        self,
        tracks_and_queries: list[Track | dict | str | list[tuple[Track | dict | str, Query]]],
        requester: int,
        index: int = None,
    ) -> None:
        """
        Adds multiple tracks to the queue.
        Parameters
        ----------
        tracks_and_queries: list[Track | dict | str | list[tuple[Track | dict | str, Query]]]
            A list of tuples containing the track and query.
        requester: :class:`int`
            The ID of the user who requested the tracks.
        index: Optional[:class:`int`]
            The index at which to add the tracks.
        """
        output = []
        is_list = isinstance(tracks_and_queries[0], (list, tuple))
        async for entry in AsyncIter(tracks_and_queries):
            track, query = entry if is_list else (entry, None)
            track = await self._query_to_track(requester, track, query)
            output.append(track)
        self.queue.put_nowait(output, index=index)
        if index is None and (
            await self.player_manager.client.player_config_manager.get_auto_shuffle(self.guild.id) is True
        ):
            await self.maybe_shuffle_queue(requester=requester)
        self.next_track = None if self.queue.empty() else self.queue.raw_queue.popleft()
        self.node.dispatch_event(TracksRequestedEvent(self, self.guild.get_member(requester), output))

    async def previous(self, requester: discord.Member, bypass_cache: bool = False) -> None:
        if self.history.empty():
            raise TrackNotFound(_("There are no tracks currently in the player history"))
        self.stopped = False
        track = await self.history.get()
        if track.is_partial:
            await track.search(self, bypass_cache=bypass_cache)
        if self.current:
            self.history.put_nowait([self.current])
            self.last_track = self.current

        if await track.query() and not self.node.has_source(await track.requires_capability()):
            self.current = None
            await self.change_to_best_node(await track.requires_capability())

        self.current = track
        options = {"noReplace": False}
        if track.skip_segments and self.node.supports_sponsorblock:
            options["skipSegments"] = track.skip_segments
        await self.node.send(op="play", guildId=self.guild_id, track=track.track, **options)
        self.node.dispatch_event(TrackPreviousRequestedEvent(self, requester, track))

    async def quick_play(
        self,
        requester: discord.Member,
        track: Track | dict | str | None,
        query: Query,
        no_replace: bool = False,
        skip_segments: list[str] | str = None,
        bypass_cache: bool = False,
    ) -> None:
        skip_segments = self._process_skip_segments(skip_segments)
        track = Track(node=self.node, data=track, query=query, skip_segments=skip_segments, requester=requester.id)
        self.next_track = None
        self.last_track = None
        self.stopped = False
        if self.current:
            self.current.timestamp = self.position
            self.queue.put_nowait([self.current], 0)
            self.next_track = self.current
            self.last_track = self.current

        if await track.query() and not self.node.has_source(await track.requires_capability()):
            self.current = None
            await self.change_to_best_node(await track.requires_capability())

        if track.is_partial:
            try:
                await track.search(self, bypass_cache=bypass_cache)
            except TrackNotFound as exc:
                if not track:
                    raise TrackNotFound from exc
                event = TrackExceptionEvent(self, track, exc, self.node)
                self.node.dispatch_event(event)
                await self._handle_event(event)
                return
        self.current = track
        if self.next_track is None and not self.queue.empty():
            self.next_track = self.queue.raw_queue.popleft()
        options = {"noReplace": no_replace}
        if track.skip_segments and self.node.supports_sponsorblock:
            options["skipSegments"] = track.skip_segments
        await self.node.send(op="play", guildId=self.guild_id, track=track.track, **options)
        self.node.dispatch_event(QuickPlayEvent(self, requester, track))

    def next(self, requester: discord.Member = None, node: Node = None) -> Coroutine[Any, Any, None]:
        return self.play(None, None, requester or self.bot.user, node=node)  # type: ignore

    async def play(
        self,
        track: Track | dict | str,
        query: Query,
        requester: discord.Member,
        start_time: int = 0,
        end_time: int = 0,
        no_replace: bool = False,
        skip_segments: list[str] | str = None,
        bypass_cache: bool = False,
        node: Node = None,
    ) -> None:
        """Plays the given track.

        Parameters
        ----------
        track: Optional[Union[:class:`Track`, :class:`dict`]]
            The track to play. If left unspecified, this will default
            to the first track in the queue. Defaults to `None` so plays the next
            song in queue. Accepts either an Track or a dict representing a track
            returned from Lavalink.
        start_time: Optional[:class:`int`]
            Setting that determines the number of milliseconds to offset the track by.
            If left unspecified, it will start the track at its beginning. Defaults to `0`,
            which is the normal start time.
        end_time: Optional[:class:`int`]
            Settings that determines the number of milliseconds the track will stop playing.
            By default, track plays until it ends as per encoded data. Defaults to `0`, which is
            the normal end time.
        no_replace: Optional[:class:`bool`]
            If set to true, operation will be ignored if a track is already playing or paused.
            Defaults to `False`
        query: Optional[:class:`Query`]
            The query that was used to search for the track.
        skip_segments: Optional[:class:`list`]
            A list of segments to skip.
        requester: :class:`discord.Member`
            The member that requested the track.
        bypass_cache: Optional[:class:`bool`]
            If set to true, the track will not be looked up in the cache. Defaults to `False`.
        node: Optional[:class:`Node`]
            The node to use. Defaults the best available node with the needed feature.
        """
        # sourcery no-metrics
        options = {}
        skip_segments = self._process_skip_segments(skip_segments)
        self._last_update = 0
        self._last_position = 0
        self.position_timestamp = 0
        self.paused = False
        self.stopped = False
        auto_play = False
        self.next_track = None
        self.last_track = None
        if track is not None and isinstance(track, (Track, dict, str, type(None))):
            track = Track(node=self.node, data=track, query=query, skip_segments=skip_segments, requester=requester.id)
        if self.current:
            if await self.config.fetch_repeat_current():
                await self.add(self.current.requester_id, self.current)
            elif await self.config.fetch_repeat_queue():
                await self.add(self.current.requester_id, self.current, index=-1)
        if self.current:
            self.current.timestamp = 0
            self.history.put_nowait([self.current])
            self.last_track = self.current
        self.current = None
        if not track:
            if self.queue.empty():
                if await self.autoplay_enabled() and (
                    available_tracks := await (await self.get_auto_playlist()).fetch_tracks()
                ):
                    if tracks_not_in_history := list(set(available_tracks) - set(self.history.raw_b64s)):
                        track = Track(
                            node=self.node,
                            data=(b64 := random.choice(tracks_not_in_history)),
                            query=await Query.from_base64(b64),
                            skip_segments=skip_segments,
                            requester=self.client.user.id,
                        )
                    else:
                        track = Track(
                            node=self.node,
                            data=(b64 := random.choice(available_tracks)),
                            query=await Query.from_base64(b64),
                            skip_segments=skip_segments,
                            requester=self.client.user.id,
                        )
                    auto_play = True
                    self.next_track = None
                else:
                    await self.stop(
                        requester=self.guild.get_member(self.node.node_manager.client.bot.user.id)
                    )  # Also sets current to None.
                    self.history.clear()
                    self.last_track = None
                    self.node.dispatch_event(QueueEndEvent(self))
                    return
            else:
                track = await self.queue.get()

        if await track.query() is None:
            track._query = await Query.from_base64(track.track)
        if node:
            if self.node != node:
                await self.change_node(node)
        else:
            try:
                await self.change_to_best_node(feature=await track.requires_capability())
            except NoNodeWithRequestFunctionalityAvailable as exc:
                event = TrackExceptionEvent(self, track, exc, self.node)
                self.node.dispatch_event(event)
                await self._handle_event(event)
                return
        track._node = self.node
        if track.is_partial:
            try:
                await track.search(self, bypass_cache=bypass_cache)
            except TrackNotFound as exc:
                if not track:
                    raise TrackNotFound from exc
                event = TrackExceptionEvent(self, track, exc, self.node)
                self.node.dispatch_event(event)
                await self._handle_event(event)
                return
        if self.node.supports_sponsorblock:
            options["skipSegments"] = skip_segments or track.skip_segments
        if start_time or track.timestamp:
            if not isinstance(start_time, int) or not 0 <= start_time <= track.duration:
                raise ValueError(
                    "start_time must be an int with a value equal to, "
                    "or greater than 0, and less than the track duration"
                )
            options["startTime"] = start_time or track.timestamp

        if end_time is not None:
            if not isinstance(end_time, int) or not 0 <= end_time <= track.duration:
                raise ValueError(
                    "end_time must be an int with a value equal to, or greater than 0, and less than the track duration"
                )
            options["endTime"] = end_time

        if no_replace is None:
            no_replace = False
        if not isinstance(no_replace, bool):
            raise TypeError("no_replace must be a bool")
        options["noReplace"] = no_replace

        self.current = track
        self.next_track = None if self.queue.empty() else self.queue.raw_queue.popleft()
        await self.node.send(op="play", guildId=self.guild_id, track=track.track, **options)
        if auto_play:
            self.node.dispatch_event(TrackAutoPlayEvent(player=self, track=track))

    async def resume(self, requester: discord.Member = None):
        options = {}
        self._last_update = 0
        self.stopped = False
        self._last_position = 0
        if self.node.supports_sponsorblock:
            options["skipSegments"] = self.current.skip_segments if self.current else []
        options["startTime"] = self.current.last_known_position if self.current else self.position
        options["noReplace"] = False
        await self.node.send(op="play", guildId=self.guild_id, track=self.current.track, **options)
        self.node.dispatch_event(PlayerResumedEvent(player=self, requester=requester or self.client.user.id))

    async def skip(self, requester: discord.Member) -> None:
        """Plays the next track in the queue, if any"""
        previous_track = self.current
        previous_position = self.position
        op = self.next(requester=requester)
        await op
        if previous_track:
            self.node.dispatch_event(TrackSkippedEvent(self, requester, previous_track, previous_position))

    async def set_repeat(
        self, op_type: Literal["current", "queue", "disable"], repeat: bool, requester: discord.Member
    ) -> None:
        """
        Sets the player's repeat state.
        Parameters
        ----------
        repeat: :class:`bool`
            Whether to repeat the player or not.
        op_type: :class:`str`
            The type of repeat to set. Can be either ``"current"`` or ``"queue"`` or ``disable``.
        requester: :class:`discord.Member`
            The member who requested the repeat change.
        """
        current_after = current_before = await self.config.fetch_repeat_current()
        queue_after = queue_before = await self.config.fetch_repeat_queue()

        if op_type == "disable":
            await self.config.update_repeat_current(False)
            await self.config.update_repeat_queue(False)
            queue_after = False
            current_after = False
        elif op_type == "current":
            current_after = repeat
            await self.config.update_repeat_current(current_after)
            await self.config.update_repeat_queue(False)
        elif op_type == "queue":
            queue_after = repeat
            await self.config.update_repeat_current(False)
            await self.config.update_repeat_queue(queue_after)
        else:
            raise ValueError(f"op_type must be either 'current' or 'queue' or `disable` not `{op_type}`")
        self.node.dispatch_event(
            PlayerRepeatEvent(self, requester, op_type, queue_before, queue_after, current_before, current_after)
        )

    async def set_shuffle(self, shuffle: bool) -> None:
        """
        Sets the player's shuffle state.
        Parameters
        ----------
        shuffle: :class:`bool`
            Whether to shuffle the player or not.
        """
        if await self.player_manager.global_config.fetch_shuffle() is False:
            return
        await self.config.update_shuffle(shuffle)

    async def set_auto_shuffle(self, shuffle: bool) -> None:
        """
        Sets the player's auto shuffle state.
        Parameters
        ----------
        shuffle: :class:`bool`
            Whether to shuffle the player or not.
        """
        if await self.player_manager.global_config.fetch_auto_shuffle() is False:
            return
        await self.config.update_auto_shuffle(shuffle)

    async def set_pause(self, pause: bool, requester: discord.Member) -> None:
        """
        Sets the player's paused state.
        Parameters
        ----------
        pause: :class:`bool`
            Whether to pause the player or not.
        requester: :class:`discord.Member`
            The member who requested the pause.
        """
        await self.node.send(op="pause", guildId=self.guild_id, pause=pause)

        self.paused = pause
        self._was_alone_paused = False
        if self.paused:
            self.node.dispatch_event(PlayerPausedEvent(self, requester))
        else:
            self.node.dispatch_event(TrackResumedEvent(self, track=self.current, requester=requester))

    async def set_volume(self, vol: int | float | Volume, requester: discord.Member) -> None:
        """
        Sets the player's volume
        Note
        ----
        A limit of 1000 is imposed by Lavalink. (This function also inforces a globally and server set limit.)
        Parameters
        ----------
        vol: :class:`int`
            The new volume level.
        requester: :class:`discord.Member`
            The member who requested the volume change.
        """
        max_volume = await self.player_manager.client.player_config_manager.get_max_volume(self.guild.id)
        volume = await asyncstdlib.max([await asyncstdlib.min([vol, max_volume]), 0])
        if volume == self.volume:
            return
        await self.config.update_volume(volume)
        self._volume = Volume(volume)
        await self.node.send(op="volume", guildId=self.guild_id, volume=self.volume)
        self.node.dispatch_event(PlayerVolumeChangedEvent(self, requester, self.volume, volume))

    async def seek(self, position: float, requester: discord.Member, with_filter: bool = False) -> None:
        """
        Seeks to a given position in the track.
        Parameters
        ----------
        position: :class:`int`
            The new position to seek to in milliseconds.
        with_filter: :class:`bool`
            Whether to apply the filter or not.
        requester: :class:`discord.Member`
            The member who requested the seek.
        """
        if self.current and self.current.is_seekable:
            if with_filter:
                position = self.position
            position = await asyncstdlib.max([await asyncstdlib.min([position, self.current.duration]), 0])
            self.node.dispatch_event(
                TrackSeekEvent(self, requester, self.current, before=self.position, after=position)
            )
            await self.node.send(op="seek", guildId=self.guild_id, position=position)
            self._last_update = time.time() * 1000
            self._last_position = position

    async def _handle_event(self, event) -> None:
        """
        Handles the given event as necessary.
        Parameters
        ----------
        event: :class:`Event`
            The event that will be handled.
        """
        if event.node.identifier != self.node.identifier:
            return
        if isinstance(event, TrackStuckEvent) or isinstance(event, TrackEndEvent) and event.reason == "FINISHED":
            self.last_track = self.current
            await self.next()
            self.next_track = None if self.queue.empty() else self.queue.raw_queue.popleft()
        elif isinstance(event, TrackExceptionEvent):
            self.last_track = self.current
            await self.next()
            self.next_track = None if self.queue.empty() else self.queue.raw_queue.popleft()

    async def _update_state(self, state: dict) -> None:
        """
        Updates the position of the player.
        Parameters
        ----------
        state: :class:`dict`
            The state that is given to update.
        """
        self._last_update = time.time() * 1000
        self._last_position = state.get("position", 0)
        self.position_timestamp = state.get("time", 0)
        self._ping = state.get("ping", 0)
        if self.current:
            self.current.last_known_position = self._last_position

        event = PlayerUpdateEvent(self, self._last_position, self.position_timestamp)
        self.node.dispatch_event(event)

    async def change_node(self, node: Node, ops: bool = True) -> None:
        """
        Changes the player's node
        Parameters
        ----------
        node: :class:`Node`
            The node the player is changed to.
        ops: :class:`bool`
            Whether to change apply the volume and filter ops on change.
        """
        if node == self.node and self.node.available and ops:
            return
        if self.node.available:
            await self.node.send(op="destroy", guildId=self.guild_id)
        old_node = self.node
        self.node = node
        if self._voice_state:
            await self._dispatch_voice_update()
        if self.current:
            options = {}
            if self.current.skip_segments and self.node.supports_sponsorblock:
                options["skipSegments"] = self.current.skip_segments
            await self.node.send(
                op="play", guildId=self.guild_id, track=self.current.track, startTime=self.position, **options
            )
            self._last_update = time.time() * 1000
            if self.paused:
                await self.node.send(op="pause", guildId=self.guild_id, pause=self.paused)
        if ops:
            if self.has_effects:
                await self.set_filters(
                    requester=self.guild.me,
                    equalizer=self.equalizer,
                    karaoke=self.karaoke,
                    timescale=self.timescale,
                    tremolo=self.tremolo,
                    vibrato=self.vibrato,
                    rotation=self.rotation,
                    distortion=self.distortion,
                    low_pass=self.low_pass,
                    channel_mix=self.channel_mix,
                    echo=self.echo,
                    reset_not_set=True,
                )

            if self.volume_filter.changed:
                await self.node.send(op="volume", guildId=self.guild_id, volume=self.volume)
        self.node.dispatch_event(NodeChangedEvent(self, old_node, node))

    async def connect(
        self,
        *,
        timeout: float = 2.0,
        reconnect: bool = False,
        self_mute: bool = False,
        self_deaf: bool = True,
        requester: discord.Member = None,
    ) -> None:
        """
        Connects the player to the voice channel.
        Parameters
        ----------
        timeout: :class:`float`
            The timeout for the connection.
        reconnect: :class:`bool`
            Whether the player should reconnect if the connection is lost.
        self_mute: :class:`bool`
            Whether the player should be muted.
        self_deaf: :class:`bool`
            Whether the player should be deafened.
        requester: :class:`discord.Member`
            The member requesting the connection.
        """
        await self.guild.change_voice_state(
            channel=self.channel,
            self_mute=self_mute,
            self_deaf=deaf if (deaf := await self.self_deaf()) is True else self_deaf,
        )
        self._connected = True
        self.connected_at = utcnow()
        LOGGER.debug("[Player-%s] Connected to voice channel", self.channel.guild.id)

    async def disconnect(self, *, force: bool = False, requester: discord.Member | None) -> None:
        try:
            if not self.stopped:
                await self.save()
            await self.guild.change_voice_state(channel=None)
            self.node.dispatch_event(PlayerDisconnectedEvent(self, requester))
            LOGGER.debug("[Player-%s] Disconnected from voice channel", self.channel.guild.id)
        finally:
            self._connected = False
            self.queue.clear()
            self.history.clear()
            self.last_track = None
            self.next_track = None
            self.stopped = True
            self.current = None
            with contextlib.suppress(ValueError):
                await self.player_manager.remove(self.channel.guild.id)
            await self.node.send(op="destroy", guildId=self.guild_id)
            self.player_manager.client.scheduler.remove_job(job_id=f"{self.bot.user.id}-{self.guild.id}-auto_dc_task")
            self.player_manager.client.scheduler.remove_job(
                job_id=f"{self.bot.user.id}-{self.guild.id}-auto_empty_queue_task"
            )
            self.player_manager.client.scheduler.remove_job(
                job_id=f"{self.bot.user.id}-{self.guild.id}-auto_pause_task"
            )
            self.player_manager.client.scheduler.remove_job(job_id=f"{self.bot.user.id}-{self.guild.id}-auto_save_task")
            self.cleanup()

    async def stop(self, requester: discord.Member) -> None:
        """Stops the player"""
        await self.node.send(op="stop", guildId=self.guild_id)
        self.node.dispatch_event(PlayerStoppedEvent(self, requester))
        self.current = None
        self.queue.clear()
        self.next_track = None
        self.stopped = True
        await self.player_manager.client.player_state_db_manager.delete_player(self.channel.guild.id)

    async def move_to(
        self,
        requester: discord.Member,
        channel: discord.channel.VocalGuildChannel,
        self_mute: bool = False,
        self_deaf: bool = True,
    ) -> discord.channel.VocalGuildChannel | None:
        """|coro|
        Moves the player to a different voice channel.
        Parameters
        -----------
        channel: :class:`discord.channel.VocalGuildChannel`
            The channel to move to. Must be a voice channel.
        self_mute: :class:`bool`
            Indicates if the player should be self-muted on move.
        self_deaf: :class:`bool`
            Indicates if the player should be self-deafened on move.
        requester: :class:`discord.Member`
            The member requesting to move the player.
        """
        if self.config and (vc := await self.forced_vc()) and channel.id != vc.id:
            channel = vc
            LOGGER.debug(
                "[Player-%s] Player has a forced VC enabled replacing channel arg with it", self.channel.guild.id
            )
        if channel == self.channel:
            return
        old_channel = self.channel
        LOGGER.debug(
            "[Player-%s] Moving from %s to voice channel: %s", self.channel.guild.id, self.channel.id, channel.id
        )
        self.channel = channel
        self_deaf = deaf if (deaf := await self.self_deaf()) is True else self_deaf
        await self.guild.change_voice_state(channel=self.channel, self_mute=self_mute, self_deaf=self_deaf)
        self._connected = True
        self.node.dispatch_event(PlayerMovedEvent(self, requester, old_channel, self.channel))
        return channel

    async def self_deafen(self, toggle: bool) -> None:
        """|coro|
        Deafens the player.
        Parameters
        -----------
        toggle: :class:`bool`
            Indicates if the player should be deafened.
        """
        await self.config.update_self_deaf(toggle)
        await self.guild.change_voice_state(self_deaf=toggle, channel=self.channel)

    async def set_volume_filter(self, requester: discord.Member, volume: Volume) -> None:
        """
        Sets the volume of Lavalink.
        Parameters
        ----------
        volume : Volume
            Volume to set
        requester : discord.Member
        """
        max_volume = await self.player_manager.client.player_config_manager.get_max_volume(self.guild.id)
        if volume.get_int_value() > max_volume:
            volume = Volume(max_volume)
        await self.set_filters(
            volume=volume,
            requester=requester,
        )

    async def set_equalizer(self, requester: discord.Member, equalizer: Equalizer, forced: bool = False) -> None:
        """
        Sets the Equalizer of Lavalink.
        Parameters
        ----------
        equalizer : Equalizer
            Equalizer to set
        forced : bool
            Whether to force the equalizer to be set resetting any other filters currently applied
        requester : discord.Member
            The member who requested the equalizer to be set
        """
        await self.set_filters(
            equalizer=equalizer,
            reset_not_set=forced,
            requester=requester,
        )

    async def set_karaoke(self, requester: discord.Member, karaoke: Karaoke, forced: bool = False) -> None:
        """
        Sets the Karaoke of Lavalink.
        Parameters
        ----------
        karaoke : Karaoke
            Karaoke to set
        forced : bool
            Whether to force the karaoke to be set resetting any other filters currently applied
        requester: discord.Member
            The member who requested the karaoke
        """
        await self.set_filters(
            karaoke=karaoke,
            reset_not_set=forced,
            requester=requester,
        )

    async def set_timescale(self, requester: discord.Member, timescale: Timescale, forced: bool = False) -> None:
        """
        Sets the Timescale of Lavalink.
        Parameters
        ----------
        timescale : Timescale
            Timescale to set
        forced : bool
            Whether to force the timescale to be set resetting any other filters currently applied
        requester: discord.Member
            The member who requested the timescale
        """
        await self.set_filters(
            timescale=timescale,
            reset_not_set=forced,
            requester=requester,
        )

    async def set_tremolo(self, requester: discord.Member, tremolo: Tremolo, forced: bool = False) -> None:
        """
        Sets the Tremolo of Lavalink.
        Parameters
        ----------
        tremolo : Tremolo
            Tremolo to set
        forced : bool
            Whether to force the tremolo to be set resetting any other filters currently applied
        requester: discord.Member
            The member who requested the tremolo
        """
        await self.set_filters(
            tremolo=tremolo,
            reset_not_set=forced,
            requester=requester,
        )

    async def set_vibrato(self, requester: discord.Member, vibrato: Vibrato, forced: bool = False) -> None:
        """
        Sets the Vibrato of Lavalink.
        Parameters
        ----------
        vibrato : Vibrato
            Vibrato to set
        forced : bool
            Whether to force the vibrato to be set resetting any other filters currently applied
        requester: discord.Member
            The member who requested the vibrato
        """
        await self.set_filters(
            vibrato=vibrato,
            reset_not_set=forced,
            requester=requester,
        )

    async def set_rotation(self, requester: discord.Member, rotation: Rotation, forced: bool = False) -> None:
        """
        Sets the Rotation of Lavalink.
        Parameters
        ----------
        rotation : Rotation
            Rotation to set
        forced : bool
            Whether to force the rotation to be set resetting any other filters currently applied
        requester: discord.Member
            The member who requested the rotation
        """
        await self.set_filters(
            rotation=rotation,
            reset_not_set=forced,
            requester=requester,
        )

    async def set_distortion(self, requester: discord.Member, distortion: Distortion, forced: bool = False) -> None:
        """
        Sets the Distortion of Lavalink.
        Parameters
        ----------
        distortion : Distortion
            Distortion to set
        forced : bool
            Whether to force the distortion to be set resetting any other filters currently applied
        requester: discord.Member
            The member who requested the distortion
        """
        await self.set_filters(
            distortion=distortion,
            reset_not_set=forced,
            requester=requester,
        )

    async def set_low_pass(self, requester: discord.Member, low_pass: LowPass, forced: bool = False) -> None:
        """
        Sets the LowPass of Lavalink.
        Parameters
        ----------
        low_pass : LowPass
            LowPass to set
        forced : bool
            Whether to force the low_pass to be set resetting any other filters currently applied
        requester : discord.Member
            Member who requested the filter change
        """
        await self.set_filters(
            low_pass=low_pass,
            reset_not_set=forced,
            requester=requester,
        )

    async def set_echo(self, requester: discord.Member, echo: Echo, forced: bool = False) -> None:
        """
        Sets the Echo of Lavalink.
        Parameters
        ----------
        echo : Echo
            Echo to set
        forced : bool
            Whether to force the low_pass to be set resetting any other filters currently applied
        requester : discord.Member
            Member who requested the filter change
        """
        await self.set_filters(
            echo=echo,
            reset_not_set=forced,
            requester=requester,
        )

    async def apply_nightcore(self, requester: discord.Member) -> None:
        """
        Applies the NightCore filter to the player.
        Parameters
        ----------
        requester : discord.Member
            Member who requested the filter change
        """
        await self.set_filters(
            requester=requester,
            low_pass=None,  # Timescale breaks if it applied with lowpass
            equalizer=Equalizer(
                levels=[
                    {"band": 0, "gain": -0.075},
                    {"band": 1, "gain": 0.125},
                    {"band": 2, "gain": 0.125},
                ],
                name="Nightcore",
            ),
            karaoke=self.karaoke if self.karaoke.changed else None,
            tremolo=self.tremolo if self.tremolo.changed else None,
            vibrato=self.vibrato if self.vibrato.changed else None,
            distortion=self.distortion if self.distortion.changed else None,
            timescale=Timescale(speed=1.17, pitch=1.2, rate=1),
            channel_mix=self.channel_mix if self.channel_mix.changed else None,
            echo=self.echo if self.echo.changed else None,
            reset_not_set=True,
        )

    async def remove_nightcore(self, requester: discord.Member) -> None:
        """
        Removes the NightCore filter from the player.
        Parameters
        ----------
        requester : discord.Member
            Member who requested the filter change
        """
        await self.set_filters(
            requester=requester,
            low_pass=None,  # Timescale breaks if it applied with lowpass
            equalizer=None,
            timescale=None,
            reset_not_set=True,
            karaoke=self.karaoke if self.karaoke.changed else None,
            tremolo=self.tremolo if self.tremolo.changed else None,
            vibrato=self.vibrato if self.vibrato.changed else None,
            distortion=self.distortion if self.distortion.changed else None,
            channel_mix=self.channel_mix if self.channel_mix.changed else None,
            echo=self.echo if self.echo.changed else None,
        )

    async def set_channel_mix(self, requester: discord.Member, channel_mix: ChannelMix, forced: bool = False) -> None:
        """
        Sets the ChannelMix of Lavalink.
        Parameters
        ----------
        channel_mix : ChannelMix
            ChannelMix to set
        forced : bool
            Whether to force the channel_mix to be set resetting any other filters currently applied
        requester : discord.Member
            The member who requested the channel_mix
        """
        await self.set_filters(
            channel_mix=channel_mix,
            reset_not_set=forced,
            requester=requester,
        )

    async def set_filters(
        self,
        *,
        requester: discord.Member,
        volume: Volume = None,
        equalizer: Equalizer = None,
        karaoke: Karaoke = None,
        timescale: Timescale = None,
        tremolo: Tremolo = None,
        vibrato: Vibrato = None,
        rotation: Rotation = None,
        distortion: Distortion = None,
        low_pass: LowPass = None,
        channel_mix: ChannelMix = None,
        echo: Echo = None,
        reset_not_set: bool = False,
    ):  # sourcery no-metrics
        """
        Sets the filters of Lavalink.
        Parameters
        ----------
        volume : Volume
            Volume to set
        equalizer : Equalizer
            Equalizer to set
        karaoke : Karaoke
            Karaoke to set
        timescale : Timescale
            Timescale to set
        tremolo : Tremolo
            Tremolo to set
        vibrato : Vibrato
            Vibrato to set
        rotation : Rotation
            Rotation to set
        distortion : Distortion
            Distortion to set
        low_pass : LowPass
            LowPass to set
        channel_mix : ChannelMix
            ChannelMix to set
        echo: Echo
            Echo to set
        reset_not_set : bool
            Whether to reset any filters that are not set
        requester : discord.Member
            Member who requested the filters to be set
        """
        changed = False
        if volume and volume.changed:
            self._volume = volume
            changed = True
        if equalizer and equalizer.changed:
            self._equalizer = equalizer
            changed = True
        if karaoke and karaoke.changed:
            self._karaoke = karaoke
            changed = True
        if timescale and timescale.changed:
            self._timescale = timescale
            changed = True
        if tremolo and tremolo.changed:
            self._tremolo = tremolo
            changed = True
        if vibrato and vibrato.changed:
            self._vibrato = vibrato
            changed = True
        if rotation and rotation.changed:
            self._rotation = rotation
            changed = True
        if distortion and distortion.changed:
            self._distortion = distortion
            changed = True
        if low_pass and low_pass.changed:
            self._low_pass = low_pass
            changed = True
        if channel_mix and channel_mix.changed:
            self._channel_mix = channel_mix
            changed = True
        if echo and echo.changed:
            self._echo = echo
            changed = True

        self._effect_enabled = changed
        if reset_not_set:
            kwargs = {
                "volume": volume or self.volume_filter,
                "equalizer": equalizer,
                "karaoke": karaoke,
                "timescale": timescale,
                "tremolo": tremolo,
                "vibrato": vibrato,
                "rotation": rotation,
                "distortion": distortion,
                "low_pass": low_pass,
                "channel_mix": channel_mix,
                "echo": echo,
            }
            if not (equalizer and equalizer.changed):
                self._equalizer = Equalizer.default()
            if not (karaoke and karaoke.changed):
                self._karaoke = Karaoke.default()
            if not (timescale and timescale.changed):
                self._timescale = Timescale.default()
            if not (tremolo and tremolo.changed):
                self._tremolo = Tremolo.default()
            if not (vibrato and vibrato.changed):
                self._vibrato = Vibrato.default()
            if not (rotation and rotation.changed):
                self._rotation = Rotation.default()
            if not (distortion and distortion.changed):
                self._distortion = Distortion.default()
            if not (low_pass and low_pass.changed):
                self._low_pass = LowPass.default()
            if not (channel_mix and channel_mix.changed):
                self._channel_mix = ChannelMix.default()
            if not (echo and echo.changed):
                self._echo = Echo.default()
        else:
            kwargs = {
                "volume": volume or (self.volume_filter if self.volume_filter.changed else None),
                "equalizer": equalizer or (self.equalizer if self.equalizer.changed else None),
                "karaoke": karaoke or (self.karaoke if self.karaoke.changed else None),
                "timescale": timescale or (self.timescale if self.timescale.changed else None),
                "tremolo": tremolo or (self.tremolo if self.tremolo.changed else None),
                "vibrato": vibrato or (self.vibrato if self.vibrato.changed else None),
                "rotation": rotation or (self.rotation if self.rotation.changed else None),
                "distortion": distortion or (self.distortion if self.distortion.changed else None),
                "low_pass": low_pass or (self.low_pass if self.low_pass.changed else None),
                "channel_mix": channel_mix or (self.channel_mix if self.channel_mix.changed else None),
                "echo": echo or (self.echo if self.echo.changed else None),
            }
        if not volume:
            kwargs.pop("volume", None)
        await self.node.filters(guild_id=self.channel.guild.id, **kwargs)
        await self.seek(self.position, with_filter=True, requester=requester)
        kwargs.pop("reset_not_set", None)
        kwargs.pop("requester", None)
        self.node.dispatch_event(FiltersAppliedEvent(player=self, requester=requester, node=self.node, **kwargs))

    def _process_skip_segments(self, skip_segments: list[str] | str | None):
        if skip_segments is not None and self.node.supports_sponsorblock:
            if isinstance(skip_segments, str) and skip_segments == "all":
                skip_segments = SegmentCategory.get_category_list_value()
            else:
                skip_segments = list(
                    filter(
                        lambda x: x in SegmentCategory.get_category_list_value(),
                        map(lambda x: x.lower(), skip_segments),
                    )
                )
        elif self.node.supports_sponsorblock:
            skip_segments = SegmentCategory.get_category_list_value()
        else:
            skip_segments = []
        return skip_segments

    def draw_time(self) -> str:
        paused = self.paused
        pos = self.position
        dur = getattr(self.current, "duration", pos)
        sections = 12
        loc_time = round((pos / dur if dur != 0 else pos) * sections)
        bar = "\N{BOX DRAWINGS HEAVY HORIZONTAL}"
        seek = "\N{RADIO BUTTON}"
        msg = (
            "\N{DOUBLE VERTICAL BAR}\N{VARIATION SELECTOR-16}"
            if paused
            else "\N{BLACK RIGHT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}"
        )

        for i in range(sections):
            msg += seek if i == loc_time else bar
        return msg

    async def get_currently_playing_message(
        self, embed: bool = True, messageable: Messageable | InteractionT = None
    ) -> discord.Embed | str:  # sourcery skip: use-fstring-for-formatting
        if not embed:
            return ""
        queue_list = ""
        arrow = self.draw_time()
        pos = format_time(self.position)
        current = self.current
        dur = _("LIVE") if current.stream else format_time(current.duration)
        current_track_description = await current.get_track_display_name(with_url=True)
        next_track_description = (
            await self.next_track.get_track_display_name(with_url=True) if self.next_track else None
        )
        previous_track_description = (
            await self.last_track.get_track_display_name(with_url=True) if self.last_track else None
        )
        if current.stream:
            queue_list += "**{}:**\n".format(discord.utils.escape_markdown(_("Currently livestreaming")))
        else:
            queue_list += _("Playing: ")
        queue_list += f"{current_track_description}\n"
        queue_list += "{translation}: **{current}**".format(
            current=current.requester.mention, translation=discord.utils.escape_markdown(_("Requester"))
        )
        queue_list += f"\n\n{arrow}`{pos}`/`{dur}`\n\n"
        page = await self.node.node_manager.client.construct_embed(
            title="{translation} __{guild}__".format(
                guild=self.guild.name, translation=discord.utils.escape_markdown(_("Now Playing in"))
            ),
            description=queue_list,
            messageable=messageable,
        )
        if url := await current.thumbnail():
            page.set_thumbnail(url=url)

        if previous_track_description:
            val = f"{previous_track_description}\n"
            val += "{translation}: `{duration}`\n".format(
                duration=_("LIVE") if self.last_track.stream else format_time(self.last_track.duration),
                translation=discord.utils.escape_markdown(_("Duration")),
            )
            if rq := self.last_track.requester:
                val += "{translation}: **{rq}**\n\n".format(
                    rq=rq.mention, translation=discord.utils.escape_markdown(_("Requester"))
                )
            page.add_field(name=_("Previous Track"), value=val)
        if next_track_description:
            val = f"{next_track_description}\n"
            val += "{translation}: `{duration}`\n".format(
                duration=_("LIVE") if self.next_track.stream else format_time(self.next_track.duration),
                translation=discord.utils.escape_markdown(_("Duration")),
            )
            if rq := self.next_track.requester:
                val += "{translation}: **{rq}**\n\n".format(
                    rq=rq.mention, translation=discord.utils.escape_markdown(_("Requester"))
                )
            page.add_field(name=_("Next Track"), value=val)

        queue_dur = await self.queue_duration()
        queue_total_duration = get_time_string(queue_dur // 1000)
        text = _("{track_count} tracks, {queue_total_duration} remaining\n").format(
            track_count=self.queue.qsize(), queue_total_duration=queue_total_duration
        )
        if not await self.is_repeating():
            repeat_emoji = "\N{CROSS MARK}"
        elif await self.config.fetch_repeat_queue():
            repeat_emoji = "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}"
        else:
            repeat_emoji = "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS WITH CIRCLED ONE OVERLAY}"

        autoplay_emoji = "\N{WHITE HEAVY CHECK MARK}" if await self.autoplay_enabled() else "\N{CROSS MARK}"

        text += _("{translation}: {repeat_emoji}").format(repeat_emoji=repeat_emoji, translation=_("Repeating"))
        text += _("{space}{translation}: {autoplay_emoji}").format(
            space=(" | " if text else ""), autoplay_emoji=autoplay_emoji, translation=_("Auto Play")
        )
        text += _("{space}{translation}: {volume}%").format(
            space=(" | " if text else ""), volume=self.volume, translation=_("Volume")
        )
        page.set_footer(text=text)
        return page

    async def get_queue_page(
        self,
        page_index: int,
        per_page: int,
        total_pages: int,
        embed: bool = True,
        messageable: Messageable | InteractionT = None,
        history: bool = False,
    ) -> discord.Embed | str:
        if not embed:
            return ""
        queue = self.history if history else self.queue
        queue_list = ""
        start_index = page_index * per_page
        end_index = start_index + per_page
        tracks = await asyncstdlib.list(asyncstdlib.islice(queue.raw_queue, start_index, end_index))
        arrow = self.draw_time()
        pos = format_time(self.position)
        current = self.current
        dur = "LIVE" if current.stream else format_time(current.duration)
        current_track_description = await current.get_track_display_name(with_url=True)
        if current.stream:
            queue_list += "**{translation}:**\n".format(
                translation=discord.utils.escape_markdown(_("Currently livestreaming"))
            )
        else:
            queue_list += "{translation}: ".format(translation=discord.utils.escape_markdown(_("Playing")))
        queue_list += f"{current_track_description}\n"
        queue_list += "{translation}: **{current}**".format(
            current=current.requester.mention, translation=discord.utils.escape_markdown(_("Requester"))
        )
        queue_list += f"\n\n{arrow}`{pos}`/`{dur}`\n\n"
        if (
            len(tracks)
            and not history
            and (await self.player_manager.client.player_config_manager.get_auto_shuffle(self.guild.id)) is True
        ):
            queue_list += "__{translation}__\n\n".format(
                translation=discord.utils.escape_markdown(
                    _("Queue order is may not be accurate due to auto-shuffle being enabled")
                )
            )
        if tracks:
            padding = len(str(start_index + len(tracks)))
            async for track_idx, track in AsyncIter(tracks).enumerate(start=start_index + 1):
                track_description = await track.get_track_display_name(max_length=50, with_url=True)
                diff = padding - len(str(track_idx))
                queue_list += f"`{track_idx}.{' '*diff}` {track_description}"
                if history and track.requester:
                    queue_list += f" - **{track.requester.mention}**"
                queue_list += "\n"
        page = await self.node.node_manager.client.construct_embed(
            title="{translation} __{guild}__".format(
                guild=self.guild.name,
                translation=discord.utils.escape_markdown(_("Recently Played for") if history else _("Queue for")),
            ),
            description=queue_list,
            messageable=messageable,
        )
        if url := await current.thumbnail():
            page.set_thumbnail(url=url)
        queue_dur = await self.queue_duration(history=history)
        queue_total_duration = get_time_string(queue_dur // 1000)
        text = _(
            "Page {current_page}/{total_pages} | {track_number} tracks, {queue_total_duration} remaining\n"
        ).format(
            current_page=page_index + 1,
            total_pages=total_pages,
            track_number=queue.qsize(),
            queue_total_duration=queue_total_duration,
        )
        if not await self.is_repeating():
            repeat_emoji = "\N{CROSS MARK}"
        elif await self.config.fetch_repeat_queue():
            repeat_emoji = "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}"
        else:
            repeat_emoji = "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS WITH CIRCLED ONE OVERLAY}"

        autoplay_emoji = "\N{WHITE HEAVY CHECK MARK}" if await self.autoplay_enabled() else "\N{CROSS MARK}"

        text += _("{translation}: {repeat_emoji}").format(repeat_emoji=repeat_emoji, translation=_("Repeating"))
        text += _("{space}{translation}: {autoplay_emoji}").format(
            space=(" | " if text else ""), autoplay_emoji=autoplay_emoji, translation=_("Auto Play")
        )
        text += _("{space}{translation}: {volume}%").format(
            space=(" | " if text else ""), volume=self.volume, translation=_("Volume")
        )
        page.set_footer(text=text)
        return page

    async def queue_duration(self, history: bool = False) -> int:
        queue = self.history if history else self.queue
        dur = [
            track.duration  # type: ignore
            async for track in AsyncIter(queue.raw_queue).filter(lambda x: not (x.stream or x.is_partial))
        ]
        queue_dur = await asyncstdlib.sum(dur)
        if queue.empty():
            queue_dur = 0
        if history:
            return queue_dur
        try:
            remain = 0 if self.current.stream else self.current.duration - self.position
        except AttributeError:
            remain = 0
        return remain + queue_dur

    async def remove_from_queue(
        self,
        track: Track,
        requester: discord.Member,
        duplicates: bool = False,
    ) -> int:
        if self.queue.empty():
            return 0
        tracks, count = await self.queue.remove(track, duplicates=duplicates)
        self.next_track = None if self.queue.empty() else self.queue.raw_queue.popleft()
        self.node.dispatch_event(QueueTracksRemovedEvent(player=self, requester=requester, tracks=tracks))
        return count

    async def move_track(
        self,
        track: Track,
        requester: discord.Member,
        new_index: int = None,
    ) -> bool:
        if self.queue.empty():
            return False
        index = self.queue.index(track)
        track = await self.queue.get(index)
        self.queue.put_nowait([track], new_index)
        self.next_track = None if self.queue.empty() else self.queue.raw_queue.popleft()
        self.node.dispatch_event(
            QueueTrackPositionChangedEvent(before=index, after=new_index, track=track, player=self, requester=requester)
        )
        return True

    async def maybe_shuffle_queue(self, requester: int) -> None:
        if (await self.player_manager.client.player_config_manager.get_shuffle(self.guild.id)) is False:
            return
        await self.shuffle_queue(requester)

    async def shuffle_queue(self, requester: int) -> None:
        self.node.dispatch_event(QueueShuffledEvent(player=self, requester=self.guild.get_member(requester)))
        await self.queue.shuffle()
        self.next_track = None if self.queue.empty() else self.queue.raw_queue.popleft()

    async def set_autoplay_playlist(self, playlist: int | PlaylistModel) -> None:
        if isinstance(playlist, int):
            await self.config.update_auto_play_playlist_id(playlist)
        else:
            await self.config.update_auto_play_playlist_id(playlist.id)

    async def get_auto_playlist(self) -> PlaylistModel | None:
        try:
            return await self.player_manager.client.playlist_db_manager.get_playlist_by_id(
                await self.config.fetch_auto_play_playlist_id()
            )
        except EntryNotFoundError:
            return None

    async def set_autoplay(self, autoplay: bool) -> None:
        await self.config.update_auto_play(autoplay)

    async def to_dict(self) -> dict:
        """
        Returns a dict representation of the player.
        """
        data = await self.config.fetch_all()
        return {
            "id": int(self.guild.id),
            "channel_id": self.channel.id,
            "current": await self.current.to_json() if self.current else None,
            "text_channel_id": data["text_channel_id"],
            "notify_channel_id": data["notify_channel_id"],
            "forced_channel_id": data["forced_channel_id"],
            "paused": self.paused,
            "repeat_queue": data["repeat_queue"],
            "repeat_current": data["repeat_current"],
            "shuffle": data["shuffle"],
            "auto_shuffle": data["auto_shuffle"],
            "auto_play": data["auto_play"],
            "auto_play_playlist_id": data["auto_play_playlist_id"],
            "volume": self.volume,
            "position": self.position,
            "playing": self.is_playing,
            "queue": [] if self.queue.empty() else [await t.to_json() for t in self.queue.raw_queue],
            "history": [] if self.history.empty() else [await t.to_json() for t in self.history.raw_queue],
            "effect_enabled": self._effect_enabled,
            "effects": {
                "volume": self._volume.to_dict(),
                "equalizer": self._equalizer.to_dict(),
                "karaoke": self._karaoke.to_dict(),
                "timescale": self._timescale.to_dict(),
                "tremolo": self._tremolo.to_dict(),
                "vibrato": self._vibrato.to_dict(),
                "rotation": self._rotation.to_dict(),
                "distortion": self._distortion.to_dict(),
                "low_pass": self._low_pass.to_dict(),
                "channel_mix": self._channel_mix.to_dict(),
                "echo": self._echo.to_dict(),
            },
            "self_deaf": data["self_deaf"],
            "extras": {
                "last_track": await self.last_track.to_json() if self.last_track else None,
                "next_track": await self.next_track.to_json() if self.next_track else None,
                "was_alone_paused": self._was_alone_paused,
            },
        }

    async def save(self) -> None:
        await self.node.node_manager.client.player_state_db_manager.save_player(await self.to_dict())

    async def restore(self, player: PlayerStateModel, requester: discord.User | discord.Member) -> None:
        # sourcery no-metrics
        if self._restored is True:
            return
        self._was_alone_paused = player.extras.get("was_alone_paused", False)
        current = (
            Track(
                node=self.node,
                data=player.current.pop("track"),
                query=await Query.from_string(player.current.pop("query")),
                **player.current.pop("extra"),
                **player.current,
            )
            if player.current
            else None
        )
        next_track = (
            Track(
                node=self.node,
                data=n_track.pop("track"),
                query=await Query.from_string(n_track.pop("query")),
                **n_track.pop("extra"),
                **n_track,
            )
            if (n_track := player.extras.get("next_track", {}))
            else None
        )
        last_track = (
            Track(
                node=self.node,
                data=l_track.pop("track"),
                query=await Query.from_string(l_track.pop("query")),
                **l_track.pop("extra"),
                **l_track,
            )
            if (l_track := player.extras.get("last_track", {}))
            else None
        )
        self.last_track = last_track
        self.next_track = next_track
        self.current = None
        self.paused = player.paused
        if self._autoplay_playlist is None:
            self._autoplay_playlist = (
                await self.player_manager.client.playlist_db_manager.get_playlist_by_id(player.auto_play_playlist_id)
                if player.auto_play_playlist_id
                else None
            )
        self._last_position = player.position
        queue = (
            [
                Track(
                    node=self.node,
                    data=t.pop("track"),
                    query=await Query.from_string(t.pop("query")),
                    **t.pop("extra"),
                    **t,
                )
                async for t in AsyncIter(player.queue, steps=200)
            ]
            if player.queue
            else []
        )
        history = (
            [
                Track(
                    node=self.node,
                    data=t.pop("track"),
                    query=await Query.from_string(t.pop("query")),
                    **t.pop("extra"),
                    **t,
                )
                async for t in AsyncIter(player.history)
            ]
            if player.history
            else []
        )
        self.queue.raw_queue = collections.deque(queue)
        self.queue.raw_b64s = [t.track for t in queue if t.track]
        self.history.raw_queue = collections.deque(history)
        self.history.raw_b64s = [t.track for t in history]
        self._effect_enabled = player.effect_enabled
        effects = player.effects
        if (v := effects.get("volume", None)) and (f := Volume.from_dict(v)) and f.changed:
            self._volume = f
        if (v := effects.get("equalizer", None)) and (f := Equalizer.from_dict(v)) and f.changed:
            self._equalizer = f
        if (v := effects.get("karaoke", None)) and (f := Karaoke.from_dict(v)) and f.changed:
            self._karaoke = f
        if (v := effects.get("timescale", None)) and (f := Timescale.from_dict(v)) and f.changed:
            self._timescale = f
        if (v := effects.get("tremolo", None)) and (f := Tremolo.from_dict(v)) and f.changed:
            self._tremolo = f
        if (v := effects.get("vibrato", None)) and (f := Vibrato.from_dict(v)) and f.changed:
            self._vibrato = f
        if (v := effects.get("rotation", None)) and (f := Rotation.from_dict(v)) and f.changed:
            self._rotation = f
        if (v := effects.get("distortion", None)) and (f := Distortion.from_dict(v)) and f.changed:
            self._distortion = f
        if (v := effects.get("low_pass", None)) and (f := LowPass.from_dict(v)) and f.changed:
            self._low_pass = f
        if (v := effects.get("channel_mix", None)) and (f := ChannelMix.from_dict(v)) and f.changed:
            self._channel_mix = f
        if (v := effects.get("echo", None)) and (f := Echo.from_dict(v)) and f.changed:
            self._echo = f
        if current:
            current.timestamp = int(player.position)
            self.queue.put_nowait([current], index=0)
        await self.change_to_best_node(ops=False)
        if self.has_effects:
            await self.node.filters(
                guild_id=self.channel.guild.id,
                equalizer=self.equalizer,
                karaoke=self.karaoke,
                timescale=self.timescale,
                tremolo=self.tremolo,
                vibrato=self.vibrato,
                rotation=self.rotation,
                distortion=self.distortion,
                low_pass=self.low_pass,
                channel_mix=self.channel_mix,
                echo=self.echo,
            )
        if self.volume_filter.changed:
            await self.node.send(op="volume", guildId=self.guild_id, volume=self.volume)
        if player.playing:
            await self.next(requester)  # type: ignore
        self.last_track = last_track
        self._restored = True
        await self.player_manager.client.player_state_db_manager.delete_player(guild_id=self.guild.id)
        self.node.dispatch_event(PlayerRestoredEvent(self, requester))
        self.stopped = (not await self.autoplay_enabled()) and not self.queue.qsize() and not self.current
        LOGGER.info("Player restored - %s", self)
