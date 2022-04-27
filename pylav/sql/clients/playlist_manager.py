from __future__ import annotations

import time
from typing import TYPE_CHECKING, AsyncIterator

import discord
from red_commons.logging import getLogger

from pylav.exceptions import EntryNotFoundError
from pylav.sql.models import PlaylistModel
from pylav.sql.tables import PlaylistRow
from pylav.types import BotT
from pylav.utils import AsyncIter

if TYPE_CHECKING:
    from pylav.client import Client

LOGGER = getLogger("red.PyLink.PlaylistConfigManager")


class PlaylistConfigManager:
    def __init__(self, client: Client):
        self._client = client

    @property
    def client(self) -> Client:
        return self._client

    @staticmethod
    async def get_playlist_by_name(playlist_name: str, limit: int = None) -> list[PlaylistModel]:
        if limit is None:
            playlists = await PlaylistRow.select().where(PlaylistRow.name.ilike(f"%{playlist_name.lower()}%"))
            if not playlists:
                raise EntryNotFoundError(f"Playlist with name {playlist_name} not found")
            return [PlaylistModel(**playlist) for playlist in playlists]
        else:
            playlists = (
                await PlaylistRow.select().where(PlaylistRow.name.ilike(f"%{playlist_name.lower()}%")).limit(limit)
            )
            if not playlists:
                raise EntryNotFoundError(f"Playlist with name {playlist_name} not found")
            return [PlaylistModel(**playlist) for playlist in playlists]

    @staticmethod
    async def get_playlist_by_id(playlist_id: int | str) -> PlaylistModel:
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
        return [PlaylistModel(**playlist) for playlist in playlists]

    @staticmethod
    async def get_playlists_by_scope(scope: int) -> list[PlaylistModel]:
        playlists = await PlaylistRow.select().where(PlaylistRow.scope == scope)
        if not playlists:
            raise EntryNotFoundError(f"Playlist with scope {scope} not found")
        return [PlaylistModel(**playlist) for playlist in playlists]

    @staticmethod
    async def get_all_playlists() -> AsyncIterator[PlaylistModel]:
        for entry in await PlaylistRow.select():
            yield PlaylistModel(**entry)

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
        if not playlist._was_created:
            await PlaylistRow.update(values).where(PlaylistRow.id == id)
        return PlaylistModel(**playlist.to_dict())

    @staticmethod
    async def delete_playlist(playlist_id: int) -> None:
        await PlaylistRow.delete().where(PlaylistRow.id == playlist_id)

    @staticmethod
    async def get_all_playlists_by_author(author: int) -> AsyncIterator[PlaylistModel]:
        for entry in await PlaylistRow.select().where(PlaylistRow.author == author):
            yield PlaylistModel(**entry)

    @staticmethod
    async def get_all_playlists_by_scope(scope: int) -> AsyncIterator[PlaylistModel]:
        for entry in await PlaylistRow.select().where(PlaylistRow.scope == scope):
            yield PlaylistModel(**entry)

    @staticmethod
    async def get_all_playlists_by_scope_and_author(scope: int, author: int) -> AsyncIterator[PlaylistModel]:
        for entry in await PlaylistRow.select().where(PlaylistRow.scope == scope, PlaylistRow.author == author):
            yield PlaylistModel(**entry)

    async def get_global_playlists(self) -> AsyncIterator[PlaylistModel]:
        for entry in await PlaylistRow.select().where(PlaylistRow.scope == self._client.bot.user.id):  # type: ignore
            yield PlaylistModel(**entry)

    async def create_or_update_global_playlist(
        self, id: int, author: int, name: str, url: str | None = None, tracks: list[str] = None
    ) -> PlaylistModel:
        return await self.create_or_update_playlist(
            id=id, scope=self._client.bot.user.id, author=author, name=name, url=url, tracks=tracks
        )

    async def create_or_update_user_playlist(
        self, id: int, author: int, name: str, url: str | None = None, tracks: list[str] = None
    ) -> PlaylistModel:
        return await self.create_or_update_playlist(
            id=id, scope=author, author=author, name=name, url=url, tracks=tracks
        )

    async def create_or_update_channel_playlist(
        self, channel: discord.TextChannel, author: int, name: str, url: str | None = None, tracks: list[str] = None
    ) -> PlaylistModel:
        return await self.create_or_update_playlist(
            id=channel.id, scope=channel.id, author=author, name=name, url=url, tracks=tracks
        )

    async def create_or_update_guild_playlist(
        self, guild: discord.Guild, author: int, name: str, url: str | None = None, tracks: list[str] = None
    ) -> PlaylistModel:
        return await self.create_or_update_playlist(
            id=guild.id, scope=guild.id, author=author, name=name, url=url, tracks=tracks
        )

    async def create_or_update_vc_playlist(
        self, vc: discord.VoiceChannel, author: int, name: str, url: str | None = None, tracks: list[str] = None
    ) -> PlaylistModel:
        return await self.create_or_update_playlist(
            id=vc.id, scope=vc.id, author=author, name=name, url=url, tracks=tracks
        )

    async def get_all_for_user(
        self,
        requester: int,
        empty: bool = False,
        *,
        vc: discord.VoiceChannel | discord.StageChannel = None,
        guild: discord.Guild = None,
        channel: discord.TextChannel | discord.ForumChannel = None,
    ) -> tuple[list[PlaylistModel], list[PlaylistModel], list[PlaylistModel], list[PlaylistModel], list[PlaylistModel]]:
        """
        Gets all playlists a user has access to in a given context.

        Globals, User specific, Guild specific, Channel specific, VC specific.

        """
        global_playlists = [
            p async for p in self.get_all_playlists_by_scope(scope=self._client.bot.user.id) if (not empty or p.tracks)
        ]
        user_playlists = [p async for p in self.get_all_playlists_by_scope(scope=requester) if (not empty or p.tracks)]
        vc_playlists = []
        guild_playlists = []
        channel_playlists = []
        if vc is not None:
            vc_playlists = [p async for p in self.get_all_playlists_by_scope(scope=vc.id) if (not empty or p.tracks)]
        if guild is not None:
            guild_playlists = [
                p async for p in self.get_all_playlists_by_scope(scope=guild.id) if (not empty or p.tracks)
            ]
        if channel is not None:
            channel_playlists = [
                p async for p in self.get_all_playlists_by_scope(scope=channel.id) if (not empty or p.tracks)
            ]
        return global_playlists, user_playlists, guild_playlists, channel_playlists, vc_playlists

    async def get_manageable_playlists(
        self, requester: discord.abc.User, bot: BotT, *, name_or_id: str | None = None
    ) -> list[PlaylistModel]:
        if name_or_id:
            try:
                playlists = await self.get_playlist_by_name_or_id(name_or_id)
            except EntryNotFoundError:
                playlists = []
        else:
            try:
                playlists = [p async for p in self.get_all_playlists()]
            except EntryNotFoundError:
                playlists = []
        returning_list = []
        if playlists:
            async for playlist in AsyncIter(playlists):
                if await playlist.can_manage(requester=requester, bot=bot):
                    returning_list.append(playlist)
        return returning_list

    async def update_bundled_playlists(self):
        curated_data = {
            1: (
                "Aikaterna's curated tracks",
                "https://gist.githubusercontent.com/Drapersniper/cbe10d7053c844f8c69637bb4fd9c5c3/raw/playlist.txt",
            ),
            2: (
                "Anime OPs/EDs",
                "https://gist.githubusercontent.com/Drapersniper/2ad7c4cdd4519d9707f1a65d685fb95f/raw/anime_pl.txt",
            ),
        }
        for id, (name, url) in curated_data.items():
            async with self._client.session.get(
                url, params={"timestamp": int(time.time())}, headers={"content-type": "application/json"}
            ) as response:
                try:
                    data = await response.text()
                except Exception as exc:
                    LOGGER.error("Built-in playlist couldn't be parsed - %s, report this error.", name, exc_info=exc)
                    data = None
                if not data:
                    continue
                tracks = [t for t in map(str.strip, data.splitlines()) if t]
                if tracks:
                    await self.create_or_update_global_playlist(
                        id=id, name=name, tracks=tracks, author=self._client.bot.user.id
                    )
                else:
                    await self.delete_playlist(playlist_id=id)
