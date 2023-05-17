from __future__ import annotations

import asyncio
import collections
import contextlib
import datetime
import pathlib
import random
import time
from collections.abc import Coroutine
from itertools import islice
from typing import TYPE_CHECKING, Any, Literal

import asyncpg
import discord
from dacite import from_dict
from discord import VoiceProtocol
from discord.abc import Messageable

from pylav.constants.config import DEFAULT_SEARCH_SOURCE, ENABLE_NODE_RESUMING
from pylav.constants.coordinates import REGION_TO_COUNTRY_COORDINATE_MAPPING
from pylav.constants.regex import VOICE_CHANNEL_ENDPOINT
from pylav.enums.plugins.sponsorblock import SegmentCategory
from pylav.events.node import NodeChangedEvent
from pylav.events.player import (
    FiltersAppliedEvent,
    PlayerAutoDisconnectedAloneEvent,
    PlayerAutoDisconnectedEmptyQueueEvent,
    PlayerAutoPausedEvent,
    PlayerAutoResumedEvent,
    PlayerDisconnectedEvent,
    PlayerMovedEvent,
    PlayerPausedEvent,
    PlayerRepeatEvent,
    PlayerRestoredEvent,
    PlayerResumedEvent,
    PlayerStoppedEvent,
    PlayerUpdateEvent,
    PlayerVolumeChangedEvent,
    QuickPlayEvent,
)
from pylav.events.queue import (
    QueueEndEvent,
    QueueShuffledEvent,
    QueueTrackPositionChangedEvent,
    QueueTracksAddedEvent,
    QueueTracksRemovedEvent,
)
from pylav.events.track import (
    TrackAutoPlayEvent,
    TrackEndEvent,
    TrackExceptionEvent,
    TrackPreviousRequestedEvent,
    TrackResumedEvent,
    TrackSeekEvent,
    TrackSkippedEvent,
    TrackStuckEvent,
)
from pylav.exceptions.database import EntryNotFoundException
from pylav.exceptions.node import (
    NodeHasNoFiltersException,
    NoNodeAvailableException,
    NoNodeWithRequestFunctionalityAvailableException,
)
from pylav.exceptions.request import HTTPException
from pylav.exceptions.track import TrackNotFoundException
from pylav.extension.radio import RadioBrowser
from pylav.helpers.format.strings import format_time_dd_hh_mm_ss, format_time_string, shorten_string
from pylav.helpers.time import get_now_utc
from pylav.logging import getLogger
from pylav.nodes.api.responses.exceptions import LavalinkException
from pylav.nodes.api.responses.player import State
from pylav.nodes.api.responses.rest_api import LavalinkPlayer
from pylav.nodes.api.responses.track import Track as APITrack
from pylav.nodes.api.responses.websocket import TrackException
from pylav.nodes.node import Node
from pylav.players.filters import (
    ChannelMix,
    Distortion,
    Echo,
    Equalizer,
    Karaoke,
    LowPass,
    Rotation,
    Timescale,
    Tremolo,
    Vibrato,
    Volume,
)
from pylav.players.filters.misc import FilterMixin
from pylav.players.query.obj import Query
from pylav.players.tracks.obj import Track
from pylav.players.utils import PlayerQueue, TrackHistoryQueue
from pylav.storage.models.player.config import PlayerConfig
from pylav.storage.models.player.state import PlayerState
from pylav.storage.models.playlist import Playlist
from pylav.type_hints.bot import DISCORD_BOT_TYPE, DISCORD_INTERACTION_TYPE
from pylav.type_hints.dict_typing import JSON_DICT_TYPE

try:
    from redbot.core.i18n import Translator

    _ = Translator("PyLav", pathlib.Path(__file__))
except ImportError:
    Translator = None

    def _(string: str) -> str:
        return string


if TYPE_CHECKING:
    from pylav.core.client import Client
    from pylav.players.manager import PlayerController


