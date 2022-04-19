from __future__ import annotations

import collections
import contextlib
import itertools
import time
from copy import copy
from typing import TYPE_CHECKING, Any, Literal

import discord
from discord import VoiceProtocol
from red_commons.logging import getLogger

from pylav.events import (
    NodeChangedEvent,
    PlayerUpdateEvent,
    QueueEndEvent,
    TrackEndEvent,
    TrackExceptionEvent,
    TrackStartEvent,
    TrackStuckEvent,
)
from pylav.exceptions import TrackNotFound
from pylav.filters import ChannelMix, Distortion, Equalizer, Karaoke, LowPass, Rotation, Timescale, Vibrato, Volume
from pylav.filters.tremolo import Tremolo
from pylav.query import Query
from pylav.tracks import AudioTrack
from pylav.utils import AsyncIter, LifoQueue, Queue, format_time

if TYPE_CHECKING:
    from pylav.node import Node
    from pylav.player_manager import PlayerManager

LOGGER = getLogger("red.PyLink.Player")


class Player(VoiceProtocol):
    def __init__(
        self,
        client: discord.Client,
        channel: discord.VoiceChannel,
        *,
        node: Node = None,
    ):
        self.bot = self.client = client
        self.guild_id = str(channel.guild.id)
        self.channel = channel
        self.channel_id = channel.id
        self.node: Node = node
        self.player_manager: PlayerManager = None  # noqa
        self._original_node: Node = None  # noqa
        self._voice_state = {}
        self.region = channel.rtc_region
        self._connected = False

        self._user_data = {}

        self.paused = False
        self._last_update = 0
        self._last_position = 0
        self.position_timestamp = 0
        self.shuffle = False
        self.repeat_current = False
        self.repeat_queue = False
        self.queue: Queue[AudioTrack] = Queue()
        self.history: LifoQueue[AudioTrack] = LifoQueue(maxsize=100)
        self.current: AudioTrack | None = None
        self._post_init_completed = False
        self._is_autoplaying = False
        self._queue_length = 0

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

    @property
    def is_repeating(self) -> bool:
        """Whether the player is repeating tracks."""
        return self.repeat_current or self.repeat_queue

    @property
    def is_auto_playing(self) -> bool:
        """Whether the player is auto-playing."""
        return self._is_autoplaying

    @property
    def volume(self) -> int:
        """
        The current volume.
        """
        return self._volume.get_int_value()

    @volume.setter
    def volume(self, value: int | float | Volume) -> None:
        self._volume = Volume(value)

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

    def post_init(self, node: Node, player_manager: PlayerManager) -> None:
        if self._post_init_completed:
            raise RuntimeError("Post init already completed for this player")
        self.player_manager = player_manager
        self.node = node

    async def change_to_best_node(self, feature: str = None) -> Node | None:
        """
        Returns the best node to play the current track.
        Returns
        -------
        :class:`Node`
        """
        node = self.node.node_manager.find_best_node(region=self.region, feature=feature)
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
        if node != self.node:
            await self.change_node(node)
            return node

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
    def position(self) -> float:
        """Returns the position in the track, adjusted for Lavalink's 5-second stats' interval."""
        if not self.is_playing:
            return 0

        if self.paused:
            return min(self._last_position, self.current.duration)

        difference = time.time() * 1000 - self._last_update
        return min(self._last_position + difference, self.current.duration)

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
        track: AudioTrack | dict | str | None,
        query: Query = None,
    ) -> AudioTrack:
        return (
            AudioTrack(self.node, track, requester=requester, query=query)
            if not isinstance(track, AudioTrack)
            else track
        )

    async def add(
        self,
        requester: int,
        track: AudioTrack | dict | str | None,
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
        await self.queue.put([at], index=index)

    async def bulk_add(
        self,
        tracks_and_queries: list[AudioTrack | dict | str | list[tuple[AudioTrack | dict | str, Query]]],
        requester: int,
        index: int = None,
    ) -> None:
        """
        Adds multiple tracks to the queue.
        Parameters
        ----------
        tracks_and_queries: list[AudioTrack | dict | str | list[tuple[AudioTrack | dict | str, Query]]]
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
        await self.queue.put(output, index=index)

    async def previous(self) -> None:
        if self.history.empty():
            raise TrackNotFound("There are no tracks currently in the player history.")

        track = await self.history.get()
        if track.is_partial and not track.track:
            await track.search(self)
        if self.current:
            await self.history.put([self.current])
        options = {"noReplace": False}
        self.current = track
        if track.skip_segments:
            options["skipSegments"] = track.skip_segments
        await self.node.send(op="play", guildId=self.guild_id, track=track.track, **options)
        await self.node.dispatch_event(TrackStartEvent(self, track))

    async def play(
        self,
        track: AudioTrack | dict | str = None,
        start_time: int = 0,
        end_time: int = 0,
        no_replace: bool = False,
        query: Query = None,
        skip_segments: list[str] | str = None,
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
        """
        options = {}
        skip_segments = self._process_skip_segments(skip_segments)
        if track is not None and isinstance(track, (AudioTrack, dict, str, type(None))):
            track = AudioTrack(self.node, track, query=query, skip_segments=skip_segments)

        if self.current and (self.repeat_queue or self.repeat_current):
            await self.add(self.current.requester_id, self.current)

        self._last_update = 0
        self._last_position = 0
        self.position_timestamp = 0
        self.paused = False
        if self.current:
            await self.history.put([self.current])
        if not track:
            if self.queue.empty():
                await self.stop()  # Also sets current to None.
                self.history.clear()
                await self.node.dispatch_event(QueueEndEvent(self))
                return
            track = await self.queue.get()
        if track.is_partial and not track.track:
            await track.search(self)
        if skip_segments:
            options["skipSegments"] = skip_segments
        if start_time is not None:
            if not isinstance(start_time, int) or not 0 <= start_time <= track.duration:
                raise ValueError(
                    "start_time must be an int with a value equal to, "
                    "or greater than 0, and less than the track duration"
                )
            options["startTime"] = start_time

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
        await self.node.dispatch_event(TrackStartEvent(self, track))

    async def stop(self) -> None:
        """Stops the player."""
        await self.node.send(op="stop", guildId=self.guild_id)
        self.current = None

    async def skip(self) -> None:
        """Plays the next track in the queue, if any."""
        await self.play()

    def set_repeat(self, op_type: Literal["current", "queue"], repeat: bool) -> None:
        """
        Sets the player's repeat state.
        Parameters
        ----------
        repeat: :class:`bool`
            Whether to repeat the player or not.
        op_type: :class:`str`
            The type of repeat to set. Can be either ``"current"`` or ``"queue"``.
        """
        if op_type == "current":
            self.repeat_current = repeat
            self.repeat_queue = False
        elif op_type == "queue":
            self.repeat_queue = repeat
            self.repeat_current = False

    def set_shuffle(self, shuffle: bool) -> None:
        """
        Sets the player's shuffle state.
        Parameters
        ----------
        shuffle: :class:`bool`
            Whether to shuffle the player or not.
        """
        self.shuffle = shuffle

    async def set_pause(self, pause: bool) -> None:
        """
        Sets the player's paused state.
        Parameters
        ----------
        pause: :class:`bool`
            Whether to pause the player or not.
        """
        await self.node.send(op="pause", guildId=self.guild_id, pause=pause)
        self.paused = pause

    async def set_volume(self, vol: int | float | Volume) -> None:
        """
        Sets the player's volume
        Note
        ----
        A limit of 1000 is imposed by Lavalink.
        Parameters
        ----------
        vol: :class:`int`
            The new volume level.
        """

        self.volume = max(min(vol, 1000), 0)
        await self.node.send(op="volume", guildId=self.guild_id, volume=self.volume)

    async def seek(self, position: float, with_filter: bool = False) -> None:
        """
        Seeks to a given position in the track.
        Parameters
        ----------
        position: :class:`int`
            The new position to seek to in milliseconds.
        with_filter: :class:`bool`
            Whether to apply the filter or not.
        """
        if self.current and self.current.is_seekable:
            if with_filter:
                position = self.position
            position = max(min(position, self.current.duration), 0)
            await self.node.send(op="seek", guildId=self.guild_id, position=position)

    async def _handle_event(self, event) -> None:
        """
        Handles the given event as necessary.
        Parameters
        ----------
        event: :class:`Event`
            The event that will be handled.
        """
        if (
            isinstance(event, (TrackStuckEvent, TrackExceptionEvent))
            or isinstance(event, TrackEndEvent)
            and event.reason == "FINISHED"
        ):
            await self.play()

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

        event = PlayerUpdateEvent(self, self._last_position, self.position_timestamp)
        await self.node.dispatch_event(event)

    async def change_node(self, node) -> None:
        """
        Changes the player's node
        Parameters
        ----------
        node: :class:`Node`
            The node the player is changed to.
        """
        if self.node.available:
            await self.node.send(op="destroy", guildId=self.guild_id)

        old_node = self.node
        self.node = node

        if self._voice_state:
            await self._dispatch_voice_update()

        if self.current:
            options = {}
            if self.current.skip_segments:
                options["skipSegments"] = self.current.skip_segments
            await self.node.send(
                op="play", guildId=self.guild_id, track=self.current.track, startTime=self.position, **options
            )
            self._last_update = time.time() * 1000

            if self.paused:
                await self.node.send(op="pause", guildId=self.guild_id, pause=self.paused)

        if self.volume != 100:
            await self.node.send(op="volume", guildId=self.guild_id, volume=self.volume)

        await self.node.dispatch_event(NodeChangedEvent(self, old_node, node))

    def to_dict(self) -> dict:
        """
        Returns a dict representation of the player.
        """

        return {
            "guild_id": int(self.guild_id),
            "channel_id": self.channel_id,
            "current": self.current.to_json() if self.current else None,
            "paused": self.paused,
            "repeat_queue": self.repeat_queue,
            "repeat_current": self.repeat_current,
            "shuffle": self.shuffle,
            "auto_playing": self._is_autoplaying,
            "volume": self.volume,
            "position": self.position,
            "playing": self.is_playing,
            "queue": [t.to_json() for t in self.queue.raw_queue] if not self.queue.empty() else [],  # noqa
            "history": [t.to_json() for t in self.history.raw_queue] if not self.history.empty() else [],
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
        }

    async def save(self) -> None:
        await self.node.node_manager.client.player_state_manager.upsert_players([self.to_dict()])

    async def connect(
        self,
        *,
        timeout: float = 2.0,
        reconnect: bool = False,
        self_mute: bool = False,
        self_deaf: bool = False,
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
        """
        await self.guild.change_voice_state(channel=self.channel, self_mute=self_mute, self_deaf=self_deaf)
        self._connected = True

        LOGGER.info("[Player-%s] Connected to voice channel", self.channel.guild.id)

    async def disconnect(self, *, force: bool = False) -> None:
        try:
            LOGGER.info("[Player-%s] Disconnected from voice channel", self.channel.guild.id)

            await self.guild.change_voice_state(channel=None)
            self._connected = False
        finally:
            self.queue.clear()
            self.history.clear()
            with contextlib.suppress(ValueError):
                self.player_manager.players.pop(self.channel.guild.id)

            await self.node.send(op="destroy", guildId=self.guild_id)

            self.cleanup()

    async def move_to(
        self,
        channel: discord.VoiceChannel,
        self_mute: bool = False,
        self_deaf: bool = False,
    ) -> None:
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
        """
        if channel == self.channel:
            return
        LOGGER.info(
            "[Player-%s] Moving from %s to voice channel: %s", self.channel.guild.id, self.channel.id, channel.id
        )
        self.channel = channel
        await self.guild.change_voice_state(channel=self.channel, self_mute=self_mute, self_deaf=self_deaf)
        self._connected = True

    async def set_volume_filter(self, volume: Volume) -> None:
        """
        Sets the volume of Lavalink.
        Parameters
        ----------
        volume : Volume
            Volume to set
        """
        await self.set_filters(
            volume=volume,
        )

    async def set_equalizer(self, equalizer: Equalizer, forced: bool = False) -> None:
        """
        Sets the Equalizer of Lavalink.
        Parameters
        ----------
        equalizer : Equalizer
            Equalizer to set
        forced : bool
            Whether to force the equalizer to be set resetting any other filters currently applied
        """
        await self.set_filters(
            equalizer=equalizer,
            reset_not_set=forced,
        )

    async def set_karaoke(self, karaoke: Karaoke, forced: bool = False) -> None:
        """
        Sets the Karaoke of Lavalink.
        Parameters
        ----------
        karaoke : Karaoke
            Karaoke to set
        forced : bool
            Whether to force the karaoke to be set resetting any other filters currently applied
        """
        await self.set_filters(
            karaoke=karaoke,
            reset_not_set=forced,
        )

    async def set_timescale(self, timescale: Timescale, forced: bool = False) -> None:
        """
        Sets the Timescale of Lavalink.
        Parameters
        ----------
        timescale : Timescale
            Timescale to set
        forced : bool
            Whether to force the timescale to be set resetting any other filters currently applied
        """
        await self.set_filters(
            timescale=timescale,
            reset_not_set=forced,
        )

    async def set_tremolo(self, tremolo: Tremolo, forced: bool = False) -> None:
        """
        Sets the Tremolo of Lavalink.
        Parameters
        ----------
        tremolo : Tremolo
            Tremolo to set
        forced : bool
            Whether to force the tremolo to be set resetting any other filters currently applied
        """
        await self.set_filters(
            tremolo=tremolo,
            reset_not_set=forced,
        )

    async def set_vibrato(self, vibrato: Vibrato, forced: bool = False) -> None:
        """
        Sets the Vibrato of Lavalink.
        Parameters
        ----------
        vibrato : Vibrato
            Vibrato to set
        forced : bool
            Whether to force the vibrato to be set resetting any other filters currently applied
        """
        await self.set_filters(
            vibrato=vibrato,
            reset_not_set=forced,
        )

    async def set_rotation(self, rotation: Rotation, forced: bool = False) -> None:
        """
        Sets the Rotation of Lavalink.
        Parameters
        ----------
        rotation : Rotation
            Rotation to set
        forced : bool
            Whether to force the rotation to be set resetting any other filters currently applied
        """
        await self.set_filters(
            rotation=rotation,
            reset_not_set=forced,
        )

    async def set_distortion(self, distortion: Distortion, forced: bool = False) -> None:
        """
        Sets the Distortion of Lavalink.
        Parameters
        ----------
        distortion : Distortion
            Distortion to set
        forced : bool
            Whether to force the distortion to be set resetting any other filters currently applied
        """
        await self.set_filters(
            distortion=distortion,
            reset_not_set=forced,
        )

    async def set_low_pass(self, low_pass: LowPass, forced: bool = False) -> None:
        """
        Sets the LowPass of Lavalink.
        Parameters
        ----------
        low_pass : LowPass
            LowPass to set
        forced : bool
            Whether to force the low_pass to be set resetting any other filters currently applied
        """
        await self.set_filters(
            low_pass=low_pass,
            reset_not_set=forced,
        )

    async def set_channel_mix(self, channel_mix: ChannelMix, forced: bool = False) -> None:
        """
        Sets the ChannelMix of Lavalink.
        Parameters
        ----------
        channel_mix : ChannelMix
            ChannelMix to set
        forced : bool
            Whether to force the channel_mix to be set resetting any other filters currently applied
        """
        await self.set_filters(
            channel_mix=channel_mix,
            reset_not_set=forced,
        )

    async def set_filters(
        self,
        *,
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
            await self.node.filters(
                guild_id=self.channel.guild.id,
                volume=volume or self.volume,
                equalizer=equalizer,
                karaoke=karaoke,
                timescale=timescale,
                tremolo=tremolo,
                vibrato=vibrato,
                rotation=rotation,
                distortion=distortion,
                low_pass=low_pass,
                channel_mix=channel_mix,
            )
        else:
            await self.node.filters(
                guild_id=self.channel.guild.id,
                volume=volume or self.volume,
                equalizer=equalizer or (self.equalizer if self.equalizer.changed else None),
                karaoke=karaoke or (self.karaoke if self.karaoke.changed else None),
                timescale=timescale or (self.timescale if self.timescale.changed else None),
                tremolo=tremolo or (self.tremolo if self.tremolo.changed else None),
                vibrato=vibrato or (self.vibrato if self.vibrato.changed else None),
                rotation=rotation or (self.rotation if self.rotation.changed else None),
                distortion=distortion or (self.distortion if self.distortion.changed else None),
                low_pass=low_pass or (self.low_pass if self.low_pass.changed else None),
                channel_mix=channel_mix or (self.channel_mix if self.channel_mix.changed else None),
            )
        await self.seek(self.position, with_filter=True)

    def _process_skip_segments(self, skip_segments: list[str] | str | None):
        if skip_segments is not None and self.node.supports_sponsorblock:
            if isinstance(skip_segments, str) and skip_segments == "all":
                skip_segments = [
                    "sponsor",
                    "selfpromo",
                    "interaction",
                    "intro",
                    "outro",
                    "preview",
                    "music_offtopic",
                    "filler",
                ]
            else:
                skip_segments = list(
                    filter(
                        lambda x: x
                        in [
                            "sponsor",
                            "selfpromo",
                            "interaction",
                            "intro",
                            "outro",
                            "preview",
                            "music_offtopic",
                            "filler",
                        ],
                        map(lambda x: x.lower(), skip_segments),
                    )
                )
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

    async def get_currently_playing_message(self, embed: bool = True) -> discord.Embed | str:
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
            )
            if url := await current.thumbnail():
                page.set_thumbnail(url=url)

            queue_dur = await self.queue_duration()
            queue_total_duration = format_time(queue_dur)
            text = "{num_tracks} tracks, {num_remaining} remaining\n".format(
                num_tracks=self.queue.qsize(),
                num_remaining=queue_total_duration,
            )
            if not self.is_repeating:
                repeat_emoji = "\N{CROSS MARK}"
            elif self.repeat_queue:
                repeat_emoji = "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}"
            else:
                repeat_emoji = "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS WITH CIRCLED ONE OVERLAY}"

            text += "Repeating" + ": " + repeat_emoji
            text += (" | " if text else "") + "Volume" + ": " + f"{self.volume}%"
            page.set_footer(text=text)
            return page

    async def get_queue_page(
        self, page_index: int, per_page: int, total_pages: int, embed: bool = True
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
            if tracks:
                async for track_idx, (_, track) in AsyncIter(tracks).enumerate(start=start_index + 1):
                    track_description = await track.get_track_display_name(max_length=50, with_url=True)
                    queue_list += f"`{track_idx}.` {track_description}\n"
            page = await self.node.node_manager.client.construct_embed(
                title=f"Queue for __{self.guild.name}__",
                description=queue_list,
            )
            if url := await current.thumbnail():
                page.set_thumbnail(url=url)
            queue_dur = await self.queue_duration()
            queue_total_duration = format_time(queue_dur)
            text = "Page {page_num}/{total_pages} | {num_tracks} tracks, {num_remaining} remaining\n".format(
                page_num=page_index + 1,
                total_pages=total_pages,
                num_tracks=self.queue.qsize(),
                num_remaining=queue_total_duration,
            )
            if not self.is_repeating:
                repeat_emoji = "\N{CROSS MARK}"
            elif self.repeat_queue:
                repeat_emoji = "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}"
            else:
                repeat_emoji = "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS WITH CIRCLED ONE OVERLAY}"

            text += "Repeating" + ": " + repeat_emoji
            text += (" | " if text else "") + "Volume" + ": " + f"{self.volume}%"
            page.set_footer(text=text)
            return page

    async def queue_duration(self) -> int:
        dur = [
            track.duration
            async for track in AsyncIter(self.queue.raw_queue, steps=50).filter(
                lambda x: not (x[1].stream or x[1].is_partial)
            )
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

    async def remove_from_queue(self, track: AudioTrack) -> int:
        if self.queue.empty():
            return 0
        unique_id = track.unique_identifier
        start_count = self.queue.qsize()
        counter = itertools.count(1)
        queue = filter(lambda x: x.unique_identifier != unique_id and next(counter), self.queue.raw_queue)
        valid = next(copy(counter)) - 1
        diff = start_count - valid
        self.queue.raw_queue = collections.deque(queue)
        return diff

    async def move_track(self, track: AudioTrack, new_index: int = None) -> bool:
        if self.queue.empty():
            return False
        index = next(i for i, t in enumerate(self.queue.raw_queue) if t == track)
        track = await self.queue.get(index)
        await self.queue.put([track], new_index)
        return True

    async def shuffle_queue(self) -> None:
        await self.queue.shuffle()
