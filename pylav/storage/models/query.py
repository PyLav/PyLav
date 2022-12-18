from __future__ import annotations

import contextlib
import random
from dataclasses import dataclass
from datetime import datetime

from pylav.constants.config import READ_CACHING_ENABLED
from pylav.helpers.singleton import SingletonCachedByKey
from pylav.storage.database.cache.decodators import maybe_cached
from pylav.storage.database.cache.model import CachedModel
from pylav.storage.database.tables.queries import QueryRow
from pylav.storage.database.tables.tracks import TrackRow


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
    async def fetch_tracks(self) -> list[str]:
        """Get the tracks of the playlist.

        Returns
        -------
        list[str]
            The tracks of the playlist.
        """
        response = (
            await QueryRow.select(QueryRow.tracks(TrackRow.encoded, as_list=True, load_json=True))
            .where(QueryRow.identifier == self.id)
            .first()
            .output(load_json=True, nested=True)
        )
        return response["tracks"] if response else []

    async def update_tracks(self, tracks: list[str]):
        """Update the tracks of the playlist.

        Parameters
        ----------
        tracks: list[str]
            The tracks of the playlist.
        """
        query_row = await QueryRow.objects().get_or_create(QueryRow.identifier == self.id)
        try:
            old_tracks = await query_row.get_m2m(QueryRow.tracks)
        except ValueError:
            old_tracks = []
        new_tracks = []
        # TODO: Optimize this, after https://github.com/piccolo-orm/piccolo/discussions/683 is answered or fixed
        with contextlib.suppress(Exception):
            for track_object in await self.client.decode_tracks(tracks, raise_on_failure=False):
                with contextlib.suppress(Exception):
                    new_tracks.append(
                        await TrackRow.get_or_create(track_object.encoded, track_object.info.to_database())
                    )
        if old_tracks:
            await query_row.remove_m2m(*old_tracks, m2m=QueryRow.tracks)
        if new_tracks:
            await query_row.add_m2m(*new_tracks, m2m=QueryRow.tracks)
        await self.update_cache(
            (self.fetch_tracks, tracks),
            (self.size, len(tracks)),
            (self.fetch_first, tracks[0] if tracks else None),
            (self.exists, True),
        )

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
        # TODO: When piccolo add support to on conflict clauses using RAW here is more efficient
        #  Tracking issue: https://github.com/piccolo-orm/piccolo/issues/252
        await QueryRow.raw(
            "INSERT INTO query (identifier, name) VALUES ({}, {}) ON CONFLICT (identifier) DO UPDATE SET name = "
            "EXCLUDED.name;",
            self.id,
            name,
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
        # TODO: When piccolo add support to on conflict clauses using RAW here is more efficient
        #  Tracking issue: https://github.com/piccolo-orm/piccolo/issues/252
        await QueryRow.raw(
            "INSERT INTO query (identifier, last_updated) "
            "VALUES ({}, {}) ON CONFLICT (identifier) "
            "DO UPDATE SET last_updated = EXCLUDED.last_updated;",
            self.id,
            QueryRow.last_updated.default.python(),
        )
        await self.update_cache(
            (self.fetch_last_updated, QueryRow.last_updated.default.python()),
            (self.exists, True),
        )

    async def bulk_update(self, tracks: list[str], name: str) -> None:
        """Bulk update the query.

        Parameters
        ----------
        tracks: list[str]
            The tracks of the playlist.
        name: str
            The name of the playlist
        """
        defaults = {QueryRow.name: name}
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
        with contextlib.suppress(Exception):
            for track_object in await self.client.decode_tracks(tracks, raise_on_failure=False):
                with contextlib.suppress(Exception):
                    new_tracks.append(
                        await TrackRow.get_or_create(track_object.encoded, track_object.info.to_database())
                    )
        if old_tracks:
            await query_row.remove_m2m(*old_tracks, m2m=QueryRow.tracks)
        if new_tracks:
            await query_row.add_m2m(*new_tracks, m2m=QueryRow.tracks)
        await self.update_cache(
            (self.fetch_tracks, tracks),
            (self.size, len(tracks)),
            (self.fetch_first, tracks[0] if tracks else None),
            (self.fetch_name, name),
            (self.fetch_last_updated, QueryRow.last_updated.default.python()),
            (self.exists, True),
        )

    async def fetch_index(self, index: int) -> str | None:
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
    async def fetch_first(self) -> str | None:
        """Get the first track.

        Returns
        -------
        str
            The first track
        """
        return await self.fetch_index(0)

    async def fetch_random(self) -> str | None:
        """Get a random track.

        Returns
        -------
        str
            A random track
        """
        return await self.fetch_index(random.randint(0, await self.size()))
