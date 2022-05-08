from __future__ import annotations

import asyncio
import collections
import contextlib
import datetime
import itertools
import random
import time
from typing import TYPE_CHECKING, Any, Coroutine, Literal

import discord
from discord import VoiceProtocol
from discord.abc import Messageable

from pylav._logging import getLogger
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
from pylav.exceptions import NoNodeWithRequestFunctionalityAvailable, TrackNotFound
from pylav.filters import ChannelMix, Distortion, Equalizer, Karaoke, LowPass, Rotation, Timescale, Vibrato, Volume
from pylav.filters.tremolo import Tremolo
from pylav.query import Query
from pylav.sql.models import PlayerModel, PlayerStateModel, PlaylistModel
from pylav.tracks import Track
from pylav.types import BotT
from pylav.utils import AsyncIter, PlayerQueue, SegmentCategory, TrackHistoryQueue, format_time

if TYPE_CHECKING:
    from pylav import Client
    from pylav.node import Node
    from pylav.player_manager import PlayerManager
    from pylav.radio import RadioBrowser

LOGGER = getLogger("red.PyLink.Player")


class Player(VoiceProtocol):
    _config: PlayerModel
    _global_config: PlayerModel
    _lavalink: Client

    def __init__(
        self,
        client: BotT,
        channel: discord.VoiceChannel,
        *,
        node: Node = None,
    ):
        self.bot = self.client = client
        self.guild_id = str(channel.guild.id)
        self._channel = None
        self.channel = channel
        self.channel_id = channel.id
        self.node: Node = node
        self.player_manager: PlayerManager = None  # type: ignore
        self._original_node: Node = None  # type: ignore
        self._voice_state = {}
        self.region = channel.rtc_region
        self._connected = False
        self.connected_at = datetime.datetime.now(tz=datetime.timezone.utc)
        self._text_channel = None
        self._notify_channel = None
        self._forced_vc = None

        self._user_data = {}

        self.paused = False
        self._last_update = 0
        self._last_position = 0
        self.position_timestamp = 0
        self.queue: PlayerQueue[Track] = PlayerQueue()
        self.history: TrackHistoryQueue[Track] = TrackHistoryQueue(maxsize=100)
        self.current: Track | None = None
        self._post_init_completed = False
        self._queue_length = 0
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
        self._low_pass: LowPass = LowPass.default()
        self._channel_mix: ChannelMix = ChannelMix.default()

        self._config = None  # type: ignore
        self._extras = {}

    def __str__(self):
        return f"Player(id={self.guild.id}, channel={self.channel.id})"

    async def post_init(self, node: Node, player_manager: PlayerManager, config: PlayerModel, pylav: Client) -> None:
        if self._post_init_completed:
            return
        self._lavalink = pylav
        self.player_manager = player_manager
        self.node = node
        self._config = config
        self._global_config = player_manager.global_config
        self._extras = config.extras
        self._post_init_completed = True
        await self.set_autoplay_playlist(config.auto_play_playlist_id)
        self._forced_vc = self.guild.get_channel_or_thread(config.forced_channel_id)
        self._text_channel = self.guild.get_channel_or_thread(config.text_channel_id)
        self._notify_channel = self.guild.get_channel_or_thread(config.notify_channel_id)
        self._volume = Volume(config.volume)
        effects = config.effects
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
        if any(
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
            )

        if self.volume_filter.changed:
            await self.node.send(op="volume", guildId=self.guild_id, volume=self.volume)

    @property
    def channel(self) -> discord.VoiceChannel:
        return self._channel

    @channel.setter
    def channel(self, value: discord.VoiceChannel):
        if isinstance(value, discord.VoiceChannel):
            self._channel = value
            self.region = value.rtc_region

    @property
    def config(self) -> PlayerModel:
        return self._config

    @property
    def lavalink(self) -> Client:
        return self._lavalink

    @property
    def radio(self) -> RadioBrowser:
        return self.lavalink.radio_browser

    @property
    def text_channel(self) -> discord.abc.Messageable:
        return self._text_channel

    @text_channel.setter
    def text_channel(self, value: discord.abc.Messageable):
        self._text_channel = value
        self.config.text_channel_id = value.id if value else None

    @property
    def notify_channel(self) -> discord.abc.Messageable:
        return self._notify_channel

    @notify_channel.setter
    def notify_channel(self, value: discord.abc.Messageable):
        self._notify_channel = value
        self.config.notify_channel_id = value.id if value else None

    @property
    def forced_vc(self) -> discord.abc.Messageable:
        return self._forced_vc

    @forced_vc.setter
    def forced_vc(self, value: discord.abc.Messageable):
        self._forced_vc = value
        self.config.forced_channel_id = value.id if value else None

    @property
    def self_deaf(self) -> bool:
        return self._config.self_deaf if self._config else True

    @property
    def is_repeating(self) -> bool:
        """Whether the player is repeating tracks."""
        return self._config.repeat_current or self._config.repeat_queue

    @property
    def autoplay_enabled(self) -> bool:
        """Whether autoplay is enabled."""
        return self._config.auto_play and self._autoplay_playlist is not None

    @property
    def volume(self) -> int:
        """
        The current volume.
        """
        return self._volume.get_int_value()

    @property
    def volume_filter(self) -> Volume:
        """The currently applied Volume filter."""
        return self._volume

    @property
    def equalizer(self) -> Equalizer:
        """The currently applied Equalizer filter."""
        return self._equalizer

    @property
    def karaoke(self) -> Karaoke:
        """The currently applied Karaoke filter."""
        return self._karaoke

    @property
    def timescale(self) -> Timescale:
        """The currently applied Timescale filter."""
        return self._timescale

    @property
    def tremolo(self) -> Tremolo:
        """The currently applied Tremolo filter."""
        return self._tremolo

    @property
    def vibrato(self) -> Vibrato:
        """The currently applied Vibrato filter."""
        return self._vibrato

    @property
    def rotation(self) -> Rotation:
        """The currently applied Rotation filter."""
        return self._rotation

    @property
    def distortion(self) -> Distortion:
        """The currently applied Distortion filter."""
        return self._distortion

    @property
    def low_pass(self) -> LowPass:
        """The currently applied Low Pass filter."""
        return self._low_pass

    @property
    def channel_mix(self) -> ChannelMix:
        """The currently applied Channel Mix filter."""
        return self._channel_mix

    @property
    def has_effects(self):
        return self._effect_enabled

    @property
    def guild(self) -> discord.Guild:
        return self.channel.guild

    @property
    def is_playing(self) -> bool:
        """Returns the player's track state."""
        return self.is_connected and self.current is not None

    @property
    def is_connected(self) -> bool:
        """Returns whether the player is connected to a voice-channel or not."""
        return self.channel_id is not None

    @property
    def is_empty(self) -> bool:
        """Returns whether the player is empty or not."""
        return sum(1 for i in self.channel.members if not i.bot) == 0

    @property
    def position(self) -> float:
        """Returns the position in the track, adjusted for Lavalink's 5-second stats' interval."""
        if not self.is_playing:
            return 0

        if self.paused:
            return min(self._last_position, self.current.duration)

        difference = time.time() * 1000 - self._last_update
        return min(self._last_position + difference, self.current.duration)

    async def change_to_best_node(self, feature: str = None) -> Node | None:
        """
        Returns the best node to play the current track.
        Returns
        -------
        :class:`Node`
        """
        node = self.node.node_manager.find_best_node(region=self.region, feature=feature)
        if feature and not node:
            raise NoNodeWithRequestFunctionalityAvailable(
                f"No node with {feature} functionality available!", feature=feature
            )

        if node != self.node:
            await self.change_node(node)
            return node

    async def change_to_best_node_diff_region(self, feature: str = None) -> Node | None:
        """
        Returns the best node to play the current track in a different region.
        Returns
        -------
        :class:`Node`
        """
        node = self.node.node_manager.find_best_node(not_region=self.region, feature=feature)
        if feature and not node:
            raise NoNodeWithRequestFunctionalityAvailable(
                f"No node with {feature} functionality available!", feature=feature
            )
        if node != self.node:
            await self.change_node(node)
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
        try:
            del self._user_data[key]
        except KeyError:
            pass

    async def on_voice_server_update(self, data: dict) -> None:
        self._voice_state.update({"event": data})

        await self._dispatch_voice_update()

    async def on_voice_state_update(self, data: dict) -> None:
        self._voice_state.update({"sessionId": data["session_id"]})

        self.channel_id = data["channel_id"]

        if not self.channel_id:  # We're disconnecting
            self._voice_state.clear()
            return

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
        track: Union[:class:`AudioTrack`, :class:`dict`]
            The track to add. Accepts either an AudioTrack or
            a dict representing a track returned from Lavalink.
        index: Optional[:class:`int`]
            The index at which to add the track.
            If index is left unspecified, the default behaviour is to append the track. Defaults to `None`.
        query: Optional[:class:`Query`]
            The query that was used to search for the track.
        """

        at = await self._query_to_track(requester, track, query)
        self.queue.put_nowait([at], index=index)
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
        tracks_and_queries: list[Track | dict | str | list[tuple[AudioTrack | dict | str, Query]]]
            A list of tuples containing the track and query.
        requester: :class:`int`
            The ID of the user who requested the tracks.
        index: Optional[:class:`int`]
            The index at which to add the tracks.
        """
        output = []
        is_list = isinstance(tracks_and_queries[0], (list, tuple))
        async for entry in AsyncIter(tracks_and_queries):
            if is_list:
                track, query = entry
                track = await self._query_to_track(requester, track, query)
            else:
                track, query = entry, None
                track = await self._query_to_track(requester, track, query)
            output.append(track)
        self.queue.put_nowait(output, index=index)
        self.node.dispatch_event(TracksRequestedEvent(self, self.guild.get_member(requester), output))

    async def previous(self, requester: discord.Member, bypass_cache: bool = False) -> None:
        if self.history.empty():
            raise TrackNotFound("There are no tracks currently in the player history.")
        track = await self.history.get()
        if track.is_partial:
            await track.search(self, bypass_cache=bypass_cache)
        if self.current:
            self.history.put_nowait([self.current])

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
        if self.current:
            self.current.timestamp = self.position
            self.queue.put_nowait([self.current], 0)

        if await track.query() and not self.node.has_source(await track.requires_capability()):
            self.current = None
            await self.change_to_best_node(await track.requires_capability())

        if track.is_partial:
            try:
                await track.search(self, bypass_cache=bypass_cache)
            except TrackNotFound as exc:
                # If track was passed to `.play()` raise here
                if not track:
                    raise TrackNotFound
                event = TrackExceptionEvent(self, track, exc, self.node)
                self.node.dispatch_event(event)
                await self._handle_event(event)
                return
        self.current = track
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
        """
        Plays the given track.
        Parameters
        ----------
        track: Optional[Union[:class:`AudioTrack`, :class:`dict`]]
            The track to play. If left unspecified, this will default
            to the first track in the queue. Defaults to `None` so plays the next
            song in queue. Accepts either an AudioTrack or a dict representing a track
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
        options = {}
        skip_segments = self._process_skip_segments(skip_segments)
        self._last_update = 0
        self._last_position = 0
        self.position_timestamp = 0
        self.paused = False
        auto_play = False
        if track is not None and isinstance(track, (Track, dict, str, type(None))):
            track = Track(node=self.node, data=track, query=query, skip_segments=skip_segments, requester=requester.id)
        if self.current and self._config.repeat_current:
            await self.add(self.current.requester_id, self.current)
        elif self.current and self._config.repeat_queue:
            await self.add(self.current.requester_id, self.current, index=-1)
        if self.current:
            self.current.timestamp = 0
            self.history.put_nowait([self.current])
        self.current = None
        if not track:
            if self.queue.empty():
                if self.autoplay_enabled:
                    available_tracks = self._autoplay_playlist.tracks
                    if available_tracks:
                        tracks_not_in_history = list(set(available_tracks) - set(self.history.raw_b64s))
                        if tracks_not_in_history:
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
                    else:
                        await self.stop(
                            requester=self.guild.get_member(self.node.node_manager.client.bot.user.id)
                        )  # Also sets current to None.
                        self.history.clear()
                        self.node.dispatch_event(QueueEndEvent(self))
                        return
                else:
                    await self.stop(
                        requester=self.guild.get_member(self.node.node_manager.client.bot.user.id)
                    )  # Also sets current to None.
                    self.history.clear()
                    self.node.dispatch_event(QueueEndEvent(self))
                    return
            else:
                if await self.player_manager.client.player_config_manager.get_shuffle(self.guild.id):
                    await self.shuffle_queue(requester=self.client.user)
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
                # If track was passed to `.play()` raise here
                if not track:
                    raise TrackNotFound
                # Otherwise dispatch Track Exception Event
                event = TrackExceptionEvent(self, track, exc, self.node)
                self.node.dispatch_event(event)
                await self._handle_event(event)
                return
        if self.node.supports_sponsorblock:
            options["skipSegments"] = skip_segments or track.skip_segments
        if start_time is not None:
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
        await self.node.send(op="play", guildId=self.guild_id, track=track.track, **options)
        if auto_play:
            self.node.dispatch_event(TrackAutoPlayEvent(player=self, track=track))

    async def resume(self, requester: discord.Member = None):
        options = {}
        self._last_update = 0
        self._last_position = 0
        if self.node.supports_sponsorblock:
            options["skipSegments"] = self.current.skip_segments if self.current else []
        options["startTime"] = self.current.last_known_position if self.current else self.position
        options["noReplace"] = False
        await self.node.send(op="play", guildId=self.guild_id, track=self.current.track, **options)
        self.node.dispatch_event(PlayerResumedEvent(player=self, requester=requester or self.client.user.id))

    async def stop(self, requester: discord.Member) -> None:
        """Stops the player."""
        await self.node.send(op="stop", guildId=self.guild_id)
        self.node.dispatch_event(PlayerStoppedEvent(self, requester))
        self.current = None

    async def skip(self, requester: discord.Member) -> None:
        """Plays the next track in the queue, if any."""
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
        current_after = current_before = self._config.repeat_current
        queue_after = queue_before = self._config.repeat_queue

        if op_type == "disable":
            queue_after = self._config.repeat_queue = False
            current_after = self._config.repeat_current = False
        elif op_type == "current":
            self._config.repeat_current = current_after = repeat
            self._config.repeat_queue = False
        elif op_type == "queue":
            self._config.repeat_queue = queue_after = repeat
            self._config.repeat_current = False
        else:
            raise ValueError(f"op_type must be either 'current' or 'queue' or `disable` not `{op_type}`")
        await self._config.save()
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
            shuffle = False
        self._config.shuffle = shuffle
        await self._config.save()

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
        max_volume = min(
            await self._config.fetch_max_volume(), await self.player_manager.global_config.fetch_max_volume()
        )
        volume = max(min(vol, max_volume), 0)
        if volume == self.volume:
            return
        self._config.volume = volume
        self._volume = Volume(volume)
        await self.node.send(op="volume", guildId=self.guild_id, volume=self.volume)
        await self._config.save()
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
            position = max(min(position, self.current.duration), 0)
            self.node.dispatch_event(
                TrackSeekEvent(self, requester, self.current, before=self.position, after=position)
            )
            await self.node.send(op="seek", guildId=self.guild_id, position=position)

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
            await self.next()
        elif isinstance(event, TrackExceptionEvent):
            await self.next()

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
        if self.current:
            self.current.last_known_position = self._last_position

        event = PlayerUpdateEvent(self, self._last_position, self.position_timestamp)
        self.node.dispatch_event(event)

    async def change_node(self, node: Node) -> None:
        """
        Changes the player's node
        Parameters
        ----------
        node: :class:`Node`
            The node the player is changed to.
        """
        if node.identifier == self.node.identifier:
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
            channel=self.channel, self_mute=self_mute, self_deaf=self.self_deaf if self._config else self_deaf
        )
        self._connected = True
        LOGGER.info("[Player-%s] Connected to voice channel", self.channel.guild.id)

    async def disconnect(self, *, force: bool = False, requester: discord.Member | None) -> None:
        try:
            LOGGER.info("[Player-%s] Disconnected from voice channel", self.channel.guild.id)
            self.node.dispatch_event(PlayerDisconnectedEvent(self, requester))
            await self.guild.change_voice_state(channel=None)
            self._connected = False
            await self._config.save()
        finally:
            self.queue.clear()
            self.history.clear()
            with contextlib.suppress(ValueError):
                await self.player_manager.remove(self.channel.guild.id)
            await self.node.send(op="destroy", guildId=self.guild_id)
            self.cleanup()

    async def move_to(
        self,
        requester: discord.Member,
        channel: discord.VoiceChannel,
        self_mute: bool = False,
        self_deaf: bool = True,
    ) -> discord.VoiceChannel | None:
        """|coro|
        Moves the player to a different voice channel.
        Parameters
        -----------
        channel: :class:`discord.VoiceChannel`
            The channel to move to. Must be a voice channel.
        self_mute: :class:`bool`
            Indicates if the player should be self-muted on move.
        self_deaf: :class:`bool`
            Indicates if the player should be self-deafened on move.
        requester: :class:`discord.Member`
            The member requesting to move the player.
        """
        if self._config and self.forced_vc and channel.id != self.forced_vc.id:
            channel = self.forced_vc
            LOGGER.debug(
                "[Player-%s] Player has a forced VC enabled replacing channel arg with it", self.channel.guild.id
            )
        if channel == self.channel:
            return
        old_channel = self.channel
        LOGGER.info(
            "[Player-%s] Moving from %s to voice channel: %s", self.channel.guild.id, self.channel.id, channel.id
        )
        self.channel = channel
        self._config.self_deaf = self_deaf
        await self.guild.change_voice_state(channel=self.channel, self_mute=self_mute, self_deaf=self_deaf)
        self._connected = True
        self.node.dispatch_event(PlayerMovedEvent(self, requester, old_channel, self.channel))
        await self._config.save()
        return channel

    async def self_deafen(self, toggle: bool) -> None:
        """|coro|
        Deafens the player.
        Parameters
        -----------
        toggle: :class:`bool`
            Indicates if the player should be deafened.
        """

        self._config.self_deaf = toggle
        await self.guild.change_voice_state(self_deaf=toggle, channel=self.channel)
        await self._config.save()

    async def set_volume_filter(self, requester: discord.Member, volume: Volume) -> None:
        """
        Sets the volume of Lavalink.
        Parameters
        ----------
        volume : Volume
            Volume to set
        requester : discord.Member
        """
        max_volume = min(
            await self._config.fetch_max_volume(), await self.player_manager.global_config.fetch_max_volume()
        )
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
        reset_not_set: bool = False,
    ):
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
            }
            if not volume:
                kwargs.pop("volume", None)
            await self.node.filters(guild_id=self.channel.guild.id, **kwargs)
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
            }
            if not volume:
                kwargs.pop("volume", None)

            await self.node.filters(
                guild_id=self.channel.guild.id,
                **kwargs,
            )
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
        if paused:
            msg = "\N{DOUBLE VERTICAL BAR}\N{VARIATION SELECTOR-16}"
        else:
            msg = "\N{BLACK RIGHT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}"
        for i in range(sections):
            if i == loc_time:
                msg += seek
            else:
                msg += bar
        return msg

    async def get_currently_playing_message(
        self, embed: bool = True, messageable: Messageable | discord.Interaction = None
    ) -> discord.Embed | str:
        if embed:
            queue_list = ""
            arrow = self.draw_time()
            pos = format_time(self.position)
            current = self.current
            if current.stream:
                dur = "LIVE"
            else:
                dur = format_time(current.duration)
            current_track_description = await current.get_track_display_name(with_url=True)
            if current.stream:
                queue_list += "**Currently livestreaming:**\n"
                queue_list += f"{current_track_description}\n"
                queue_list += f"Requester: **{current.requester.mention}**"
                queue_list += f"\n\n{arrow}`{pos}`/`{dur}`\n\n"
            else:
                queue_list += "Playing: "
                queue_list += f"{current_track_description}\n"
                queue_list += f"Requester: **{current.requester.mention}**"
                queue_list += f"\n\n{arrow}`{pos}`/`{dur}`\n\n"
            page = await self.node.node_manager.client.construct_embed(
                title=f"Now Playing in __{self.guild.name}__",
                description=queue_list,
                messageable=messageable,
            )
            if url := await current.thumbnail():
                page.set_thumbnail(url=url)

            queue_dur = await self.queue_duration()
            queue_total_duration = format_time(queue_dur)
            text = f"{self.queue.qsize()} tracks, {queue_total_duration} remaining\n"
            if not self.is_repeating:
                repeat_emoji = "\N{CROSS MARK}"
            elif self._config.repeat_queue:
                repeat_emoji = "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}"
            else:
                repeat_emoji = "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS WITH CIRCLED ONE OVERLAY}"

            if not self._config.auto_play:
                autoplay_emoji = "\N{CROSS MARK}"
            else:
                autoplay_emoji = "\N{WHITE HEAVY CHECK MARK}"

            text += "Repeating" + ": " + repeat_emoji
            text += (" | " if text else "") + "Auto Play" + ": " + autoplay_emoji
            text += (" | " if text else "") + "Volume" + ": " + f"{self.volume}%"
            page.set_footer(text=text)
            return page

    async def get_queue_page(
        self,
        page_index: int,
        per_page: int,
        total_pages: int,
        embed: bool = True,
        messageable: Messageable | discord.Interaction = None,
    ) -> discord.Embed | str:
        start_index = page_index * per_page
        end_index = start_index + per_page
        tracks = list(itertools.islice(self.queue.raw_queue, start_index, end_index))
        if embed:
            queue_list = ""
            arrow = self.draw_time()
            pos = format_time(self.position)
            current = self.current
            if current.stream:
                dur = "LIVE"
            else:
                dur = format_time(current.duration)
            current_track_description = await current.get_track_display_name(with_url=True)
            if current.stream:
                queue_list += "**Currently livestreaming:**\n"
                queue_list += f"{current_track_description}\n"
                queue_list += f"Requester: **{current.requester.mention}**"
                queue_list += f"\n\n{arrow}`{pos}`/`{dur}`\n\n"
            else:
                queue_list += "Playing: "
                queue_list += f"{current_track_description}\n"
                queue_list += f"Requester: **{current.requester.mention}**"
                queue_list += f"\n\n{arrow}`{pos}`/`{dur}`\n\n"
            if await self._config.fetch_shuffle():
                queue_list += "__Queue order is not accurate due to shuffle being toggled__\n\n"
            if tracks:
                padding = len(str(start_index + len(tracks)))
                async for track_idx, track in AsyncIter(tracks).enumerate(start=start_index + 1):
                    track_description = await track.get_track_display_name(max_length=50, with_url=True)
                    diff = padding - len(str(track_idx))
                    queue_list += f"`{track_idx}.{' '*diff}` {track_description}\n"
            page = await self.node.node_manager.client.construct_embed(
                title=f"Queue for __{self.guild.name}__",
                description=queue_list,
                messageable=messageable,
            )
            if url := await current.thumbnail():
                page.set_thumbnail(url=url)
            queue_dur = await self.queue_duration()
            queue_total_duration = format_time(queue_dur)
            text = (
                f"Page {page_index + 1}/{total_pages} | {self.queue.qsize()} tracks, {queue_total_duration} remaining\n"
            )
            if not self.is_repeating:
                repeat_emoji = "\N{CROSS MARK}"
            elif self._config.repeat_queue:
                repeat_emoji = "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}"
            else:
                repeat_emoji = "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS WITH CIRCLED ONE OVERLAY}"

            if not self.autoplay_enabled:
                autoplay_emoji = "\N{CROSS MARK}"
            else:
                autoplay_emoji = "\N{WHITE HEAVY CHECK MARK}"
            text += f"Repeating: {repeat_emoji}"
            text += f"{(' | ' if text else '')}Auto Play: {autoplay_emoji}"
            text += f"{(' | ' if text else '')}Volume: {self.volume}%"
            page.set_footer(text=text)
            return page

    async def queue_duration(self) -> int:
        dur = [
            track.duration  # type: ignore
            async for track in AsyncIter(self.queue.raw_queue).filter(lambda x: not (x.stream or x.is_partial))
        ]
        queue_dur = sum(dur)
        if self.queue.empty():
            queue_dur = 0
        try:
            if not self.current.stream:
                remain = self.current.duration - self.position
            else:
                remain = 0
        except AttributeError:
            remain = 0
        queue_total_duration = remain + queue_dur
        return queue_total_duration

    async def remove_from_queue(
        self,
        track: Track,
        requester: discord.Member,
        duplicates: bool = False,
    ) -> int:
        if self.queue.empty():
            return 0
        tracks, count = await self.queue.remove(track, duplicates=duplicates)
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
        self.node.dispatch_event(
            QueueTrackPositionChangedEvent(before=index, after=new_index, track=track, player=self, requester=requester)
        )
        return True

    async def shuffle_queue(self, requester: discord.Member) -> None:
        if await self.player_manager.global_config.fetch_shuffle() is False:
            return
        self.node.dispatch_event(QueueShuffledEvent(player=self, requester=requester))
        await self.queue.shuffle()

    async def set_autoplay_playlist(self, playlist: int | PlaylistModel) -> None:
        if isinstance(playlist, int):
            self._autoplay_playlist = await self.player_manager.client.playlist_db_manager.get_playlist_by_id(playlist)
        else:
            self._autoplay_playlist = playlist
        self.config.auto_play_playlist_id = self._autoplay_playlist.id
        await self.config.save()

    async def set_autoplay(self, autoplay: bool) -> None:
        self._config.auto_play = autoplay
        await self._config.save()

    async def to_dict(self) -> dict:
        """
        Returns a dict representation of the player.
        """
        return {
            "id": int(self.guild.id),
            "channel_id": self.channel.id,
            "current": await self.current.to_json() if self.current else None,
            "text_channel_id": self.text_channel.id if self.text_channel else None,
            "notify_channel_id": self.notify_channel.id if self.notify_channel else None,
            "paused": self.paused,
            "repeat_queue": self._config.repeat_queue,
            "repeat_current": self._config.repeat_current,
            "shuffle": self._config.shuffle,
            "auto_play": self._config.auto_play,
            "auto_play_playlist_id": self._autoplay_playlist.id if self._autoplay_playlist is not None else None,
            "volume": self.volume,
            "position": self.position,
            "playing": self.is_playing,
            "queue": [await t.to_json() for t in self.queue.raw_queue] if not self.queue.empty() else [],
            "history": [await t.to_json() for t in self.history.raw_queue] if not self.history.empty() else [],
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
            },
            "self_deaf": self.self_deaf,
            "extras": {},
        }

    async def save(self) -> None:
        await self.node.node_manager.client.player_state_db_manager.save_player(await self.to_dict())

    async def restore(self, player: PlayerStateModel, requester: discord.abc.User) -> None:
        if self._restored is True:
            return
        # FIXME: Add an event to ensure that the player is restored in the correct state ?
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
        self.current = None
        self._notify_channel = self.guild.get_channel_or_thread(player.notify_channel_id)
        self._text_channel = self.guild.get_channel_or_thread(player.text_channel_id)
        self._forced_vc = self.guild.get_channel_or_thread(player.channel_id)
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
        self.queue.raw_b64s = list(t.track for t in queue if t.track)
        self.history.raw_queue = collections.deque(history)
        self.history.raw_b64s = list(t.track for t in history)
        tried = 0
        if current:
            current.timestamp = int(player.position)
            self.queue.put_nowait([current], index=0)
            node = self.node.node_manager.find_best_node(
                region=self.region, feature=await current.requires_capability()
            )
            while not node:
                await asyncio.sleep(1)
                node = self.node.node_manager.find_best_node(
                    region=self.region, feature=await current.requires_capability()
                )
                tried += 1
                if tried > 600:
                    return  # Exit without restoring after 10 minutes of waiting
            await self.change_node(node)
        else:
            await self.change_to_best_node()

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
            )
        if self.volume_filter.changed:
            await self.node.send(op="volume", guildId=self.guild_id, volume=self.volume)
        if player.playing:
            await self.next(requester)  # type: ignore
        self._restored = True
        await self.player_manager.client.player_state_db_manager.delete_player(guild_id=self.guild.id)
        self.node.dispatch_event(PlayerRestoredEvent(self, requester))
        LOGGER.info("Player restored - %s", self)
