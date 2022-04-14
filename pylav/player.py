from __future__ import annotations

import asyncio
import collections
import heapq
import time
from typing import TYPE_CHECKING, Any, Literal

import discord
from discord import VoiceProtocol

from pylav.events import (
    NodeChangedEvent,
    PlayerUpdateEvent,
    QueueEndEvent,
    TrackEndEvent,
    TrackExceptionEvent,
    TrackStartEvent,
    TrackStuckEvent,
)
from pylav.tracks import AudioTrack

if TYPE_CHECKING:
    from pylav.node import Node


class Player(VoiceProtocol):
    def __init__(self, client: discord.Client, channel: discord.VoiceChannel, node: Node = None):
        self.bot = client
        self.guild_id = str(channel.guild.id)
        self.channel_id = channel.id
        self.node = node
        self._original_node = None  # This is used internally for fail-over.
        self._voice_state = {}
        self.channel_id = None
        self.region = channel.rtc_region

        self._user_data = {}

        self.paused = False
        self._last_update = 0
        self._last_position = 0
        self.position_timestamp = 0
        self.volume = 100
        self.shuffle = False
        self.repeat_current = False
        self.repeat_queue = False
        self.queue = asyncio.PriorityQueue()
        self.history = collections.deque(maxlen=100)
        self.current: AudioTrack | None = None

    def add_node(self, node: Node) -> None:
        if self.node is None:
            self.node = node
        else:
            raise RuntimeError("Cannot add more than one node to a player")

    def change_to_best_node(self) -> Node:
        """
        Returns the best node to play the current track.
        Returns
        -------
        :class:`Node`
        """
        node = self.node.node_manager.find_best_node(region=self.region)
        await self.change_node(node)
        return node

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

    async def add(
        self,
        requester: int,
        track: AudioTrack | dict | str | None,
        index: int = None,
        priority: int = 1000,
        query: str = None,
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
        priority: Optional[:class:`int`]
            The priority of the track. Defaults to `1`, higher numbers will be played first.
        query: Optional[:class:`str`]
            The query that was used to search for the track.
        """
        at = (
            AudioTrack(self.node, track, requester=requester, query=query)
            if not isinstance(track, AudioTrack)
            else track
        )

        if index is None:
            await self.queue.put((priority, at))
        else:
            heapq.heappush(self.queue._queue, (priority, at))

    async def previous(self) -> None:
        if not self.history:
            raise TrackNotFound("There are no tracks currently in the player history.")

        track = self.history.pop()
        if track.is_partial and not track.track:
            await track.search()
        if self.current:
            self.history.appendleft(self.current)
        options = {"noReplace": False}
        self.current = track
        await self.node.send(op="play", guildId=self.guild_id, track=track.track, **options)
        await self.node.dispatch_event(TrackStartEvent(self, track))

    async def play(
        self,
        track: AudioTrack | dict | str = None,
        start_time: int = 0,
        end_time: int = 0,
        no_replace: bool = False,
        query: str = None,
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
        query: Optional[:class:`str`]
            The query that was used to search for the track.
        """
        if track is not None and isinstance(track, dict):
            track = AudioTrack(self.node, track, requester=self.client.user.id, query=query)
        elif track is None and query is not None:
            track = AudioTrack(self.node, None, requester=self.client.user.id, query=query)

        if self.repeat_queue and self.current:
            await self.add(self.current.requester_id, self.current)
        elif self.repeat_current and self.current:
            await self.add(self.current.requester_id, self.current, priority=100)

        self._last_update = 0
        self._last_position = 0
        self.position_timestamp = 0
        self.paused = False
        if self.current:
            self.history.appendleft(self.current)
        if not track:
            if not self.queue:
                await self.stop()  # Also sets current to None.
                self.history.clear()
                await self.node.dispatch_event(QueueEndEvent(self))
                return
            track = await self.queue.get()

        if track.is_partial and not track.track:
            await track.search()

        options = {}

        if start_time is not None:
            if not isinstance(start_time, int) or not 0 <= start_time <= track.duration:
                raise ValueError(
                    "start_time must be an int with a value equal to, or greater than 0, and less than the track duration"
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

    async def set_volume(self, vol: int) -> None:
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

    async def seek(self, position: int) -> None:
        """
        Seeks to a given position in the track.
        Parameters
        ----------
        position: :class:`int`
            The new position to seek to in milliseconds.
        """
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
            await self.node.send(op="play", guildId=self.guild_id, track=self.current.track, startTime=self.position)
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
            "queue": [t[-1].to_json() for t in self.queue._queue] if self.queue else [],
            "history": [t.to_json() for t in self.history] if self.history else [],
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
        self.node.node_manager.client.player_state_manager.upsert_players(self)