class Player(VoiceProtocol):
    __slots__ = (
        "ready",
        "bot",
        "client",
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
        "_paused",
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
        "_pylav",
        "_discord_session_id",
        "_logger",
        "_last_track_stuck_check",
        "_last_track_stuck_position",
        "_paused_position",
    )
    _config: PlayerConfig
    _global_config: PlayerConfig
    _pylav: Client

    def __init__(
        self,
        client: DISCORD_BOT_TYPE,
        channel: discord.channel.VocalGuildChannel,
        *,
        node: Node = None,
    ):
        super().__init__(client, channel)
        self.__adding_lock = asyncio.Lock()
        self.__reconnect_lock = asyncio.Lock()
        self.__playing_lock = asyncio.Lock()

        self.ready = asyncio.Event()
        self.bot = self.client = client
        self._channel = None
        self.channel = channel
        self.channel_id = channel.id
        self.node: Node = node
        self._logger = getLogger(f"PyLav.Player-{channel.guild.id}")
        self.player_manager: PlayerController = None  # type: ignore
        self._original_node: Node = None  # type: ignore
        self._voice_state = {}
        self._region = channel.rtc_region or "unknown_pylav"
        self._coordinates = REGION_TO_COUNTRY_COORDINATE_MAPPING.get(self._region, (0, 0))
        self._connected = False
        self.connected_at = get_now_utc()
        self.last_track: Track | None = None
        self.next_track: Track | None = None
        self._hashed_voice_state = None
        self._discord_session_id = None

        self._user_data = {}

        self._paused = False
        self.stopped = False
        self._last_update = 0
        self._last_position = 0
        self._paused_position = 0
        self.position_timestamp = 0
        self._ping = 0
        self.queue: PlayerQueue[Track] = PlayerQueue()
        self.history: TrackHistoryQueue[Track] = TrackHistoryQueue(maxsize=100)
        self.current: Track | None = None
        self._post_init_completed = False
        self._autoplay_playlist: Playlist | None = None
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
        self._last_track_stuck_check = 0
        self._last_track_stuck_position = -1
        self._waiting_for_node = asyncio.Event()

    def __hash__(self):
        return hash((self.channel.guild.id, self.channel_id))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__hash__() == other.__hash__()

    def __repr__(self):
        return (
            f"<Player id={self.guild.id} "
            f"channel={self.channel.id} "
            f"playing={self.is_active} "
            f"queue={self.queue.size()} "
            f"node={self.node}>"
        )

    def add_voice_to_payload(self, payload: JSON_DICT_TYPE) -> JSON_DICT_TYPE:
        if not payload:
            payload = {}
        if {"sessionId", "token", "endpoint"} == self._voice_state.keys():
            payload["voice"] = self._voice_state
        return payload

    async def post_init(
        self,
        node: Node,
        player_manager: PlayerController,
        config: PlayerConfig,
        pylav: Client,
        requester: discord.Member = None,
    ) -> None:
        # sourcery no-metrics
        if self._post_init_completed:
            return
        self._pylav = pylav
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
            self._logger.verbose("Player restored in postinit - %s", self)
        else:
            await self._apply_filters_to_new_player(config, player_manager)

        await self._create_job_for_player()
        self.ready.set()

    async def _create_job_for_player(self) -> None:
        now_time = get_now_utc()
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

    async def _apply_filters_to_new_player(self, config: PlayerConfig, player_manager: PlayerController) -> None:
        self._volume = Volume(await player_manager.client.player_config_manager.get_volume(self.guild.id))
        effects = await config.fetch_effects()
        if (v := effects.get("volume", None)) and (f := Volume.from_dict(v)):
            self._volume = f
        if (
            self.node.has_filter("equalizer")
            and (eq := effects.get("equalizer", None))
            and (f := Equalizer.from_dict(eq))  # noqa
        ):
            self._equalizer = f
        if (
            self.node.has_filter("karaoke")
            and (k := effects.get("karaoke", None))
            and (f := Karaoke.from_dict(k))  # noqa
        ):
            self._karaoke = f
        if (
            self.node.has_filter("timescale")
            and (ts := effects.get("timescale", None))
            and (f := Timescale.from_dict(ts))  # noqa
        ):
            self._timescale = f
        if (
            self.node.has_filter("tremolo")
            and (tr := effects.get("tremolo", None))
            and (f := Tremolo.from_dict(tr))  # noqa
        ):
            self._tremolo = f
        if (
            self.node.has_filter("vibrato")
            and (vb := effects.get("vibrato", None))
            and (f := Vibrato.from_dict(vb))  # noqa
        ):
            self._vibrato = f
        if (
            self.node.has_filter("rotation")
            and (ro := effects.get("rotation", None))
            and (f := Rotation.from_dict(ro))  # noqa
        ):
            self._rotation = f
        if (
            self.node.has_filter("distortion")
            and (di := effects.get("distortion", None))
            and (f := Distortion.from_dict(di))  # noqa
        ):
            self._distortion = f
        if (
            self.node.has_filter("lowPass")
            and (lo := effects.get("lowpass", None))
            and (f := LowPass.from_dict(lo))  # noqa
        ):
            self._low_pass = f
        if (
            self.node.has_filter("channelMix")
            and (ch := effects.get("channel_mix", None))
            and (f := ChannelMix.from_dict(ch))  # noqa
        ):
            self._channel_mix = f
        if self.node.has_filter("echo") and (echo := effects.get("echo", None)) and (f := Echo.from_dict(echo)):  # noqa
            self._echo = f
        payload = {}
        if any(
            [
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
            payload["filters"] = self.node.get_filter_payload(
                player=self,
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
        if self.volume_filter:
            payload["volume"] = self.volume
        if payload:
            await self.node.patch_session_player(guild_id=self.guild.id, payload=payload)

    async def update_current_duration(self) -> Track | None:
        if not self.current:
            return
        if await self.current.is_spotify() or await self.current.is_apple_music():
            await asyncio.sleep(1)
            api_player = await self.fetch_node_player()
            track = api_player.track
            if self.current._processed.info.length != track.info.length:
                object.__setattr__(self.current._processed.info, "length", track.info.length)
                return self.current

    @property
    def paused(self) -> bool:
        return self._paused

    @paused.setter
    def paused(self, value: bool) -> None:
        self._paused = value
        if value:
            self._paused_position = self._last_position + ((time.time() * 1000) - self._last_update)
        else:
            self._paused_position = 0

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
    def config(self) -> PlayerConfig:
        return self._config

    @property
    def lavalink(self) -> Client:
        return self._pylav

    @property
    def pylav(self) -> Client:
        return self._pylav

    @property
    def radio(self) -> RadioBrowser:
        return self.pylav.radio_browser

    def vote_node_down(self) -> int:
        return -1 if (self.node is None or not self.is_active) else self.node.down_vote(self)

    def voted(self) -> bool:
        return self.node.voted(self)

    def unvote_node_down(self) -> int:
        return -1 if (self.node is None or not self.is_active) else not self.node.down_unvote(self)

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
    def filters(self) -> list[FilterMixin]:
        """A list of all  filters"""
        return [
            self.equalizer,
            self.karaoke,
            self.timescale,
            self.tremolo,
            self.vibrato,
            self.rotation,
            self.distortion,
            self.echo,
            self.low_pass,
            self.channel_mix,
        ]

    @property
    def has_effects(self):
        return any(f.changed for f in self.filters)

    @property
    def guild(self) -> discord.Guild:
        return self.channel.guild

    @property
    def is_playing(self) -> bool:
        """Returns the player's track state"""
        return self.is_active and not self.paused

    @property
    def is_active(self) -> bool:
        """Returns the player's track state"""
        return self.is_connected and self.current is not None and not self.stopped

    @property
    def is_connected(self) -> bool:
        """Returns whether the player is connected to a voice-channel or not"""
        return self.channel_id is not None

    @property
    def is_empty(self) -> bool:
        """Returns whether the player is empty or not"""
        return sum(not i.bot for i in self.channel.members) == 0

    async def position(self) -> float:
        """Returns the position in the track, adjusted for delta since last update and the Timescale filter"""
        if not self.is_active:
            return 0

        if self.paused:
            return min(
                self.timescale.adjust_position(self._paused_position)
                if self.timescale.changed
                else self._paused_position,
                await self.current.duration(),
            )

        difference = time.time() * 1000 - self._last_update
        position = self._last_position + difference
        return min(
            self.timescale.adjust_position(position) if self.timescale.changed else position,
            await self.current.duration(),
        )

    @property
    def estimated_position(self) -> float:
        """Returns the position in the track, adjusted for delta since last update"""
        if not self.is_active:
            return 0

        if self.paused:
            return min(
                self.timescale.adjust_position(self._paused_position)
                if self.timescale.changed
                else self._paused_position,
                self.current._duration,
            )

        difference = time.time() * 1000 - self._last_update
        position = self._last_position + difference
        return min(
            self.timescale.adjust_position(position) if self.timescale.changed else position,
            self.current._duration,
        )

    async def fetch_player_stats(self, return_position: bool = False):
        try:
            player = await self.fetch_node_player()
        except Exception:  # noqa
            return
        if isinstance(player, HTTPException):
            return
        self._last_position = player.track.info.position if player.track else 0
        self._last_update = time.time() * 1000
        self.paused = player.paused
        self._volume = Volume(player.volume)
        self._connected = player.state.connected
        self._ping = player.state.ping
        if self.current:
            self.current.last_known_position = self._last_position
            object.__setattr__(self.current._processed.info, "length", player.track.info.length)
        if return_position:
            return player.track.info.position or 0 if player.track else 0

    async def fetch_position(self, skip_fetch: bool = False) -> float:
        """Returns the position in the track"""
        pos = await self.position()
        if skip_fetch:
            return pos
        try:
            if not self.current:
                return pos
            # await self.fetch_player_stats()
        except Exception:  # noqa
            return pos
        return pos

    async def auto_pause_task(self):
        with contextlib.suppress(
            asyncio.exceptions.CancelledError,
        ):
            if not self.ready.is_set():
                return
            if not self.is_connected:
                self._logger.trace(
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
                    self._logger.verbose(
                        "Auto Pause task for %s - Player is alone - starting countdown",
                        self,
                    )
                    self._last_alone_paused_check = time.time()
                if (self._last_alone_paused_check + feature.time) <= time.time():
                    self._logger.debug(
                        "Auto Pause task for %s - Player in an empty channel for longer than %s seconds - Pausing",
                        self,
                        feature.time,
                    )
                    await self.set_pause(pause=True, requester=self.guild.me)
                    self._was_alone_paused = True
                    self._last_alone_paused_check = 0
                    self.player_manager.client.dispatch_event(PlayerAutoPausedEvent(self))
            else:
                self._last_alone_paused_check = 0

    async def auto_resume_task(self):
        with contextlib.suppress(
            asyncio.exceptions.CancelledError,
        ):
            if not self.ready.is_set():
                return
            if not self._was_alone_paused:
                self._logger.trace(
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
                self._logger.debug(
                    "Auto Resume task for %s - Player in an non-empty channel - Resuming",
                    self,
                    feature.time,
                )
                await self.set_pause(pause=False, requester=self.guild.me)
                self._was_alone_paused = False
                self.player_manager.client.dispatch_event(PlayerAutoResumedEvent(self))

    async def auto_dc_task(self):
        with contextlib.suppress(
            asyncio.exceptions.CancelledError, NoNodeAvailableException, asyncpg.exceptions.CannotConnectNowError
        ):
            if not self.ready.is_set():
                return
            if not self.is_connected:
                self._logger.trace(
                    "Auto Disconnect task fired while player is not connected to a voice channel - discarding",
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
                    self._logger.verbose(
                        "Auto Disconnect task - Player is alone - starting countdown",
                    )
                    self._last_alone_dc_check = time.time()
                if (self._last_alone_dc_check + feature.time) <= time.time():
                    self._logger.debug(
                        "Auto Disconnect task - Player in an empty channel for longer than %s seconds "
                        "- Disconnecting",
                        feature.time,
                    )
                    await self.disconnect(requester=self.guild.me)
                    self._last_alone_dc_check = 0
                    self.player_manager.client.dispatch_event(PlayerAutoDisconnectedEmptyQueueEvent(self))
            else:
                self._last_alone_dc_check = 0

    async def auto_empty_queue_task(self):
        with contextlib.suppress(
            asyncio.exceptions.CancelledError, NoNodeAvailableException, asyncpg.exceptions.CannotConnectNowError
        ):
            if not self.ready.is_set():
                return
            if not self.is_connected:
                self._logger.trace(
                    "Auto Empty Queue task fired while player is not connected to a voice channel - discarding",
                )
                return
            if self.current:
                self._logger.trace("Auto Empty Queue task - Current track is not empty - discarding")
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
                    self._logger.verbose(
                        "Auto Empty Queue task - Queue is empty - starting countdown",
                    )
                    self._last_empty_queue_check = time.time()
                if (self._last_empty_queue_check + feature.time) <= time.time():
                    self._logger.debug(
                        "Auto Empty Queue task - Queue is empty for longer than %s seconds "
                        "- Stopping and disconnecting",
                        feature.time,
                    )
                    await self.stop(requester=self.guild.me)
                    await self.disconnect(requester=self.guild.me)
                    self._last_empty_queue_check = 0
                    self.player_manager.client.dispatch_event(PlayerAutoDisconnectedAloneEvent(self))
            else:
                self._last_empty_queue_check = 0

    async def auto_save_task(self):
        with contextlib.suppress(
            asyncio.exceptions.CancelledError, NoNodeAvailableException, asyncpg.exceptions.CannotConnectNowError
        ):
            if not self.is_active:
                self._logger.trace(
                    "Auto save task for %s fired while player is not active - discarding",
                    self,
                )
                return
            self._logger.trace("Auto save task for %s - Saving the player at %s", self, get_now_utc())
            await self.save()

    async def change_to_best_node(
        self, feature: str = None, ops: bool = True, forced: bool = True, skip_position_fetch: bool = False
    ) -> Node | None:
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
            self._logger.warning(
                "No node with %s functionality available - Waiting for one to become available!", feature
            )
            node = await self.node.node_manager.find_best_node(
                region=self.region, feature=feature, coordinates=self.coordinates, wait=True
            )

        if feature and not node:
            self._logger.warning(
                "No node with %s functionality available after one temporarily became available!", feature
            )
            raise NoNodeWithRequestFunctionalityAvailableException(
                f"No node with {feature} functionality available", feature
            )
        if node != self.node or (not ops) or forced:
            await self.change_node(node, ops=ops, skip_position_fetch=skip_position_fetch, forced=forced)
            return node

    async def change_to_best_node_diff_region(
        self, feature: str = None, ops: bool = True, skip_position_fetch: bool = False, forced: bool = False
    ) -> Node | None:
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
            self._logger.warning(
                "No node with %s functionality available - Waiting for one to become available!", feature
            )
            node = await self.node.node_manager.find_best_node(
                region=self.region, feature=feature, coordinates=self.coordinates, wait=True
            )

        if feature and not node:
            self._logger.warning(
                "No node with %s functionality available after one temporarily became available!", feature
            )
            raise NoNodeWithRequestFunctionalityAvailableException(
                f"No node with {feature} functionality available", feature
            )

        if node != self.node or (not ops) or forced:
            await self.change_node(node, ops=ops, skip_position_fetch=skip_position_fetch, forced=forced)
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
        if "token" in data and data["token"]:
            self._voice_state.update({"token": data["token"]})
        if "endpoint" in data and data["endpoint"]:
            self._voice_state.update({"endpoint": data["endpoint"]})
            if match := VOICE_CHANNEL_ENDPOINT.match(data["endpoint"]):
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
        self._discord_session_id = data["session_id"]
        self.channel_id = data["channel_id"]
        if not self.channel_id:  # We're disconnecting
            await self.disconnect(force=True, requester=self.guild.me)
            return
        if self.channel_id != int(self.channel_id):
            self.channel = self.guild.get_channel(int(self.channel_id))

        # Ensure we're in the correct voice channel
        if (vc := await self.forced_vc()) and vc.id != int(self.channel_id):
            self._logger.debug(
                "Player was moved to %s, which is different than the forced voice channel; Moving to %s",
                self.channel_id,
                vc.id,
            )
            await self.move_to(channel=vc, requester=self.guild.me)
            return
        await self._dispatch_voice_update()

    async def _dispatch_voice_update(self) -> None:
        if {"sessionId", "token", "endpoint"} == self._voice_state.keys():
            existing_session = await self.fetch_node_player()

            if isinstance(existing_session, HTTPException) or (
                existing_session.voice.sessionId != self._voice_state["sessionId"]
                or existing_session.voice.token != self._voice_state["token"]
                or existing_session.voice.endpoint != self._voice_state["endpoint"]
            ):
                await self.node.patch_session_player(self.guild.id, payload={"voice": self._voice_state})
            self._waiting_for_node.set()
            self._hashed_voice_state = hash(tuple(self._voice_state.items()))

    async def _query_to_track(
        self,
        requester: int,
        track: Track | APITrack | dict | str | None,
        query: Query = None,
    ) -> Track:
        if not isinstance(track, Track):
            track = await Track.build_track(
                node=self.node, data=track, query=query, requester=requester, player_instance=self
            )
        else:
            track._requester = requester
            track._player = self
        return track

    async def add(
        self,
        requester: int,
        track: Track | APITrack | dict | str | None,
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
        async with self.__adding_lock:
            at = await self._query_to_track(requester, track, query)
            await self.queue.put([at], index=index)
            if index is None:
                await self.maybe_shuffle_queue(requester=requester)
            self.next_track = None if self.queue.empty() else self.queue.raw_queue.popleft()
            self.node.dispatch_event(QueueTracksAddedEvent(self, self.guild.get_member(requester), [at]))

    async def bulk_add(
        self,
        tracks_and_queries: list[Track | APITrack | dict | str | list[tuple[Track | APITrack | dict | str, Query]]],
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
        async with self.__adding_lock:
            output = []
            is_list = isinstance(tracks_and_queries[0], (list, tuple))
            for entry in tracks_and_queries:
                track, query = entry if is_list else (entry, None)
                track = await self._query_to_track(requester, track, query)
                output.append(track)
            await self.queue.put(output, index=index)
            if index is None:
                await self.maybe_shuffle_queue(requester=requester)
            self.next_track = None if self.queue.empty() else self.queue.raw_queue.popleft()
            self.node.dispatch_event(QueueTracksAddedEvent(self, self.guild.get_member(requester), output))

    async def previous(self, requester: discord.Member, bypass_cache: bool = False) -> None:
        async with self.__playing_lock:
            if self.history.empty():
                raise TrackNotFoundException(_("There are no tracks currently in the player history."))
            self.stopped = False
            track = await self.history.get()
            if self.current:
                self.last_track = self.current

            if await track.query() and not self.node.has_source(await track.requires_capability()):
                self.current = None
                await self.change_to_best_node(feature=await track.requires_capability(), skip_position_fetch=True)

            self.current = track
            payload = {"encodedTrack": track.encoded}
            if self.volume_filter:
                payload["volume"] = self.volume
            await self.node.patch_session_player(guild_id=self.guild.id, payload=payload, no_replace=False)

            self.node.dispatch_event(TrackPreviousRequestedEvent(self, requester, track))

    async def quick_play(
        self,
        requester: discord.Member,
        track: Track | APITrack | dict | str | None,
        query: Query,
        no_replace: bool = False,
        bypass_cache: bool = False,
    ) -> None:
        async with self.__playing_lock:
            track = await Track.build_track(
                node=self.node, data=track, query=query, requester=requester.id, player_instance=self
            )
            self.next_track = None
            self.last_track = None
            self.stopped = False
            if self.current:
                self.current.timestamp = self.fetch_position()
                await self.queue.put([self.current], 0)
                self.next_track = self.current
                self.last_track = self.current

            if await track.query() and not self.node.has_source(await track.requires_capability()):
                self.current = None
                await self.change_to_best_node(feature=await track.requires_capability(), skip_position_fetch=True)
            self.current = track
            if self.next_track is None and not self.queue.empty():
                self.next_track = self.queue.raw_queue.popleft()
            payload = {"encodedTrack": track.encoded}
            if self.volume_filter:
                payload["volume"] = self.volume
            await self.node.patch_session_player(guild_id=self.guild.id, payload=payload, no_replace=no_replace)
            self.node.dispatch_event(QuickPlayEvent(self, requester, track))

    def next(self, requester: discord.Member = None, node: Node = None) -> Coroutine[Any, Any, None]:
        return self.play(None, None, requester or self.bot.user, node=node)  # type: ignore

    async def play(
        self,
        track: Track | APITrack | dict | str | None,
        query: Query | None,
        requester: discord.Member,
        start_time: int = 0,
        end_time: int = None,
        no_replace: bool = False,
        bypass_cache: bool = False,
        node: Node = None,
    ) -> None:  # sourcery skip: low-code-quality
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
        requester: :class:`discord.Member`
            The member that requested the track.
        bypass_cache: Optional[:class:`bool`]
            If set to true, the track will not be looked up in the cache. Defaults to `False`.
        node: Optional[:class:`Node`]
            The node to use. Defaults the best available node with the needed feature.
        """
        # sourcery no-metrics
        async with self.__playing_lock:
            auto_play, payload = await self._on_play_reset()
            if track is not None and isinstance(track, (Track, APITrack, dict, str, type(None))):
                track = await Track.build_track(
                    node=self.node, data=track, query=query, requester=requester.id, player_instance=self
                )
            if self.current:
                await self._process_repeat_on_play()
            if self.current:
                await self.history.put([self.current], discard=True)
                self.last_track = self.current
            self.current = None
            if not track:
                auto_play, track, returned = await self._process_play_no_track(auto_play, track)
                if returned:
                    return
            if await track.query() is None:
                track._query = await Query.from_base64(track.encoded, lazy=True)
            if node:
                if self.node != node:
                    await self.change_node(node)
            else:
                try:
                    await self.change_to_best_node(feature=await track.requires_capability(), skip_position_fetch=True)
                except NoNodeWithRequestFunctionalityAvailableException as exc:
                    await self._process_error_on_play(exc, track)
                    return
            track._node = self.node

            await self._process_partial_payload(end_time, payload, start_time, track)

            if no_replace is None:
                no_replace = False
            if not isinstance(no_replace, bool):
                raise TypeError("no_replace must be a bool")
            if not track.encoded:
                return await self.play(None, None, requester or self.bot.user, node=node)
            self.current = track
            self.next_track = None if self.queue.empty() else self.queue.raw_queue.popleft()
            payload["encodedTrack"] = track.encoded
            if self.volume_filter:
                payload["volume"] = self.volume

            await self.node.patch_session_player(guild_id=self.guild.id, payload=payload, no_replace=no_replace)
            if auto_play:
                self.node.dispatch_event(TrackAutoPlayEvent(player=self, track=track))

    async def _process_partial_payload(self, end_time, payload, start_time, track: Track):
        if start_time or track.timestamp:
            await self._process_payload_position(payload, start_time, track)
        if end_time is not None:
            await self._process_payload_end_time(end_time, payload, track)

    async def _process_payload_end_time(self, end_time, payload, track: Track):
        if not isinstance(end_time, int) or not 0 <= end_time <= self.timescale.reverse_position(
            await track.duration()
        ):
            raise ValueError(
                "end_time must be an int with a value equal to, or greater than 0, and less than the track duration"
            )
        payload["endTime"] = int(end_time)

    async def _process_payload_position(self, payload, start_time, track: Track):
        start_time = start_time or track.timestamp
        if not isinstance(start_time, int) or not 0 <= start_time <= self.timescale.reverse_position(
            await track.duration()
        ):
            raise ValueError(
                "start_time must be an int with a value equal to, "
                "or greater than 0, and less than the track duration"
            )
        payload["position"] = int(start_time or track.timestamp)

    async def _process_partial_playlist(
        self, track: Track, requester: int | discord.Member | None
    ) -> bool | list[Track]:
        try:
            tracks = await track.search_all(self, requester.id if requester else self.client.user.id)
            if not tracks:
                raise TrackNotFoundException(f"No tracks found for query {await track.query_identifier()}")
        except TrackNotFoundException as exc:
            if not track:
                raise TrackNotFoundException from exc
            await self._process_error_on_play(exc, track)
            return False
        return tracks

    async def _on_play_reset(self):
        payload = {}
        self._last_update = 0
        self._last_position = 0
        self.position_timestamp = 0
        self.paused = False
        self.stopped = False
        auto_play = False
        self.next_track = None
        self.last_track = None
        return auto_play, payload

    async def _process_play_no_track(self, auto_play, track):
        if self.queue.empty():
            if await self.autoplay_enabled() and (
                available_tracks := await (await self.get_auto_playlist()).fetch_tracks()
            ):
                auto_play, track = await self._process_autoplay_on_play(available_tracks)
            else:
                await self.stop(
                    requester=self.guild.get_member(self.node.node_manager.client.bot.user.id)
                )  # Also sets current to None.
                self.history.clear()
                self.last_track = None
                self.node.dispatch_event(QueueEndEvent(self))
                return auto_play, track, True
        else:
            track = await self.queue.get()
        return auto_play, track, False

    async def _process_error_on_play(self, exc: Exception, track: Track) -> None:
        event = TrackExceptionEvent(
            self,
            track,
            self.node,
            event_object=TrackException(
                op="event",
                guildId=str(self.guild.id),
                type="TrackExceptionEvent",
                track=await track.fetch_full_track_data(),
                exception=LavalinkException(cause=str(exc), message=str(exc), severity="suspicious"),
            ),
        )
        self.node.dispatch_event(event)
        await self._handle_event(event)

    async def _process_autoplay_on_play(self, available_tracks):
        available_tracks = {track["encoded"]: track for track in available_tracks}
        if tracks_not_in_history := list(set(available_tracks) - set(self.history.raw_b64s)):
            track = await Track.build_track(
                node=self.node,
                data=available_tracks[random.choice(list(tracks_not_in_history))],
                query=None,
                requester=self.client.user.id,
                player_instance=self,
            )
        else:
            track = await Track.build_track(
                node=self.node,
                data=available_tracks[random.choice(list(available_tracks))],
                query=None,
                requester=self.client.user.id,
                player_instance=self,
            )
        auto_play = True
        self.next_track = None
        return auto_play, track

    async def _process_repeat_on_play(self):
        if await self.config.fetch_repeat_current():
            await self.add(self.current.requester_id, self.current)
        elif await self.config.fetch_repeat_queue():
            await self.add(self.current.requester_id, self.current, index=-1)

    async def resume(self, requester: discord.Member = None):
        self._last_update = 0
        self.stopped = False
        self._last_position = 0
        payload = {
            "encodedTrack": self.current.encoded,
            "position": int(self.current.last_known_position if self.current else await self.fetch_position()),
        }
        if self.volume_filter:
            payload["volume"] = self.volume
        await self.node.patch_session_player(guild_id=self.guild.id, payload=payload, no_replace=False)
        self.node.dispatch_event(PlayerResumedEvent(player=self, requester=requester or self.client.user.id))

    async def skip(self, requester: discord.Member) -> None:
        """Plays the next track in the queue, if any"""
        previous_track = self.current
        previous_position = await self.fetch_position()
        # Send a Stop OP to clear the buffer for avoid a small continuation on playback after skip fires
        payload = {"encodedTrack": None}
        await self.node.patch_session_player(guild_id=self.guild.id, payload=payload)
        await self.next(requester=requester)
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
        payload = {"paused": pause}
        await self.node.patch_session_player(guild_id=self.guild.id, payload=payload)
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
        volume = max([min([vol, max_volume]), 0])
        if volume == self.volume:
            return
        await self.config.update_volume(volume)
        self._volume = Volume(volume)
        payload = {"volume": volume}
        await self.node.patch_session_player(guild_id=self.guild.id, payload=payload)
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
        if self.current and await self.current.is_seekable():
            if with_filter:
                position = await self.fetch_position()
            position = max([min([position, await self.current.duration()]), 0])
            if self.timescale.changed:
                position = self.timescale.reverse_position(position)
            self.node.dispatch_event(
                TrackSeekEvent(self, requester, self.current, before=await self.fetch_position(), after=position)
            )
            payload = {"position": int(position)}
            await self.node.patch_session_player(guild_id=self.guild.id, payload=payload)
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
        if isinstance(event, TrackStuckEvent) or isinstance(event, TrackEndEvent) and event.reason == "finished":
            self.last_track = self.current
            await self.next()
            self.next_track = None if self.queue.empty() else self.queue.raw_queue.popleft()
        elif isinstance(event, TrackExceptionEvent):
            self.last_track = self.current
            await self.next()
            self.next_track = None if self.queue.empty() else self.queue.raw_queue.popleft()

    async def _update_state(self, state: State) -> None:
        """
        Updates the position of the player.
        Parameters
        ----------
        state: :class:`dict`
            The state that is given to update.
        """
        self._last_update = time.time() * 1000
        self._last_position = state.position
        self.position_timestamp = state.time
        self._ping = state.ping
        if self.current:
            self.current.last_known_position = self._last_position

        event = PlayerUpdateEvent(self, self._last_position, self.position_timestamp)
        self.node.dispatch_event(event)

    async def change_node(
        self, node: Node, ops: bool = True, forced: bool = False, skip_position_fetch: bool = False
    ) -> None:
        """
        Changes the player's node
        Parameters
        ----------
        node: :class:`Node`
            The node the player is changed to.
        ops: :class:`bool`
            Whether to change apply the volume and filter ops on change.
        forced: :class:`bool`
            Whether to force the change
        skip_position_fetch: :class:`bool`
            Whether to skip the position fetch.
        """
        if node == self.node and self.node.available and ops and not forced:
            return
        payload = {}
        old_node = self.node
        position = await self.fetch_position(skip_fetch=skip_position_fetch)
        if self.timescale.changed:
            position = self.timescale.reverse_position(position)
        self.node = node
        await asyncio.wait_for(self._waiting_for_node.wait(), timeout=None)
        await node.websocket.wait_until_ready()
        if old_node.available and node.session_id != old_node.session_id:
            await old_node.delete_session_player(self.guild.id)
        if self._voice_state:
            await self._dispatch_voice_update()
        if node.session_id != old_node.session_id and self.node.supports_sponsorblock:
            await self.add_sponsorblock_categories()
        if ops:
            if self.current:
                payload = {"encodedTrack": self.current.encoded, "position": int(position)}
                if self.paused:
                    payload["paused"] = self.paused

                self._last_update = time.time() * 1000

            if self.has_effects:
                payload["filters"] = node.get_filter_payload(
                    player=self,
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
            if self.volume_filter:
                payload["volume"] = self.volume
        if old_node.identifier != node.identifier:
            node.dispatch_event(NodeChangedEvent(self, old_node, node))
            if payload:
                await node.patch_session_player(guild_id=self.guild.id, payload=payload)

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
        async with self.__reconnect_lock:
            await self.guild.change_voice_state(
                channel=self.channel,
                self_mute=self_mute,
                self_deaf=deaf if (deaf := await self.self_deaf()) is True else self_deaf,
            )
            self._connected = True
            self.connected_at = get_now_utc()
            self._logger.debug(
                "Connected to voice channel"
                if self.guild.me not in self.channel.members
                else "Reconnected to voice channel"
            )

    async def reconnect(self):
        if self.__reconnect_lock.locked():
            return
        async with self.__reconnect_lock:
            self._waiting_for_node.clear()
            shard = self.bot.get_shard(self.guild.shard_id)
            while shard.is_closed():
                await asyncio.sleep(1)

            await self.guild.change_voice_state(
                channel=None,
                self_mute=False,
                self_deaf=False,
            )
            await self.guild.change_voice_state(
                channel=self.channel,
                self_mute=False,
                self_deaf=await self.self_deaf(),
            )
            self._connected = True
            self.connected_at = get_now_utc()
            await asyncio.wait_for(self._waiting_for_node.wait(), timeout=None)
            await self.change_to_best_node(forced=True, skip_position_fetch=True)
            self._logger.debug("Reconnected to voice channel")

    async def disconnect(
        self, *, force: bool = False, requester: discord.Member | None, maybe_resuming: bool = False
    ) -> None:
        try:
            if self.is_active:
                await self.save()
            if (not maybe_resuming) and self.node.can_resume and self.channel_id is not None:
                await self.guild.change_voice_state(channel=None)
            self.node.dispatch_event(PlayerDisconnectedEvent(self, requester))
            self._logger.debug("Disconnected from voice channel")
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
            if not maybe_resuming:
                await self.node.delete_session_player(self.guild.id)
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
        payload = {"encodedTrack": None}
        await self.node.patch_session_player(guild_id=self.guild.id, payload=payload)
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
        if self.config and (vc := await self.forced_vc()) and channel.id != vc.id:  # noqa
            channel = vc
            self._logger.debug("Player has a forced VC enabled replacing channel arg with it")
        if channel == self.channel:
            return
        old_channel = self.channel
        self._logger.debug("Moving from %s to voice channel: %s", self.channel.id, channel.id)
        self.channel = channel
        self_deaf = deaf if (deaf := await self.self_deaf()) is True else self_deaf
        if self.guild.me not in self.channel.members:
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

        Raises
        ------
        ValueError
            If the volume is not between 0 and 1000
        NodeHasNoFiltersException
            If the node does not have specified filter enabled
        """
        if not self.node.has_filter("volume"):
            raise NodeHasNoFiltersException(_("Current node has the volume filter feature disabled."))
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
        if not self.node.has_filter("equalizer"):
            raise NodeHasNoFiltersException(_("Current node has the equalizer feature disabled."))
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
        if not self.node.has_filter("karaoke"):
            raise NodeHasNoFiltersException(_("Current node has the karaoke feature disabled"))
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
        if not self.node.has_filter("timescale"):
            raise NodeHasNoFiltersException(_("Current node has the timescale feature disabled."))
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
        if not self.node.has_filter("tremolo"):
            raise NodeHasNoFiltersException(_("Current node has the tremolo feature disabled."))
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
        if not self.node.has_filter("vibrato"):
            raise NodeHasNoFiltersException(_("Current node has the vibrato feature disabled."))
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
        if not self.node.has_filter("rotation"):
            raise NodeHasNoFiltersException(_("Current node has the rotation feature disabled."))
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
        if not self.node.has_filter("distortion"):
            raise NodeHasNoFiltersException(_("Current node has the distortion feature disabled."))
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
        if not self.node.has_filter("lowPass"):
            raise NodeHasNoFiltersException(_("Current node has the low-pass feature disabled."))
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
        if not self.node.has_filter("echo"):
            raise NodeHasNoFiltersException(_("Current node has the echo feature disabled."))
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
        if not self.node.has_filter("equalizer"):
            raise NodeHasNoFiltersException(_("Current node has the equalizer feature disabled."))
        if not self.node.has_filter("timescale"):
            raise NodeHasNoFiltersException(_("Current node has the timescale feature disabled."))
        await self.set_filters(
            requester=requester,
            low_pass=None,
            equalizer=Equalizer(
                levels=[
                    {"band": 0, "gain": -0.075},
                    {"band": 1, "gain": 0.125},
                    {"band": 2, "gain": 0.125},
                ],
                name="Nightcore",
            ),
            karaoke=self.karaoke or None,
            tremolo=self.tremolo or None,
            vibrato=self.vibrato or None,
            distortion=self.distortion or None,
            timescale=Timescale(speed=1.0, pitch=0.95, rate=1.3),
            channel_mix=self.channel_mix or None,
            echo=self.echo or None,
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
            low_pass=self.low_pass or None,
            equalizer=None,
            timescale=None,
            reset_not_set=True,
            karaoke=self.karaoke or None,
            tremolo=self.tremolo or None,
            vibrato=self.vibrato or None,
            distortion=self.distortion or None,
            channel_mix=self.channel_mix or None,
            echo=self.echo or None,
        )

    async def apply_vaporwave(self, requester: discord.Member) -> None:
        """
        Applies the Vaporwave filter to the player.
        Parameters
        ----------
        requester : discord.Member
            Member who requested the filter change
        """
        if not self.node.has_filter("equalizer"):
            raise NodeHasNoFiltersException(_("Current node has the equalizer feature disabled."))
        if not self.node.has_filter("timescale"):
            raise NodeHasNoFiltersException(_("Current node has the timescale feature disabled."))
        await self.set_filters(
            requester=requester,
            low_pass=None,
            equalizer=Equalizer(
                levels=[
                    {"band": 0, "gain": 0.25},
                    {"band": 1, "gain": 0.2},
                    {"band": 2, "gain": 0.2},
                ],
                name="Vaporwave",
            ),
            karaoke=self.karaoke or None,
            tremolo=self.tremolo or None,
            vibrato=self.vibrato or None,
            distortion=self.distortion or None,
            timescale=Timescale(speed=1.0, pitch=1.0, rate=0.7),
            channel_mix=self.channel_mix or None,
            echo=self.echo or None,
            reset_not_set=True,
        )

    async def remove_vaporwave(self, requester: discord.Member) -> None:
        """
        Removes the Vaporwave filter from the player.
        Parameters
        ----------
        requester : discord.Member
            Member who requested the filter change
        """
        await self.set_filters(
            requester=requester,
            low_pass=self.low_pass or None,
            equalizer=None,
            timescale=None,
            reset_not_set=True,
            karaoke=self.karaoke or None,
            tremolo=self.tremolo or None,
            vibrato=self.vibrato or None,
            distortion=self.distortion or None,
            channel_mix=self.channel_mix or None,
            echo=self.echo or None,
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
        if not self.node.has_filter("channelMix"):
            raise NodeHasNoFiltersException(_("Current node has the channel-mix feature disabled."))
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
    ):  # sourcery skip: low-code-quality
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

        if volume and not self.node.has_filter("volume"):
            volume = None
        if equalizer and not self.node.has_filter("equalizer"):
            equalizer = None
        if karaoke and not self.node.has_filter("karaoke"):
            karaoke = None
        if timescale and not self.node.has_filter("timescale"):
            timescale = None
        if tremolo and not self.node.has_filter("tremolo"):
            tremolo = None
        if vibrato and not self.node.has_filter("vibrato"):
            vibrato = None
        if rotation and not self.node.has_filter("rotation"):
            rotation = None
        if distortion and not self.node.has_filter("distortion"):
            distortion = None
        if low_pass and not self.node.has_filter("lowPass"):
            low_pass = None
        if channel_mix and not self.node.has_filter("channelMix"):
            channel_mix = None
        if echo and not self.node.has_filter("echo"):
            echo = None

        changed = await self._set_filter_variables(
            False,
            channel_mix,
            distortion,
            echo,
            equalizer,
            karaoke,
            low_pass,
            rotation,
            timescale,
            tremolo,
            vibrato,
            volume,
        )

        self._effect_enabled = changed
        if reset_not_set:
            kwargs = await self._process_filters_reset_not_set(
                channel_mix,
                distortion,
                echo,
                equalizer,
                karaoke,
                low_pass,
                rotation,
                timescale,
                tremolo,
                vibrato,
                volume,
            )
        else:
            kwargs = {
                "volume": volume or self.volume_filter or None,
                "equalizer": equalizer or self.equalizer or None,
                "karaoke": karaoke or self.karaoke or None,
                "timescale": timescale or self.timescale or None,
                "tremolo": tremolo or self.tremolo or None,
                "vibrato": vibrato or self.vibrato or None,
                "rotation": rotation or self.rotation or None,
                "distortion": distortion or self.distortion or None,
                "low_pass": low_pass or self.low_pass or None,
                "channel_mix": channel_mix or self.channel_mix or None,
                "echo": echo or self.echo or None,
            }
        if not volume:
            kwargs.pop("volume", None)
        position = await self.fetch_position()
        if self.timescale.changed:
            position = self.timescale.reverse_position(position)
        payload = {
            "filters": self.node.get_filter_payload(
                player=self,
                reset_no_set=reset_not_set,
                **kwargs,
            ),
            "position": int(position),
        }
        await self.node.patch_session_player(self.guild.id, payload=payload)
        kwargs.pop("reset_not_set", None)
        kwargs.pop("requester", None)
        self.node.dispatch_event(FiltersAppliedEvent(player=self, requester=requester, node=self.node, **kwargs))

    async def _process_filters_reset_not_set(
        self, channel_mix, distortion, echo, equalizer, karaoke, low_pass, rotation, timescale, tremolo, vibrato, volume
    ):
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
        if not equalizer:
            self._equalizer = self._equalizer.default()
        if not karaoke:
            self._karaoke = self._karaoke.default()
        if not timescale:
            self._timescale = self._timescale.default()
        if not tremolo:
            self._tremolo = self._tremolo.default()
        if not vibrato:
            self._vibrato = self._vibrato.default()
        if not rotation:
            self._rotation = self._rotation.default()
        if not distortion:
            self._distortion = self._distortion.default()
        if not low_pass:
            self._low_pass = self._low_pass.default()
        if not channel_mix:
            self._channel_mix = self._channel_mix.default()
        if not echo:
            self._echo = self._echo.default()
        return kwargs

    async def _set_filter_variables(
        self,
        changed,
        channel_mix,
        distortion,
        echo,
        equalizer,
        karaoke,
        low_pass,
        rotation,
        timescale,
        tremolo,
        vibrato,
        volume,
    ):
        if volume and self.node.has_filter("volume"):
            self._volume = volume
        if equalizer and self.node.has_filter("equalizer"):
            self._equalizer = equalizer
            changed = True
        if karaoke and self.node.has_filter("karaoke"):
            self._karaoke = karaoke
            changed = True
        if timescale and self.node.has_filter("timescale"):
            self._timescale = timescale
            changed = True
        if tremolo and self.node.has_filter("tremolo"):
            self._tremolo = tremolo
            changed = True
        if vibrato and self.node.has_filter("vibrato"):
            self._vibrato = vibrato
            changed = True
        if rotation and self.node.has_filter("rotation"):
            self._rotation = rotation
            changed = True
        if distortion and self.node.has_filter("distortion"):
            self._distortion = distortion
            changed = True
        if low_pass and self.node.has_filter("low_pass"):
            self._low_pass = low_pass
            changed = True
        if channel_mix and self.node.has_filter("channel_mix"):
            self._channel_mix = channel_mix
            changed = True
        if echo and self.node.has_filter("echo"):
            self._echo = echo
            changed = True
        return changed

    @staticmethod
    async def _process_skip_segments() -> list[str]:
        return SegmentCategory.get_category_list_value()

    async def draw_time(self) -> str:
        paused = self.paused
        position = await self.fetch_position()
        duration = None if not self.current else await self.current.duration()
        dur = duration or position
        sections = 12
        loc_time = round((position / dur if dur != 0 else position) * sections)
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
        self,
        embed: bool = True,
        messageable: Messageable | DISCORD_INTERACTION_TYPE = None,
        progress: bool = True,
        show_help: bool = False,
    ) -> dict[str, discord.Embed | str | discord.File]:  # sourcery skip: use-fstring-for-formatting
        if not embed:
            return {"content": ""}
        queue_list = ""
        if not progress:
            arrow = ""
            pos = ""
        else:
            arrow = await self.draw_time()
            position = await self.fetch_position()
            pos = format_time_dd_hh_mm_ss(position)
        current = self.current
        dur = (
            None
            if current is None
            else _("LIVE")
            if await current.stream()
            else format_time_dd_hh_mm_ss(await current.duration())
        )
        if self.timescale.changed:
            dur += "*"
            pos += "*"
        current_track_description = await current.get_track_display_name(with_url=True) if current else None
        next_track_description = (
            await self.next_track.get_track_display_name(with_url=True) if self.next_track else None
        )
        previous_track_description = (
            await self.last_track.get_track_display_name(with_url=True) if self.last_track else None
        )
        queue_list = await self._process_np_embed_initial_description(
            arrow, current, current_track_description, dur, pos, queue_list, progress
        )
        page = await self.node.node_manager.client.construct_embed(
            title=discord.utils.escape_markdown(
                _("Now Playing in {server_name_variable_do_not_translate}").format(
                    server_name_variable_do_not_translate=self.guild.name
                )
            ),
            description=queue_list,
            messageable=messageable,
        )
        if current and (url := await current.artworkUrl()):
            page.set_thumbnail(url=url)

        await self._process_np_embed_prev_track(page, previous_track_description)
        await self._process_np_embed_next_track(next_track_description, page)

        await self._process_now_playing_embed_footer(page, show_help)
        kwargs = {"embed": page}
        if current and (artwork := await current.get_embedded_artwork()):
            kwargs["file"] = artwork
        return kwargs

    @staticmethod
    async def _process_np_embed_initial_description(
        arrow, current, current_track_description, dur, pos, queue_list, progress
    ):
        if current is None:
            return queue_list
        # sourcery skip: use-fstring-for-formatting
        if await current.stream():
            queue_list += "**{}:**\n".format(discord.utils.escape_markdown(_("Currently livestreaming")))
        else:
            queue_list += _("Playing: ")
        queue_list += f"{current_track_description}\n"
        queue_list += "{translation}: **{current}**".format(
            current=current.requester.mention, translation=discord.utils.escape_markdown(_("Requester"))
        )
        if progress:
            queue_list += f"\n\n{arrow}`{pos}`/`{dur}`\n\n"
        else:
            queue_list += "\n{dur}\n\n\n".format(
                dur=_("Duration: {track_duration_variable_do_not_translate}").format(
                    track_duration_variable_do_not_translate=f"`{dur}`"
                )
            )
        return queue_list

    async def _process_np_embed_prev_track(self, page, previous_track_description):
        if previous_track_description:
            val = f"{previous_track_description}\n"
            val += "{translation}: `{duration}`\n".format(
                duration=shorten_string(max_length=100, string=_("LIVE"))
                if await self.last_track.stream()
                else (
                    format_time_dd_hh_mm_ss(await self.last_track.duration()) + ("*" if self.timescale.changed else "")
                ),
                translation=discord.utils.escape_markdown(_("Duration")),
            )
            if rq := self.last_track.requester:
                val += "{translation}: **{rq}**\n\n".format(
                    rq=rq.mention, translation=discord.utils.escape_markdown(_("Requester"))
                )
            page.add_field(name=_("Previous Track"), value=val)

    async def _process_np_embed_next_track(self, next_track_description, page):
        if next_track_description:
            val = f"{next_track_description}\n"
            val += "{translation}: `{duration}`\n".format(
                duration=_("LIVE")
                if await self.next_track.stream()
                else format_time_dd_hh_mm_ss(await self.next_track.duration())
                + ("*" if self.timescale.changed else ""),
                translation=discord.utils.escape_markdown(_("Duration")),
            )
            if rq := self.next_track.requester:
                val += "{translation}: **{rq}**\n\n".format(
                    rq=rq.mention, translation=discord.utils.escape_markdown(_("Requester"))
                )
            page.add_field(name=_("Next Track"), value=val)

    async def _process_now_playing_embed_footer(self, page, show_help):
        queue_dur = await self.queue_duration()
        queue_total_duration = format_time_string(queue_dur // 1000)
        if self.timescale.changed:
            queue_total_duration += "*"
        track_count = self.queue.qsize()
        match track_count:
            case 1:
                text = _("1 track, {queue_total_duration_variable_do_not_translate} remaining\n").format(
                    queue_total_duration_variable_do_not_translate=queue_total_duration
                )
            case 0:
                text = _("0 tracks, {queue_total_duration_variable_do_not_translate} remaining\n").format(
                    queue_total_duration_variable_do_not_translate=queue_total_duration
                )
            case __:
                text = _(
                    "{track_count_variable_do_not_translate} tracks, {queue_total_duration_variable_do_not_translate} remaining\n"
                ).format(
                    track_count_variable_do_not_translate=track_count,
                    queue_total_duration_variable_do_not_translate=queue_total_duration,
                )
        autoplay_emoji, repeat_emoji, filter_emoji = await self._process_embed_emojis()
        text += "{translation}: {repeat_emoji}".format(repeat_emoji=repeat_emoji, translation=_("Repeating"))
        text += "{space}{translation}: {autoplay_emoji}".format(
            space=(" | " if text else ""), autoplay_emoji=autoplay_emoji, translation=_("Auto Play")
        )
        text += "{space}{translation}: {filter_emoji}".format(
            space=(" | " if text else ""), filter_emoji=filter_emoji, translation=_("Effects")
        )
        text += "{space}{translation}: {volume}".format(
            space=(" | " if text else ""),
            volume=_("{volume_variable_do_not_translate}%").format(volume_variable_do_not_translate=self.volume),
            translation=_("Volume"),
        )
        if show_help:
            text += _(
                "\n\nYou can search specific services by using the following prefixes:\n"
                "{deezer_service_variable_do_not_translate}  - Deezer\n"
                "{spotify_service_variable_do_not_translate}  - Spotify\n"
                "{apple_music_service_variable_do_not_translate}  - Apple Music\n"
                "{youtube_music_service_variable_do_not_translate} - YouTube Music\n"
                "{youtube_service_variable_do_not_translate}  - YouTube\n"
                "{soundcloud_service_variable_do_not_translate}  - SoundCloud\n"
                "{yandex_music_service_variable_do_not_translate}  - Yandex Music\n"
                "Example: {example_variable_do_not_translate}.\n\n"
                "If no prefix is used I will default to {fallback_service_variable_do_not_translate}\n"
            ).format(
                fallback_service_variable_do_not_translate=f"`{DEFAULT_SEARCH_SOURCE}:`",
                deezer_service_variable_do_not_translate="'dzsearch:' ",
                spotify_service_variable_do_not_translate="'spsearch:' ",
                apple_music_service_variable_do_not_translate="'amsearch:' ",
                youtube_music_service_variable_do_not_translate="'ytmsearch:'",
                youtube_service_variable_do_not_translate="'ytsearch:' ",
                soundcloud_service_variable_do_not_translate="'scsearch:' ",
                yandex_music_service_variable_do_not_translate="'ymsearch:' ",
                example_variable_do_not_translate=f"'{DEFAULT_SEARCH_SOURCE}:Hello Adele'",
            )
        page.set_footer(text=text)

    async def _process_embed_emojis(self):
        if not await self.is_repeating():
            repeat_emoji = "\N{CROSS MARK}"
        elif await self.config.fetch_repeat_queue():
            repeat_emoji = "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}"
        else:
            repeat_emoji = "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS WITH CIRCLED ONE OVERLAY}"
        autoplay_emoji = "\N{WHITE HEAVY CHECK MARK}" if await self.autoplay_enabled() else "\N{CROSS MARK}"
        filter_emoji = "\N{WHITE HEAVY CHECK MARK}" if self.has_effects else "\N{CROSS MARK}"
        return autoplay_emoji, repeat_emoji, filter_emoji

    async def get_queue_page(
        self,
        page_index: int,
        per_page: int,
        total_pages: int,
        embed: bool = True,
        messageable: Messageable | DISCORD_INTERACTION_TYPE = None,
        history: bool = False,
    ) -> dict[str, discord.Embed | str | discord.File]:
        if not embed:
            return {"content": ""}
        queue = self.history if history else self.queue
        queue_list = ""
        start_index = page_index * per_page
        end_index = start_index + per_page
        tracks = list(islice(queue.raw_queue, start_index, end_index))
        arrow = await self.draw_time()
        position = await self.fetch_position()
        pos = format_time_dd_hh_mm_ss(position)
        current = self.current
        dur = (
            None
            if current is None
            else _("LIVE")
            if await current.stream()
            else format_time_dd_hh_mm_ss(await current.duration())
        )
        if self.timescale.changed:
            pos += "*"
            dur += "*"
        queue_list = await self._process_queue_embed_initial_description(arrow, current, dur, pos, queue_list)
        queue_list = await self._process_queue_embed_maybe_shuffle(history, queue_list, tracks)
        queue_list = await self._process_queue_tracks(history, queue_list, start_index, tracks)

        if history:
            title = discord.utils.escape_markdown(
                _("Recently Played for {server_name_variable_do_not_translate}").format(
                    server_name_variable_do_not_translate=self.guild.name
                )
            )
        else:
            title = discord.utils.escape_markdown(
                _("Queue for {server_name_variable_do_not_translate}").format(
                    server_name_variable_do_not_translate=self.guild.name
                )
            )

        page = await self.node.node_manager.client.construct_embed(
            title=title,
            description=queue_list,
            messageable=messageable,
        )
        if current and (url := await current.artworkUrl()):
            page.set_thumbnail(url=url)
        queue_dur = await self.queue_duration(history=history)
        queue_total_duration = format_time_string(queue_dur // 1000)
        if self.timescale.changed:
            queue_total_duration += "*"
        await self._process_queue_embed_footer(page, page_index, queue, queue_total_duration, total_pages)
        kwargs = {"embed": page}
        if current and (artwork := await current.get_embedded_artwork()):
            kwargs["file"] = artwork
        return kwargs

    @staticmethod
    async def _process_queue_embed_initial_description(arrow, current, dur, pos, queue_list):
        if current is None:
            return queue_list
        current_track_description = await current.get_track_display_name(with_url=True)
        if await current.stream():
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
        return queue_list

    async def _process_queue_embed_maybe_shuffle(self, history, queue_list, tracks):
        if (
            len(tracks)
            and not history
            and (await self.player_manager.client.player_config_manager.get_auto_shuffle(self.guild.id)) is True
        ):
            queue_list += "__{translation}__\n\n".format(
                translation=discord.utils.escape_markdown(
                    _("Queue order will change every time a track is added due to auto shuffle being enabled.")
                )
            )
        return queue_list

    async def _process_queue_embed_footer(self, page, page_index, queue, queue_total_duration, total_pages):
        track_number = queue.qsize()

        match track_number:
            case 1:
                text = _("Page 1 / 1 | 1 track, {queue_total_duration_variable_do_not_translate} remaining\n").format(
                    queue_total_duration_variable_do_not_translate=queue_total_duration,
                )
            case 0:
                text = _("Page 1 / 1 | 0 tracks, {queue_total_duration_variable_do_not_translate} remaining\n").format(
                    queue_total_duration_variable_do_not_translate=queue_total_duration,
                )
            case __:
                text = _(
                    "Page {current_page_variable_do_not_translate} / {total_pages_variable_do_not_translate} | {track_number_variable_do_not_translate} tracks, {queue_total_duration_variable_do_not_translate} remaining\n"
                ).format(
                    current_page_variable_do_not_translate=page_index + 1,
                    total_pages_variable_do_not_translate=total_pages,
                    track_number_variable_do_not_translate=track_number,
                    queue_total_duration_variable_do_not_translate=queue_total_duration,
                )

        autoplay_emoji, repeat_emoji, filter_emoji = await self._process_embed_emojis()
        text += "{translation}: {repeat_emoji}".format(repeat_emoji=repeat_emoji, translation=_("Repeating"))
        text += "{space}{translation}: {autoplay_emoji}".format(
            space=(" | " if text else ""), autoplay_emoji=autoplay_emoji, translation=_("Auto Play")
        )
        text += "{space}{translation}: {filter_emoji}".format(
            space=(" | " if text else ""), filter_emoji=filter_emoji, translation=_("Effects")
        )
        text += "{space}{translation}: {volume}".format(
            space=(" | " if text else ""),
            volume=_("{volume_variable_do_not_translate}%").format(volume_variable_do_not_translate=self.volume),
            translation=_("Volume"),
        )
        page.set_footer(text=text)

    async def _process_queue_tracks(self, history, queue_list, start_index, tracks):
        if tracks:
            padding = len(str(start_index + len(tracks)))
            for track_idx, track in enumerate(tracks, start=start_index + 1):
                queue_list = await self._process_single_queue_track(history, padding, queue_list, track, track_idx)
        return queue_list

    @staticmethod
    async def _process_single_queue_track(history, padding, queue_list, track, track_idx):
        track_description = await track.get_track_display_name(max_length=50, with_url=True)
        diff = padding - len(str(track_idx))
        queue_list += f"`{track_idx}.{' ' * diff}` {track_description}"
        if history and track.requester:
            queue_list += f" - **{track.requester.mention}**"
        queue_list += "\n"
        return queue_list

    async def queue_duration(self, history: bool = False) -> int:
        queue = self.history if history else self.queue
        dur = [await track.duration() for track in queue.raw_queue if not await track.stream()]
        queue_dur = sum(dur)
        if queue.empty():
            queue_dur = 0
        if history:
            return queue_dur
        try:
            remain = 0 if await self.current.stream() else (await self.current.duration() - await self.fetch_position())
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
        queue_number: int,
        requester: discord.Member,
        new_index: int = None,
    ) -> Track | None:
        if self.queue.empty():
            return None
        track = await self.queue.get(queue_number)
        await self.queue.put([track], new_index)
        self.next_track = None if self.queue.empty() else self.queue.raw_queue.popleft()
        self.node.dispatch_event(
            QueueTrackPositionChangedEvent(
                before=queue_number, after=new_index, track=track, player=self, requester=requester
            )
        )
        return track

    async def maybe_shuffle_queue(self, requester: int) -> None:
        if (await self.player_manager.client.player_config_manager.get_auto_shuffle(self.guild.id)) is False:
            return
        await self.shuffle_queue(requester)

    async def shuffle_queue(self, requester: int) -> None:
        self.node.dispatch_event(QueueShuffledEvent(player=self, requester=self.guild.get_member(requester)))
        await self.queue.shuffle()
        self.next_track = None if self.queue.empty() else self.queue.raw_queue.popleft()

    async def set_autoplay_playlist(self, playlist: int | Playlist) -> None:
        if isinstance(playlist, int):
            await self.config.update_auto_play_playlist_id(playlist)
        else:
            await self.config.update_auto_play_playlist_id(playlist.id)

    async def get_auto_playlist(self) -> Playlist | None:
        try:
            return await self.player_manager.client.playlist_db_manager.get_playlist_by_id(
                await self.config.fetch_auto_play_playlist_id()
            )
        except EntryNotFoundException:
            return None

    async def set_autoplay(self, autoplay: bool) -> None:
        await self.config.update_auto_play(autoplay)

    async def to_dict(self) -> dict:
        """
        Returns a dict representation of the player.
        """
        data = await self.config.fetch_all()
        position = await self.position()
        if self.timescale.changed:
            position = self.timescale.reverse_position(position)
        return {
            "id": int(self.guild.id),
            "channel_id": self.channel.id,
            "current": await self.current.to_dict() if self.current else None,
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
            "position": position,
            "playing": self.is_active,
            "queue": [] if self.queue.empty() else [await t.to_dict() for t in self.queue.raw_queue],
            "history": [] if self.history.empty() else [await t.to_dict() for t in self.history.raw_queue],
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
                "last_track": await self.last_track.to_dict() if self.last_track else None,
                "next_track": await self.next_track.to_dict() if self.next_track else None,
                "was_alone_paused": self._was_alone_paused,
            },
        }

    async def save(self) -> None:
        if self.is_active:
            await self.node.node_manager.client.player_state_db_manager.save_player(await self.to_dict())

    async def restore(self, player: PlayerState, requester: discord.User | discord.Member) -> None:
        # sourcery no-metrics
        if self._restored is True:
            return
        self._was_alone_paused = player.extras.get("was_alone_paused", False)
        current, last_track, next_track, restoring_session = await self._process_restore_current_tracks(player)
        self.last_track = last_track
        self.next_track = next_track
        self.current = None
        self.paused = player.paused
        await self._process_restore_autoplaylist(player)
        self._last_position = player.position
        history, queue = await self._process_restore_queues(player)
        self.queue.raw_queue = collections.deque(queue)
        self.queue.raw_b64s = [t.encoded for t in queue if t.encoded]
        self.history.raw_queue = collections.deque(history)
        self.history.raw_b64s = [t.encoded for t in history]
        self._effect_enabled = player.effect_enabled
        await self._process_restore_filters(player)
        self.current = current
        if self.current is None and ENABLE_NODE_RESUMING:
            self.stopped = (not await self.autoplay_enabled()) and not self.queue.qsize()
        else:
            self.stopped = (not await self.autoplay_enabled()) and not self.queue.qsize() and not self.current
        await self.change_to_best_node(ops=False, skip_position_fetch=True)
        await self._process_restore_rest_call(restoring_session)
        self.last_track = last_track
        self._restored = True
        await self.player_manager.client.player_state_db_manager.delete_player(guild_id=self.guild.id)
        self.node.dispatch_event(PlayerRestoredEvent(self, requester))
        self._logger.verbose("Player restored - %s", self)

    async def _process_restore_autoplaylist(self, player: PlayerState) -> None:
        if self._autoplay_playlist is None:
            try:
                self._autoplay_playlist = (
                    await self.player_manager.client.playlist_db_manager.get_playlist_by_id(
                        player.auto_play_playlist_id
                    )
                    if player.auto_play_playlist_id
                    else None
                )
            except EntryNotFoundException:
                # Set playlist no longer exists, reset to the bundled playlist - stop player crashing on creation
                await self.set_autoplay_playlist(1)

    async def _process_restore_rest_call(self, restoring_session: bool) -> None:
        payload = {}
        if self.paused:
            payload["paused"] = self.paused
        if self.current and not restoring_session:
            payload |= {"encodedTrack": self.current.encoded, "position": int(self._last_position)}
            self._last_update = time.time() * 1000
        if self.stopped and not restoring_session:
            payload |= {"encodedTrack": None}
            self._last_update = time.time() * 1000
        if self.has_effects:
            payload["filters"] = self.node.get_filter_payload(
                player=self,
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
        if self.volume_filter:
            payload["volume"] = self.volume
        if payload:
            await self.node.patch_session_player(guild_id=self.guild.id, payload=payload)

    async def _process_restore_queues(self, player):
        queue = await self._generate_queue(player.queue)
        history = await self._generate_queue(player.history)
        return history, queue

    async def _generate_queue(self, raw_queue):
        queue_raw = (
            [
                {
                    "data": t.pop("encoded", None),
                    "query": t.pop("query"),
                    "full_track_data": t.pop("full_track_data", None),
                    "lazy": True,
                    **t.pop("extra", {}),
                    **t,
                }
                for t in raw_queue
            ]
            if raw_queue
            else []
        )
        encoded_list = [track["data"] for track in queue_raw if track["full_track_data"] is None]
        full_track_data = [track["full_track_data"] for track in queue_raw if track["full_track_data"] is not None]

        if encoded_list:
            track_objects = await self.node.post_decodetracks(encoded_list)
            track_objects_mapping = (
                {track.encoded: track for track in track_objects} if isinstance(track_objects, list) else {}
            )
        else:
            track_objects_mapping = {}
        queue = []
        if track_objects_mapping:
            for i, track in enumerate(queue_raw, start=0):
                query = await Query.from_string(track.pop("query"))
                lazy = track.pop("lazy")
                if track["data"] is not None and track["data"] in track_objects_mapping:
                    data = track_objects_mapping[track.pop("data")]
                else:
                    data = track.pop("data")
                new_track = await Track.build_track(
                    node=self.node, query=query, lazy=lazy, data=data, **track, player_instance=self
                )
                if new_track:
                    queue.append(new_track)
        if (not track_objects_mapping) or full_track_data:
            queue = (
                [
                    (
                        await Track.build_track(
                            node=self.node,
                            data=t_full or t_data,
                            query=await Query.from_string(t.pop("query"), lazy=True),
                            lazy=t.pop("lazy") and not t_full,
                            **t,
                            player_instance=self,
                        )
                    )
                    for t in queue_raw
                    if [(t_full := t.pop("full_track_list", None)), (t_data := t.pop("data", None)), False]
                    and t_data not in track_objects_mapping
                    and t_full
                    or t_data
                ]
                if queue_raw
                else []
            )
        return queue

    async def _process_restore_current_tracks(self, player):
        restoring_session = False
        if player.current:
            player_api = await self.node.fetch_session_player(guild_id=self.guild.id)
            if isinstance(player_api, LavalinkPlayer):
                if player_api.track:
                    current = await Track.build_track(
                        node=self.node,
                        data=player_api.track,
                        **player.current.pop("extra"),
                        **player.current,
                        player_instance=self,
                    )
                    restoring_session = True
                else:
                    current = None
            elif full_track := player.current.pop("full_track_data", None):
                current = await Track.build_track(
                    node=self.node,
                    data=from_dict(data_class=APITrack, data=full_track),
                    lazy=True,
                    query=await Query.from_string(player.current.pop("query")),
                    **player.current.pop("extra"),
                    **player.current,
                    player_instance=self,
                )
            else:
                current = await Track.build_track(
                    node=self.node,
                    data=player.current.pop("encoded", None),
                    lazy=True,
                    query=await Query.from_string(player.current.pop("query")),
                    **player.current.pop("extra"),
                    **player.current,
                    player_instance=self,
                )
        else:
            current = None

        if n_track := player.extras.get("next_track", {}):
            if full_track := n_track.pop("full_track_data", None):
                next_track = await Track.build_track(
                    node=self.node,
                    data=from_dict(data_class=APITrack, data=full_track),
                    lazy=True,
                    query=await Query.from_string(n_track.pop("query")),
                    **n_track.pop("extra"),
                    **n_track,
                    player_instance=self,
                )
            else:
                next_track = await Track.build_track(
                    node=self.node,
                    data=n_track.pop("encoded", None),
                    lazy=True,
                    query=await Query.from_string(n_track.pop("query")),
                    **n_track.pop("extra"),
                    **n_track,
                    player_instance=self,
                )
        else:
            next_track = None

        if l_track := player.extras.get("last_track", {}):
            if full_track := l_track.pop("full_track_data", None):
                last_track = await Track.build_track(
                    node=self.node,
                    data=from_dict(data_class=APITrack, data=full_track),
                    lazy=True,
                    query=await Query.from_string(l_track.pop("query")),
                    **l_track.pop("extra"),
                    **l_track,
                    player_instance=self,
                )
            else:
                last_track = await Track.build_track(
                    node=self.node,
                    data=l_track.pop("encoded", None),
                    lazy=True,
                    query=await Query.from_string(l_track.pop("query")),
                    **l_track.pop("extra"),
                    **l_track,
                    player_instance=self,
                )
        else:
            last_track = None
        return current, last_track, next_track, restoring_session

    async def _process_restore_filters(self, player):
        effects = player.effects
        if (v := effects.get("volume", None)) and (f := Volume.from_dict(v)):
            self._volume = f
        if (
            self.node.has_filter("equalizer")
            and (v := effects.get("equalizer", None))
            and (f := Equalizer.from_dict(v))
        ):
            self._equalizer = f
        if self.node.has_filter("karaoke") and (v := effects.get("karaoke", None)) and (f := Karaoke.from_dict(v)):
            self._karaoke = f
        if (
            self.node.has_filter("timescale")
            and (v := effects.get("timescale", None))
            and (f := Timescale.from_dict(v))
        ):
            self._timescale = f
        if self.node.has_filter("tremolo") and (v := effects.get("tremolo", None)) and (f := Tremolo.from_dict(v)):
            self._tremolo = f
        if self.node.has_filter("vibrato") and (v := effects.get("vibrato", None)) and (f := Vibrato.from_dict(v)):
            self._vibrato = f
        if self.node.has_filter("rotation") and (v := effects.get("rotation", None)) and (f := Rotation.from_dict(v)):
            self._rotation = f
        if (
            self.node.has_filter("distortion")
            and (v := effects.get("distortion", None))
            and (f := Distortion.from_dict(v))
        ):
            self._distortion = f
        if self.node.has_filter("lowPass") and (v := effects.get("low_pass", None)) and (f := LowPass.from_dict(v)):
            self._low_pass = f
        if (
            self.node.has_filter("channelMix")
            and (v := effects.get("channel_mix", None))
            and (f := ChannelMix.from_dict(v))
        ):
            self._channel_mix = f
        if self.node.has_filter("echo") and (v := effects.get("echo", None)) and (f := Echo.from_dict(v)):
            self._echo = f

    async def fetch_node_player(self) -> LavalinkPlayer | HTTPException:
        return await self.node.fetch_session_player(self.guild.id)

    async def add_sponsorblock_categories(self, *categories: str) -> None:
        """
        Add sponsorblock categories to the player.
        Parameters
        ----------
        categories: :class:`str`
            The categories to add.
        """
        if not self.node.supports_sponsorblock:
            return
        if not categories and not (categories := await self._process_skip_segments()):
            return
        await self.node.put_session_player_sponsorblock_categories(guild_id=self.guild.id, categories=categories)

    async def remove_sponsorblock_categories(self) -> None:
        """
        Remove sponsorblock categories from the player.
        """
        if not self.node.supports_sponsorblock:
            return
        await self.node.delete_session_player_sponsorblock_categories(guild_id=self.guild.id)

    async def get_sponsorblock_categories(self) -> list[str]:
        """
        Get the sponsorblock categories for the player.
        Returns
        -------
        list[:class:`str`]
            The categories for the player.
        """
        if not self.node.supports_sponsorblock:
            return []
        categories = await self.node.get_session_player_sponsorblock_categories(guild_id=self.guild.id)
        return categories if isinstance(categories, list) else []
