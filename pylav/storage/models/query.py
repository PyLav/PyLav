from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from dacite import from_dict

from pylav.constants.config import READ_CACHING_ENABLED
from pylav.helpers.singleton import SingletonCachedByKey
from pylav.nodes.api.responses.track import Track
from pylav.storage.database.cache.decodators import maybe_cached
from pylav.storage.database.cache.model import CachedModel
from pylav.storage.database.tables.queries import QueryRow
from pylav.storage.database.tables.tracks import TrackRow
from pylav.type_hints.dict_typing import JSON_DICT_TYPE


@dataclass(eq=True, slots=True, unsafe_hash=True, order=True, kw_only=True, frozen=True)
class Query(CachedModel, metaclass=SingletonCachedByKey):
    id: str

    def get_cache_key(self) -> str:
        return self.id

    @maybe_cached
    async def exists(self) -> bool:
        """Check if the config exists.

        Returns
        -------
        bool
            Whether the config exists.
        """
        return await QueryRow.exists().where(QueryRow.identifier == self.id)

    async def delete(self) -> None:
        """Delete the query from the database"""
        await QueryRow.delete().where(QueryRow.identifier == self.id)
        await self.invalidate_cache()

    @maybe_cached
    async def size(self) -> int:
        """Count the tracks of the playlist.

        Returns
        -------
        int
            The number of tracks in the playlist.
        """
        tracks = await self.fetch_tracks()
        return len(tracks) if tracks else 0

    @maybe_cached
    async def fetch_tracks(self) -> list[str | JSON_DICT_TYPE]:
        """Get the tracks of the playlist.

        Returns
        -------
        list[str]
            The tracks of the playlist.
        """
        response = (
            await QueryRow.select(QueryRow.tracks(TrackRow.encoded, TrackRow.info, TrackRow.pluginInfo, load_json=True))
            .where(QueryRow.identifier == self.id)
            .first()
            .output(load_json=True, nested=True)
        )
        data = response["tracks"] if response else []
        return data

    async def update_tracks(self, tracks: list[str | Track]):
        """Update the tracks of the playlist.

        Parameters
        ----------
        tracks: list[str | Track]
            The tracks of the playlist.
        """
        query_row = await QueryRow.objects().get_or_create(QueryRow.identifier == self.id)
        try:
            old_tracks = await query_row.get_m2m(QueryRow.tracks)
        except ValueError:
            old_tracks = []
        new_tracks = []
        # TODO: Optimize this, after https://github.com/piccolo-orm/piccolo/discussions/683 is answered or fixed
        _temp = defaultdict(list)
        for x in tracks:
            _temp[type(x)].append(x)
        for entry_type, entry_list in _temp.items():
            if entry_type == str:
                for track_object in await self.client.decode_tracks(entry_list, raise_on_failure=False):
                    new_tracks.append(await TrackRow.get_or_create(track_object))
            elif entry_type == dict:
                for track_object in entry_list:
                    new_tracks.append(await TrackRow.get_or_create(from_dict(data_class=Track, data=track_object)))
            else:
                for track_object in entry_list:
                    new_tracks.append(await TrackRow.get_or_create(track_object))

        if old_tracks:
            await query_row.remove_m2m(*old_tracks, m2m=QueryRow.tracks)
        if new_tracks:
            await query_row.add_m2m(*new_tracks, m2m=QueryRow.tracks)
        await self.invalidate_cache(self.fetch_tracks, self.fetch_first)
        await self.update_cache(
            (self.size, len(tracks)),
            (self.exists, True),
        )

    @maybe_cached
    async def fetch_plugin_info(self) -> JSON_DICT_TYPE:
        """Get the plugin info of the playlist.

        Returns
        -------
        JSON_DICT_TYPE
            The plugin info of the playlist.
        """
        response = (
            await QueryRow.select(QueryRow.pluginInfo)
            .where(QueryRow.identifier == self.id)
            .first()
            .output(load_json=True, nested=True)
        )
        return response["pluginInfo"] if response else {}

    async def update_plugin_info(self, plugin_info: JSON_DICT_TYPE) -> None:
        """Update the plugin info of the playlist.

        Parameters
        ----------
        plugin_info: JSON_DICT_TYPE
            The plugin info of the playlist.
        """

        await QueryRow.insert(QueryRow(identifier=self.id, pluginInfo=plugin_info)).on_conflict(
            action="DO UPDATE", target=QueryRow.identifier, values=[QueryRow.pluginInfo]
        )
        await self.update_cache((self.fetch_plugin_info, plugin_info), (self.exists, True))

    @maybe_cached
    async def fetch_info(self) -> JSON_DICT_TYPE:
        """Get the info of the playlist.

        Returns
        -------
        JSON_DICT_TYPE
            The plugin info of the playlist.
        """
        response = (
            await QueryRow.select(QueryRow.info)
            .where(QueryRow.identifier == self.id)
            .first()
            .output(load_json=True, nested=True)
        )
        return response["info"] if response else {}

    async def update_info(self, info: JSON_DICT_TYPE) -> None:
        """Update the info of the playlist.

        Parameters
        ----------
        info: JSON_DICT_TYPE
            The plugin info of the playlist.
        """

        await QueryRow.insert(QueryRow(identifier=self.id, info=info)).on_conflict(
            action="DO UPDATE", target=QueryRow.identifier, values=[QueryRow.info]
        )
        await self.update_cache((self.fetch_plugin_info, info), (self.exists, True))

    @maybe_cached
    async def fetch_name(self) -> str:
        """Get the name of the playlist.

        Returns
        -------
        str
            The name of the playlist.
        """
        response = (
            await QueryRow.select(QueryRow.name)
            .where(QueryRow.identifier == self.id)
            .first()
            .output(load_json=True, nested=True)
        )
        return response["name"] if response else QueryRow.name.default

    async def update_name(self, name: str) -> None:
        """Update the name of the playlist.

        Parameters
        ----------
        name: str
            The name of the playlist.
        """
        await QueryRow.insert(QueryRow(identifier=self.id, name=name)).on_conflict(
            action="DO UPDATE", target=QueryRow.identifier, values=[QueryRow.name]
        )
        await self.update_cache((self.fetch_name, name), (self.exists, True))

    @maybe_cached
    async def fetch_last_updated(self) -> datetime:
        """Get the last updated time of the playlist.

        Returns
        -------
        datetime
            The last updated time of the playlist.
        """
        response = (
            await QueryRow.select(QueryRow.last_updated)
            .where(QueryRow.identifier == self.id)
            .first()
            .output(load_json=True, nested=True)
        )
        return response["last_updated"] if response else QueryRow.last_updated.default

    async def update_last_updated(self) -> None:
        """Update the last updated time of the playlist"""
        await QueryRow.insert(
            QueryRow(identifier=self.id, last_updated=QueryRow.last_updated.default.python())
        ).on_conflict(action="DO UPDATE", target=QueryRow.identifier, values=[QueryRow.last_updated])
        await self.update_cache(
            (self.fetch_last_updated, QueryRow.last_updated.default.python()),
            (self.exists, True),
        )

    async def bulk_update(
        self,
        tracks: list[str | Track],
        name: str,
        info: JSON_DICT_TYPE | None = None,
        plugin_info: JSON_DICT_TYPE | None = None,
    ) -> None:
        """Bulk update the query.

        Parameters
        ----------
        tracks: list[str | Track]
            The tracks of the playlist.
        name: str
            The name of the playlist
        """
        defaults = {QueryRow.name: name}
        if info is not None:
            defaults[QueryRow.info] = info
        if plugin_info is not None:
            defaults[QueryRow.pluginInfo] = plugin_info
        query_row = await QueryRow.objects().get_or_create(QueryRow.identifier == self.id, defaults)
        # noinspection PyProtectedMember
        if not query_row._was_created:
            await QueryRow.update(defaults).where(QueryRow.identifier == self.id)
        try:
            old_tracks = await query_row.get_m2m(QueryRow.tracks)
        except ValueError:
            old_tracks = []
        new_tracks = []
        # TODO: Optimize this, after https://github.com/piccolo-orm/piccolo/discussions/683 is answered or fixed
        _temp = defaultdict(list)
        for x in tracks:
            _temp[type(x)].append(x)
        for entry_type, entry_list in _temp.items():
            if entry_type == str:
                for track_object in await self.client.decode_tracks(entry_list, raise_on_failure=False):
                    new_tracks.append(await TrackRow.get_or_create(track_object))
            elif entry_type == dict:
                for track_object in entry_list:
                    new_tracks.append(await TrackRow.get_or_create(from_dict(data_class=Track, data=track_object)))
            else:
                for track_object in entry_list:
                    new_tracks.append(await TrackRow.get_or_create(track_object))
        if old_tracks:
            await query_row.remove_m2m(*old_tracks, m2m=QueryRow.tracks)
        if new_tracks:
            await query_row.add_m2m(*new_tracks, m2m=QueryRow.tracks)
        await self.invalidate_cache(self.fetch_tracks, self.fetch_first)
        await self.update_cache(
            (self.size, len(tracks)),
            (self.fetch_name, name),
            (self.fetch_last_updated, QueryRow.last_updated.default.python()),
            (self.exists, True),
        )

    async def fetch_index(self, index: int) -> JSON_DICT_TYPE | None:
        """Get the track at the index.

        Parameters
        ----------
        index: int
            The index of the track

        Returns
        -------
        str
            The track at the index
        """
        if READ_CACHING_ENABLED:
            tracks = await self.fetch_tracks()
            return tracks[index] if index < len(tracks) else None
        else:
            tracks = await self.fetch_tracks()
            if tracks and len(tracks) > index:
                return tracks[index]

    @maybe_cached
    async def fetch_first(self) -> JSON_DICT_TYPE | None:
        """Get the first track.

        Returns
        -------
        str
            The first track
        """
        return await self.fetch_index(0)

    async def fetch_random(self) -> JSON_DICT_TYPE | None:
        """Get a random track.

        Returns
        -------
        str
            A random track
        """
        return await self.fetch_index(random.randint(0, await self.size()))

    async def fetch_bulk(
        self, info: bool = False, name: bool = False, pluginInfo: bool = False, tracks: bool = False
    ) -> JSON_DICT_TYPE | None:
        """Get all tracks.

        Returns
        -------
        list[str]
            All tracks
        """
        columns = [QueryRow.identifier]
        if name:
            columns.append(QueryRow.name)
        if info:
            columns.append(QueryRow.info)
        if pluginInfo:
            columns.append(QueryRow.pluginInfo)
        if tracks:
            columns.append(QueryRow.tracks(TrackRow.encoded, TrackRow.info, TrackRow.pluginInfo, load_json=True))
        response = (
            await QueryRow.select(*columns)
            .where(QueryRow.identifier == self.id)
            .first()
            .output(load_json=True, nested=True)
        )
        return response if response else None
