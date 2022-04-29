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


class TrackEndedEvent:
    pass


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

    def __init__(self, client: Client):
        self._client = client
        self.dispatcher = client.bot.dispatch

    async def dispatch(self, event: Event):
        # Track events
        if isinstance(event, TrackStuckEvent):
            self.pylav_track_stuck(event)
        elif isinstance(event, TrackExceptionEvent):
            self.pylav_track_exception(event)
        elif isinstance(event, TrackEndEvent):
            self.pylav_track_end(event)
        elif isinstance(event, TrackStartEvent):
            if isinstance(event, TrackStartYouTubeMusicEvent):
                self.pylav_track_start_youtube_music(event)
            elif isinstance(event, TrackStartSpotifyEvent):
                self.pylav_track_start_spotify(event)
            elif isinstance(event, TrackStartAppleMusicEvent):
                self.pylav_track_start_apple_music(event)
            elif isinstance(event, TrackStartLocalFileEvent):
                self.pylav_track_start_localfile(event)
            elif isinstance(event, TrackStartHTTPEvent):
                self.pylav_track_start_http(event)
            elif isinstance(event, TrackStartSpeakEvent):
                self.pylav_track_start_speak(event)
            elif isinstance(event, TrackStartYouTubeEvent):
                self.pylav_track_start_youtube(event)
            elif isinstance(event, TrackStartClypitEvent):
                self.pylav_track_start_clypit(event)
            elif isinstance(event, TrackStartGetYarnEvent):
                self.pylav_track_start_getyarn(event)
            elif isinstance(event, TrackStartMixCloudEvent):
                self.pylav_track_start_mixcloud(event)
            elif isinstance(event, TrackStartOCRMixEvent):
                self.pylav_track_start_ocrmix(event)
            elif isinstance(event, TrackStartPornHubEvent):
                self.pylav_track_start_pornhub(event)
            elif isinstance(event, TrackStartRedditEvent):
                self.pylav_track_start_reddit(event)
            elif isinstance(event, TrackStartSoundgasmEvent):
                self.pylav_track_start_soundgasm(event)
            elif isinstance(event, TrackStartTikTokEvent):
                self.pylav_track_start_tiktok(event)
            elif isinstance(event, TrackStartBandcampEvent):
                self.pylav_track_start_bandcamp(event)
            elif isinstance(event, TrackStartSoundCloudEvent):
                self.pylav_track_start_soundcloud(event)
            elif isinstance(event, TrackStartTwitchEvent):
                self.pylav_track_start_twitch(event)
            elif isinstance(event, TrackStartVimeoEvent):
                self.pylav_track_start_vimeo(event)
            elif isinstance(event, TrackStartGCTTSEvent):
                self.pylav_track_start_gctts(event)
            elif isinstance(event, TrackStartNicoNicoEvent):
                self.pylav_track_start_niconico(event)
            else:
                self.pylav_track_start(event)
        elif isinstance(event, TrackSkippedEvent):
            self.pylav_track_skipped(event)
        elif isinstance(event, TrackSeekEvent):
            self.pylav_track_seek_event(event)
        elif isinstance(event, TrackPreviousRequestedEvent):
            self.pylav_track_previous_requested(event)
        elif isinstance(event, TracksRequestedEvent):
            self.pylav_tracks_requested(event)
        elif isinstance(event, TrackAutoPlayEvent):
            self.pylav_track_autoplay(event)
        elif isinstance(event, TrackResumedEvent):
            self.pylav_track_resumed(event)
        # Queue events
        elif isinstance(event, QueueShuffledEvent):
            self.pylav_queue_shuffled(event)
        elif isinstance(event, QueueEndEvent):
            self.pylav_queue_end(event)
        elif isinstance(event, QueueTrackPositionChangedEvent):
            self.pylav_queue_track_position_changed(event)
        elif isinstance(event, QueueTracksRemovedEvent):
            self.pylav_queue_tracks_removed(event)
        # Player events
        elif isinstance(event, PlayerUpdateEvent):
            self.pylav_player_update(event)
        elif isinstance(event, PlayerPausedEvent):
            self.pylav_player_paused(event)
        elif isinstance(event, PlayerStoppedEvent):
            self.pylav_player_stopped(event)
        elif isinstance(event, PlayerResumedEvent):
            self.pylav_player_resumed(event)
        elif isinstance(event, PlayerMovedEvent):
            self.pylav_player_moved(event)
        elif isinstance(event, PlayerDisconnectedEvent):
            self.pylav_player_disconnected(event)
        elif isinstance(event, PlayerConnectedEvent):
            self.pylav_player_connected(event)
        elif isinstance(event, PlayerVolumeChangedEvent):
            self.pylav_player_volume_changed(event)
        elif isinstance(event, PlayerRepeatEvent):
            self.pylav_player_repeat(event)
        elif isinstance(event, PlayerRestoredEvent):
            self.pylav_player_restored(event)
        # Sponsorblock events
        elif isinstance(event, SegmentSkippedEvent):
            self.pylav_segment_skipped(event)
        elif isinstance(event, SegmentsLoadedEvent):
            self.pylav_segments_loaded(event)
        # Filter events
        elif isinstance(event, FiltersAppliedEvent):
            self.pylav_filters_applied(event)
        # Node events
        elif isinstance(event, NodeConnectedEvent):
            self.pylav_node_connected(event)
        elif isinstance(event, NodeDisconnectedEvent):
            self.pylav_node_disconnected(event)
        elif isinstance(event, NodeChangedEvent):
            self.pylav_node_changed(event)
        elif isinstance(event, WebSocketClosedEvent):
            self.pylav_websocket_closed(event)

    # Track events

    def pylav_track_stuck(self, event: TrackStuckEvent):
        self.dispatcher(self.pylav_track_stuck.__name__, event)

    def pylav_track_exception(self, event: TrackExceptionEvent):
        self.dispatcher(self.pylav_track_exception.__name__, event)

    def pylav_track_end(self, event: TrackEndEvent):
        self.dispatcher(self.pylav_track_end.__name__, event)

    def pylav_track_start(self, event: TrackStartEvent):
        self.dispatcher(self.pylav_track_start.__name__, event)

    def pylav_track_skipped(self, event: TrackSkippedEvent):
        self.dispatcher(self.pylav_track_skipped.__name__, event)

    def pylav_track_seek_event(self, event: TrackSeekEvent):
        self.dispatcher(self.pylav_track_seek_event.__name__, event)

    def pylav_track_previous_requested(self, event: TrackPreviousRequestedEvent):
        self.dispatcher(self.pylav_track_previous_requested.__name__, event)

    def pylav_tracks_requested(self, event: TracksRequestedEvent):
        self.dispatcher(self.pylav_tracks_requested.__name__, event)

    def pylav_track_start_youtube(self, event: TrackStartYouTubeEvent):
        self.dispatcher(self.pylav_track_start_youtube.__name__, event)

    def pylav_track_start_soundcloud(self, event: TrackStartSoundCloudEvent):
        self.dispatcher(self.pylav_track_start_soundcloud.__name__, event)

    def pylav_track_start_spotify(self, event: TrackStartSpotifyEvent):
        self.dispatcher(self.pylav_track_start_spotify.__name__, event)

    def pylav_track_start_youtube_music(self, event: TrackStartYouTubeMusicEvent):
        self.dispatcher(self.pylav_track_start_youtube_music.__name__, event)

    def pylav_track_start_apple_music(self, event: TrackStartAppleMusicEvent):
        self.dispatcher(self.pylav_track_start_apple_music.__name__, event)

    def pylav_track_start_localfile(self, event: TrackStartLocalFileEvent):
        self.dispatcher(self.pylav_track_start_localfile.__name__, event)

    def pylav_track_start_http(self, event: TrackStartHTTPEvent):
        self.dispatcher(self.pylav_track_start_http.__name__, event)

    def pylav_track_start_twitch(self, event: TrackStartTwitchEvent):
        self.dispatcher(self.pylav_track_start_twitch.__name__, event)

    def pylav_track_start_speak(self, event: TrackStartSpeakEvent):
        self.dispatcher(self.pylav_track_start_speak.__name__, event)

    def pylav_track_start_clypit(self, event: TrackStartClypitEvent):
        self.dispatcher(self.pylav_track_start_clypit.__name__, event)

    def pylav_track_start_getyarn(self, event: TrackStartGetYarnEvent):
        self.dispatcher(self.pylav_track_start_getyarn.__name__, event)

    def pylav_track_start_mixcloud(self, event: TrackStartMixCloudEvent):
        self.dispatcher(self.pylav_track_start_mixcloud.__name__, event)

    def pylav_track_start_ocrmix(self, event: TrackStartOCRMixEvent):
        self.dispatcher(self.pylav_track_start_ocrmix.__name__, event)

    def pylav_track_start_pornhub(self, event: TrackStartPornHubEvent):
        self.dispatcher(self.pylav_track_start_pornhub.__name__, event)

    def pylav_track_start_reddit(self, event: TrackStartRedditEvent):
        self.dispatcher(self.pylav_track_start_reddit.__name__, event)

    def pylav_track_start_soundgasm(self, event: TrackStartSoundgasmEvent):
        self.dispatcher(self.pylav_track_start_soundgasm.__name__, event)

    def pylav_track_start_tiktok(self, event: TrackStartTikTokEvent):
        self.dispatcher(self.pylav_track_start_tiktok.__name__, event)

    def pylav_track_start_bandcamp(self, event: TrackStartBandcampEvent):
        self.dispatcher(self.pylav_track_start_bandcamp.__name__, event)

    def pylav_track_start_vimeo(self, event: TrackStartVimeoEvent):
        self.dispatcher(self.pylav_track_start_vimeo.__name__, event)

    def pylav_track_start_gctts(self, event: TrackStartGCTTSEvent):
        self.dispatcher(self.pylav_track_start_gctts.__name__, event)

    def pylav_track_start_niconico(self, event: TrackStartNicoNicoEvent):
        self.dispatcher(self.pylav_track_start_niconico.__name__, event)

    def pylav_track_autoplay(self, event: TrackAutoPlayEvent):
        self.dispatcher(self.pylav_track_autoplay.__name__, event)

    def pylav_track_resumed(self, event: TrackResumedEvent):
        self.dispatcher(self.pylav_track_resumed.__name__, event)

    # Queue events

    def pylav_queue_shuffled(self, event: QueueShuffledEvent):
        self.dispatcher(self.pylav_queue_shuffled.__name__, event)

    def pylav_queue_end(self, event: QueueEndEvent):
        self.dispatcher(self.pylav_queue_end.__name__, event)

    def pylav_queue_tracks_removed(self, event: QueueTracksRemovedEvent):
        self.dispatcher(self.pylav_queue_tracks_removed.__name__, event)

    def pylav_queue_track_position_changed(self, event: QueueTrackPositionChangedEvent):
        self.dispatcher(self.pylav_queue_track_position_changed.__name__, event)

    # Player events

    def pylav_player_update(self, event: PlayerUpdateEvent):
        self.dispatcher(self.pylav_player_update.__name__, event)

    def pylav_player_paused(self, event: PlayerPausedEvent):
        self.dispatcher(self.pylav_player_paused.__name__, event)

    def pylav_player_stopped(self, event: PlayerStoppedEvent):
        self.dispatcher(self.pylav_player_stopped.__name__, event)

    def pylav_player_resumed(self, event: PlayerResumedEvent):
        self.dispatcher(self.pylav_player_resumed.__name__, event)

    def pylav_player_moved(self, event: PlayerMovedEvent):
        self.dispatcher(self.pylav_player_moved.__name__, event)

    def pylav_player_disconnected(self, event: PlayerDisconnectedEvent):
        self.dispatcher(self.pylav_player_disconnected.__name__, event)

    def pylav_player_connected(self, event: PlayerConnectedEvent):
        self.dispatcher(self.pylav_player_connected.__name__, event)

    def pylav_player_volume_changed(self, event: PlayerVolumeChangedEvent):
        self.dispatcher(self.pylav_player_volume_changed.__name__, event)

    def pylav_player_repeat(self, event: PlayerRepeatEvent):
        self.dispatcher(self.pylav_player_repeat.__name__, event)

    def pylav_player_restored(self, event: PlayerRestoredEvent):
        self.dispatcher(self.pylav_player_restored.__name__, event)

    # Sponsorblock events

    def pylav_segment_skipped(self, event: SegmentSkippedEvent):
        self.dispatcher(self.pylav_segment_skipped.__name__, event)

    def pylav_segments_loaded(self, event: SegmentsLoadedEvent):
        self.dispatcher(self.pylav_segments_loaded.__name__, event)

    # Filter events

    def pylav_filters_applied(self, event: FiltersAppliedEvent):
        self.dispatcher(self.pylav_filters_applied.__name__, event)

    # Node events

    def pylav_node_connected(self, event: NodeConnectedEvent):
        self.dispatcher(self.pylav_node_connected.__name__, event)

    def pylav_node_disconnected(self, event: NodeDisconnectedEvent):
        self.dispatcher(self.pylav_node_disconnected.__name__, event)

    def pylav_node_changed(self, event: NodeChangedEvent):
        self.dispatcher(self.pylav_node_changed.__name__, event)

    def pylav_websocket_closed(self, event: WebSocketClosedEvent):
        self.dispatcher(self.pylav_websocket_closed.__name__, event)
