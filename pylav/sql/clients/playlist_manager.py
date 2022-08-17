from __future__ import annotations

import datetime
import time
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

import asyncstdlib
import discord

from pylav._logging import getLogger
from pylav.envvars import (
    TASK_TIMER_UPDATE_BUNDLED_EXTERNAL_PLAYLISTS,
    TASK_TIMER_UPDATE_BUNDLED_PLAYLISTS,
    TASK_TIMER_UPDATE_EXTERNAL_PLAYLISTS,
)
from pylav.exceptions import EntryNotFoundError
from pylav.sql import tables
from pylav.sql.models import PlaylistModel
from pylav.types import BotT
from pylav.utils import AsyncIter

if TYPE_CHECKING:
    from pylav.client import Client

LOGGER = getLogger("PyLav.PlaylistConfigManager")


class PlaylistConfigManager:
    def __init__(self, client: Client):
        self._client = client

    @property
    def client(self) -> Client:
        return self._client

    @staticmethod
    async def get_playlist_by_name(playlist_name: str, limit: int = None) -> list[PlaylistModel]:
        if limit is None:
            playlists = await tables.PlaylistRow.select().where(
                tables.PlaylistRow.name.ilike(f"%{playlist_name.lower()}%")
            )
        else:
            playlists = (
                await tables.PlaylistRow.select()
                .where(tables.PlaylistRow.name.ilike(f"%{playlist_name.lower()}%"))
                .limit(limit)
            )

        if not playlists:
            raise EntryNotFoundError(f"Playlist with name {playlist_name} not found")
        return [PlaylistModel(**playlist) for playlist in playlists]

    @staticmethod
    async def get_playlist_by_id(playlist_id: int | str) -> PlaylistModel:
        try:
            playlist_id = int(playlist_id)
        except ValueError as e:
            raise EntryNotFoundError(f"Playlist with id {playlist_id} not found") from e
        playlist = await tables.PlaylistRow.select().where(tables.PlaylistRow.id == playlist_id).limit(1).first()
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
        playlists = await tables.PlaylistRow.select().where(tables.PlaylistRow.author == author)
        if not playlists:
            raise EntryNotFoundError(f"Playlist with author {author} not found")
        return [PlaylistModel(**playlist) for playlist in playlists]

    @staticmethod
    async def get_playlists_by_scope(scope: int) -> list[PlaylistModel]:
        playlists = await tables.PlaylistRow.select().where(tables.PlaylistRow.scope == scope)
        if not playlists:
            raise EntryNotFoundError(f"Playlist with scope {scope} not found")
        return [PlaylistModel(**playlist) for playlist in playlists]

    @staticmethod
    async def get_all_playlists() -> AsyncIterator[PlaylistModel]:
        for entry in await tables.PlaylistRow.select():
            yield PlaylistModel(**entry)

    @staticmethod
    async def get_external_playlists(*ids: int, ignore_ids: list[int] = None) -> AsyncIterator[PlaylistModel]:
        if ignore_ids is None:
            ignore_ids = []

        if ids:
            for entry in await tables.PlaylistRow.select().where(
                (tables.PlaylistRow.url.is_not_null())
                & (tables.PlaylistRow.id.is_in(ids))
                & (tables.PlaylistRow.id.not_in(ignore_ids))
            ):
                yield PlaylistModel(**entry)
        else:
            for entry in await tables.PlaylistRow.select().where(
                (tables.PlaylistRow.url.is_not_null()) & (tables.PlaylistRow.id.not_in(ignore_ids))
            ):
                yield PlaylistModel(**entry)

    @staticmethod
    async def create_or_update_playlist(
        id: int, scope: int, author: int, name: str, url: str | None = None, tracks: list[str] = None
    ) -> PlaylistModel:
        values = {
            tables.PlaylistRow.scope: scope,
            tables.PlaylistRow.author: author,
            tables.PlaylistRow.name: name,
            tables.PlaylistRow.url: url,
            tables.PlaylistRow.tracks: tracks or [],
        }
        playlist = (
            await tables.PlaylistRow.objects()
            .output(load_json=True)
            .get_or_create(tables.PlaylistRow.id == id, defaults=values)
        )
        if not playlist._was_created:
            await tables.PlaylistRow.update(values).where(tables.PlaylistRow.id == id)
        return PlaylistModel(**playlist.to_dict())

    @staticmethod
    async def delete_playlist(playlist_id: int) -> None:
        await tables.PlaylistRow.delete().where(tables.PlaylistRow.id == playlist_id)

    @staticmethod
    async def get_all_playlists_by_author(author: int) -> AsyncIterator[PlaylistModel]:
        for entry in await tables.PlaylistRow.select().where(tables.PlaylistRow.author == author):
            yield PlaylistModel(**entry)

    @staticmethod
    async def get_all_playlists_by_scope(scope: int) -> AsyncIterator[PlaylistModel]:
        for entry in await tables.PlaylistRow.select().where(tables.PlaylistRow.scope == scope):
            yield PlaylistModel(**entry)

    @staticmethod
    async def get_all_playlists_by_scope_and_author(scope: int, author: int) -> AsyncIterator[PlaylistModel]:
        for entry in await tables.PlaylistRow.select().where(
            tables.PlaylistRow.scope == scope, tables.PlaylistRow.author == author
        ):
            yield PlaylistModel(**entry)

    async def get_global_playlists(self) -> AsyncIterator[PlaylistModel]:
        for entry in await tables.PlaylistRow.select().where(tables.PlaylistRow.scope == self._client.bot.user.id):  # type: ignore
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
        self,
        channel: discord.abc.MessageableChannel,
        author: int,
        name: str,
        url: str | None = None,
        tracks: list[str] = None,
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
        self,
        vc: discord.channel.VocalGuildChannel,
        author: int,
        name: str,
        url: str | None = None,
        tracks: list[str] = None,
    ) -> PlaylistModel:
        return await self.create_or_update_playlist(
            id=vc.id, scope=vc.id, author=author, name=name, url=url, tracks=tracks
        )

    async def get_all_for_user(
        self,
        requester: int,
        empty: bool = False,
        *,
        vc: discord.channel.VocalGuildChannel = None,
        guild: discord.Guild = None,
        channel: discord.abc.MessageableChannel = None,
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

    async def update_bundled_playlists(self, *ids: int) -> None:
        # NOTICE: Update the BUNDLED_PLAYLIST_IDS constant in the constants.py file
        self.client._config.next_execution_update_bundled_playlists = datetime.datetime.now(
            tz=datetime.timezone.utc
        ) + datetime.timedelta(days=TASK_TIMER_UPDATE_BUNDLED_PLAYLISTS)
        await self.client._config.save()
        curated_data = {
            1: (
                "Aikaterna's curated tracks",
                "https://gist.githubusercontent.com/Drapersniper/cbe10d7053c844f8c69637bb4fd9c5c3/raw/playlist.pylav",
            ),
            2: (
                "Anime OPs/EDs",
                "https://gist.githubusercontent.com/Drapersniper/2ad7c4cdd4519d9707f1a65d685fb95f/raw/anime_pl.pylav",
            ),
        }
        id_filtered = {id: curated_data[id] for id in ids}
        if not id_filtered:
            id_filtered = curated_data
        for id, (name, url) in id_filtered.items():
            async with self._client.cached_session.get(
                url, params={"timestamp": int(time.time())}, headers={"content-type": "application/json"}
            ) as response:
                try:
                    data = await response.text()
                except Exception as exc:
                    LOGGER.error("Built-in playlist couldn't be parsed - %s, report this error.", name, exc_info=exc)
                    data = None
                if not data:
                    continue
                if tracks := [t async for t in asyncstdlib.map(str.strip, data.splitlines()) if t]:
                    LOGGER.info("Updating bundled playlist - %s (%s)", name, id)
                    await self.create_or_update_global_playlist(
                        id=id, name=name, tracks=tracks, author=self._client.bot.user.id
                    )
                else:
                    await self.delete_playlist(playlist_id=id)

    async def update_bundled_external_playlists(self, *ids: int) -> None:
        from pylav.query import Query

        self.client._config.next_execution_update_bundled_external_playlists = datetime.datetime.now(
            tz=datetime.timezone.utc
        ) + datetime.timedelta(days=TASK_TIMER_UPDATE_BUNDLED_EXTERNAL_PLAYLISTS)
        await self.client._config.save()

        # NOTICE: Update the BUNDLED_PLAYLIST_IDS constant in the constants.py file
        curated_data = {
            1000001: (
                # CYBER//
                # Predä
                ("https://open.spotify.com/playlist/2seaovjQuA2cMgltyLQUtd", "CYBER//")
            ),
            1000002: (
                # PHONK//
                # Predä
                ("https://open.spotify.com/playlist/0rSd8LoXBD5tEBbSsbXqbc", "PHONK//")
            ),
            1000003: (  # bangers
                # Predä
                ("https://open.spotify.com/playlist/21trhbHm5hVgosPS1YpwSM", "bangers")
            ),
            1000004: ("https://open.spotify.com/playlist/0BbMjMQZ43vtdz7al266XH", "???"),
        }
        id_filtered = {id: curated_data[id] for id in ids}
        if not id_filtered:
            id_filtered = curated_data
        for id, (url, name) in id_filtered.items():
            track_list = []
            try:
                LOGGER.info("Updating bundled external playlist - %s", id)
                data = await self.client.get_tracks(await Query.from_string(url), bypass_cache=True)
                name = data.get("playlistInfo", {}).get("name") or name
                tracks_raw = data.get("tracks", [])
                track_list = [t_ for t in tracks_raw if (t_ := t.get("track"))]
            except Exception as exc:
                LOGGER.error(
                    "Built-in external playlist couldn't be parsed - %s, report this error.", name, exc_info=exc
                )
                data = None
            if not data:
                continue
            if track_list:
                await self.create_or_update_global_playlist(
                    id=id, name=name, tracks=track_list, author=self._client.bot.user.id, url=url
                )
            else:
                await self.delete_playlist(playlist_id=id)

    async def update_external_playlists(self, *ids: int) -> None:
        from pylav.constants import BUNDLED_PLAYLIST_IDS
        from pylav.query import Query

        self.client._config.next_execution_update_external_playlists = datetime.datetime.now(
            tz=datetime.timezone.utc
        ) + datetime.timedelta(days=TASK_TIMER_UPDATE_EXTERNAL_PLAYLISTS)
        await self.client._config.save()

        async for playlist in self.get_external_playlists(*ids, ignore_ids=BUNDLED_PLAYLIST_IDS):
            try:
                LOGGER.info("Updating external playlist - %s (%s)", playlist.name, playlist.id)
                query = await self.client.get_tracks(
                    await Query.from_string(playlist.url),
                    bypass_cache=True,
                )
                tracks_raw = query.get("tracks", [])
                track_list = [t_ for t in tracks_raw if (t_ := t.get("track"))]
                name = query.get("playlistInfo", {}).get("name") or playlist.name
                if track_list:
                    playlist.tracks = track_list
                    playlist.name = name
                    await playlist.save()
            except Exception as exc:
                LOGGER.error(
                    "External playlist couldn't be updated - %s (%s), report this error.",
                    playlist.name,
                    playlist.id,
                    exc_info=exc,
                )
