from __future__ import annotations

from logging import getLogger
from typing import TYPE_CHECKING, AsyncIterator

from pylav.exceptions import EntryNotFoundError
from pylav.sql.models import PlaylistModel
from pylav.sql.tables import PlaylistRow

if TYPE_CHECKING:
    from pylav.client import Client

LOGGER = getLogger("red.PyLink.LibConfigManager")


class PlaylistConfigManager:
    def __init__(self, client: Client):
        self._client = client

    @property
    def client(self) -> Client:
        return self._client

    async def get_playlist_by_name(self, playlist_name: str, limit: int = None) -> list[PlaylistModel]:
        if limit is None:
            playlist = await PlaylistRow.select().where(PlaylistRow.name == playlist_name).first()
            if not playlist:
                raise EntryNotFoundError(f"Playlist with name {playlist_name} not found")
            return [PlaylistModel(**playlist)]
        else:
            playlists = await PlaylistRow.select().where(PlaylistRow.name == playlist_name).limit(limit)
            if not playlists:
                raise EntryNotFoundError(f"Playlist with name {playlist_name} not found")
            return [PlaylistModel(**playlist.to_dict()) for playlist in playlists]

    @staticmethod
    async def get_playlist_by_id(playlist_id: int) -> PlaylistModel:
        try:
            playlist_id = int(playlist_id)
        except ValueError:
            raise EntryNotFoundError(f"Playlist with id {playlist_id} not found")
        playlist = await PlaylistRow.select().where(PlaylistRow.id == playlist_id).limit(1).first()
        if not playlist:
            raise EntryNotFoundError(f"Playlist with ID {playlist_id} not found")
        return PlaylistModel(**playlist)

    async def get_playlist_by_name_or_id(
        self, playlist_name_or_id: int | str, limit: int = None
    ) -> list[PlaylistModel]:
        try:
            return [await self.get_playlist_by_id(playlist_name_or_id)]
        except EntryNotFoundError:
            return await self.get_playlist_by_name(playlist_name_or_id, limit=limit)

    @staticmethod
    async def get_playlists_by_author(author: int) -> list[PlaylistModel]:
        playlists = await PlaylistRow.select().where(PlaylistRow.author == author)
        if not playlists:
            raise EntryNotFoundError(f"Playlist with author {author} not found")
        return [PlaylistModel(**playlist.to_dict()) for playlist in playlists]

    @staticmethod
    async def get_playlists_by_scope(scope: int) -> list[PlaylistModel]:
        playlists = await PlaylistRow.select().where(PlaylistRow.scope == scope)
        if not playlists:
            raise EntryNotFoundError(f"Playlist with scope {scope} not found")
        return [PlaylistModel(**playlist.to_dict()) for playlist in playlists]

    @staticmethod
    async def get_all_playlists() -> AsyncIterator[PlaylistModel]:
        for entry in await PlaylistRow.select():
            yield PlaylistModel(**entry)

    # async with await PlaylistRow.select().batch(batch_size=10) as batch:
    #     async for entry in batch:
    #         yield PlaylistModel(**entry.to_dict())

    @staticmethod
    async def create_or_update_playlist(
        id: int, scope: int, author: int, name: str, url: str | None = None, tracks: list[str] = None
    ) -> PlaylistModel:
        values = {
            PlaylistRow.scope: scope,
            PlaylistRow.author: author,
            PlaylistRow.name: name,
            PlaylistRow.url: url,
            PlaylistRow.tracks: tracks or [],
        }
        playlist = (
            await PlaylistRow.objects().output(load_json=True).get_or_create(PlaylistRow.id == id, defaults=values)
        )
        if not playlist._was_created:  # noqa
            await PlaylistRow.update(values).where(PlaylistRow.id == id)
        return PlaylistModel(**playlist.to_dict())

    @staticmethod
    async def delete_playlist(playlist_id: int) -> None:
        await PlaylistRow.delete().where(PlaylistRow.id == playlist_id)
