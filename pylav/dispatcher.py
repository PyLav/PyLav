from __future__ import annotations

from typing import TYPE_CHECKING

from pylav.events import (
    Event,
    FiltersAppliedEvent,
    NodeChangedEvent,
    NodeConnectedEvent,
    NodeDisconnectedEvent,
    PlayerConnectedEvent,
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
    SegmentSkippedEvent,
    SegmentsLoadedEvent,
    TrackAutoPlayEvent,
    TrackEndEvent,
    TrackExceptionEvent,
    TrackPreviousRequestedEvent,
    TrackResumedEvent,
    TrackSeekEvent,
    TrackSkippedEvent,
    TracksRequestedEvent,
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

if TYPE_CHECKING:
    from pylav.client import Client


class DispatchManager:
    """
    The Dispatcher is responsible for dispatching events to the appropriate
    handlers.

    The method names are the event names.

    You can listen to events by adding the following to your client:


    Examples
    --------
    >>> from discord.app_commands import commands

    >>> @commands.Cog.listener()
    >>> async def on_pylav_queue_ended(self, event: QueueEndEvent):
    >>>    print(f"Queue ended: {event.player}")

    >>> @commands.Cog.listener()
    >>> async def on_pylav_track_stuck(self, event: TrackStuckEvent):
    >>>    print(f"Track got stuck: {event.track}")

    """

    __slots__ = ("_client", "dispatcher", "mapping")

    def __init__(self, client: Client):
        self._client = client
        self.dispatcher = client.bot.dispatch
        self.mapping = {
            TrackStuckEvent: "pylav_track_stuck",
            TrackExceptionEvent: "pylav_track_exception",
            TrackEndEvent: "pylav_track_end",
            TrackStartEvent: "pylav_track_start",
            TrackStartYouTubeMusicEvent: "pylav_track_start_youtube_music",
            TrackStartSpotifyEvent: "pylav_track_start_spotify",
            TrackStartAppleMusicEvent: "pylav_track_start_apple_music",
            TrackStartLocalFileEvent: "pylav_track_start_localfile",
            TrackStartHTTPEvent: "pylav_track_start_http",
            TrackStartSpeakEvent: "pylav_track_start_speak",
            TrackStartYouTubeEvent: "pylav_track_start_youtube",
            TrackStartClypitEvent: "pylav_track_start_clypit",
            TrackStartGetYarnEvent: "pylav_track_start_getyarn",
            TrackStartMixCloudEvent: "pylav_track_start_mixcloud",
            TrackStartOCRMixEvent: "pylav_track_start_ocrmix",
            TrackStartPornHubEvent: "pylav_track_start_pornhub",
            TrackStartRedditEvent: "pylav_track_start_reddit",
            TrackStartSoundgasmEvent: "pylav_track_start_soundgasm",
            TrackStartTikTokEvent: "pylav_track_start_tiktok",
            TrackStartBandcampEvent: "pylav_track_start_bandcamp",
            TrackStartSoundCloudEvent: "pylav_track_start_soundcloud",
            TrackStartTwitchEvent: "pylav_track_start_twitch",
            TrackStartVimeoEvent: "pylav_track_start_vimeo",
            TrackStartGCTTSEvent: "pylav_track_start_gctts",
            TrackStartNicoNicoEvent: "pylav_track_start_niconico",
            TrackSkippedEvent: "pylav_track_skipped",
            TrackSeekEvent: "pylav_track_seek",
            TrackPreviousRequestedEvent: "pylav_track_previous_requested",
            TracksRequestedEvent: "pylav_tracks_requested",
            TrackAutoPlayEvent: "pylav_track_autoplay",
            TrackResumedEvent: "pylav_track_resumed",
            QueueShuffledEvent: "pylav_queue_shuffled",
            QueueEndEvent: "pylav_queue_end",
            QueueTrackPositionChangedEvent: "pylav_queue_track_position_changed",
            QueueTracksRemovedEvent: "pylav_queue_tracks_removed",
            PlayerUpdateEvent: "pylav_player_update",
            PlayerPausedEvent: "pylav_player_paused",
            PlayerStoppedEvent: "pylav_player_stopped",
            PlayerResumedEvent: "pylav_player_resumed",
            PlayerMovedEvent: "pylav_player_moved",
            PlayerDisconnectedEvent: "pylav_player_disconnected",
            PlayerConnectedEvent: "pylav_player_connected",
            PlayerVolumeChangedEvent: "pylav_player_volume_changed",
            PlayerRepeatEvent: "pylav_player_repeat",
            PlayerRestoredEvent: "pylav_player_restored",
            SegmentSkippedEvent: "pylav_segment_skipped",
            SegmentsLoadedEvent: "pylav_segments_loaded",
            FiltersAppliedEvent: "pylav_filters_applied",
            NodeConnectedEvent: "pylav_node_connected",
            NodeDisconnectedEvent: "pylav_node_disconnected",
            NodeChangedEvent: "pylav_node_changed",
            WebSocketClosedEvent: "pylav_websocket_closed",
        }

    async def dispatch(self, event: Event):
        event_name = self.mapping[type(event)]
        self.dispatcher(event_name, event)
