from __future__ import annotations

import asyncio
import contextlib
import datetime
import pathlib
import typing
from collections import namedtuple
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

import discord
from discord.utils import utcnow

from pylav._logging import getLogger
from pylav.constants import BUNDLED_PLAYLIST_IDS
from pylav.envvars import (
    TASK_TIMER_UPDATE_BUNDLED_EXTERNAL_PLAYLISTS_DAYS,
    TASK_TIMER_UPDATE_BUNDLED_PLAYLISTS_DAYS,
    TASK_TIMER_UPDATE_EXTERNAL_PLAYLISTS_DAYS,
)
from pylav.exceptions import EntryNotFoundError
from pylav.sql import tables
from pylav.sql.models import PlaylistModel
from pylav.types import BotT
from pylav.utils import AsyncIter, PyLavContext

if TYPE_CHECKING:
    from pylav.client import Client

LOGGER = getLogger("PyLav.PlaylistConfigManager")
try:
    from redbot.core.i18n import Translator

    _ = Translator("PyLavPlayer", pathlib.Path(__file__))
except ImportError:
    _ = lambda x: x


class PlaylistConfigManager:
    __slots__ = ("_client",)

    def __init__(self, client: Client):
        self._client = client

    @property
    def client(self) -> Client:
        return self._client

    def get_playlist(self, id: int) -> PlaylistModel:
        return PlaylistModel(id=id)

    async def get_bundled_playlists(self) -> list[PlaylistModel]:
        return [self.get_playlist(playlist) for playlist in BUNDLED_PLAYLIST_IDS]

    async def get_playlist_by_name(self, playlist_name: str, limit: int = None) -> list[PlaylistModel]:
        where = tables.PlaylistRow.name.ilike(f"%{playlist_name.lower()}%")
        if limit is None:
            query = tables.PlaylistRow.raw(f"SELECT id FROM playlist WHERE {where.querystring}")
        else:
            query = tables.PlaylistRow.raw(
                f"SELECT id FROM playlist WHERE {where.querystring} " f"LIMIT {limit}",
            )
        playlists = await query
        if not playlists:
            raise EntryNotFoundError(
                _("Playlist with name {playlist_name} not found").format(playlist_name=playlist_name)
            )
        return [self.get_playlist(**playlist) for playlist in playlists]

    async def get_playlist_by_id(self, playlist_id: int | str) -> PlaylistModel:
        try:
            response = await tables.PlaylistRow.raw("SELECT id FROM playlist WHERE id = {}", int(playlist_id))
        except ValueError as e:
            raise EntryNotFoundError(f"Playlist with id {playlist_id} not found") from e
        if response:
            return self.get_playlist(**response[0])
        else:
            raise EntryNotFoundError(f"Playlist with id {playlist_id} not found")

    async def get_playlist_by_name_or_id(
        self, playlist_name_or_id: int | str, limit: int = None
    ) -> list[PlaylistModel]:
        try:
            return [await self.get_playlist_by_id(playlist_name_or_id)]
        except EntryNotFoundError:
            return await self.get_playlist_by_name(playlist_name_or_id, limit=limit)

    async def get_playlists_by_author(self, author: int, return_empty: bool = True) -> list[PlaylistModel]:
        playlists = await tables.PlaylistRow.raw("SELECT id FROM playlist WHERE author = {}", author)

        if playlists or return_empty:
            return [self.get_playlist(**playlist) for playlist in playlists]
        else:
            raise EntryNotFoundError(f"Playlist with author {author} not found")

    async def get_playlists_by_scope(self, scope: int, return_empty: bool = True) -> list[PlaylistModel]:
        playlists = await tables.PlaylistRow.raw("SELECT id FROM playlist WHERE scope = {}", scope)

        if playlists or return_empty:
            return [self.get_playlist(**playlist) for playlist in playlists]
        else:
            raise EntryNotFoundError(f"Playlist with scope {scope} not found")

    async def get_all_playlists(self) -> AsyncIterator[PlaylistModel]:
        playlists = await tables.PlaylistRow.raw("SELECT id FROM playlist")
        if playlists:
            for playlist in playlists:
                yield self.get_playlist(**playlist)

    async def get_external_playlists(self, *ids: int, ignore_ids: list[int] = None) -> AsyncIterator[PlaylistModel]:
        if ignore_ids is None:
            ignore_ids = []

        if ids and ignore_ids:

            for entry in await tables.PlaylistRow.raw(
                """SELECT id FROM playlist WHERE {}""".format(
                    (
                        tables.PlaylistRow.url.is_not_null()
                        & tables.PlaylistRow.id.in_(ids)
                        & tables.PlaylistRow.id.not_in(ignore_ids)
                    ).querystring,
                )
            ):
                yield self.get_playlist(**entry)
        elif ignore_ids:
            for entry in await tables.PlaylistRow.raw(
                f"""SELECT id FROM playlist WHERE
                    {(tables.PlaylistRow.url.is_not_null() & tables.PlaylistRow.id.not_in(ignore_ids)).querystring}"""
            ):
                yield self.get_playlist(**entry)
        else:
            for entry in await tables.PlaylistRow.raw(
                f"""SELECT id FROM playlist WHERE
                    {(tables.PlaylistRow.url.is_not_null() & tables.PlaylistRow.id.is_in(ignore_ids)).querystring}"""
            ):
                yield self.get_playlist(**entry)

    async def create_or_update_playlist(
        self, id: int, scope: int, author: int, name: str, url: str | None = None, tracks: list[str] = None
    ) -> PlaylistModel:

        playlist = self.get_playlist(id=id)
        await playlist.bulk_update(
            scope=scope,
            author=author,
            name=name,
            url=url,
            tracks=tracks or [],
        )
        return playlist

    async def delete_playlist(self, playlist_id: int) -> None:
        await self.get_playlist(id=playlist_id).delete()

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
        async with tables.DB.transaction():
            global_playlists = [
                p
                for p in await self.get_playlists_by_scope(scope=self._client.bot.user.id, return_empty=True)
                if (not empty or await p.size())
            ]
            user_playlists = [
                p
                for p in await self.get_playlists_by_scope(scope=requester, return_empty=True)
                if (not empty or await p.size())
            ]
            vc_playlists = []
            guild_playlists = []
            channel_playlists = []
            if vc is not None:
                vc_playlists = [
                    p
                    for p in await self.get_playlists_by_scope(scope=vc.id, return_empty=True)
                    if (not empty or await p.size())
                ]
            if guild is not None:
                guild_playlists = [
                    p
                    for p in await self.get_playlists_by_scope(scope=guild.id, return_empty=True)
                    if (not empty or await p.size())
                ]
            if channel is not None:
                channel_playlists = [
                    p
                    for p in await self.get_playlists_by_scope(scope=channel.id, return_empty=True)
                    if (not empty or await p.size())
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
        with contextlib.suppress(
            asyncio.exceptions.CancelledError,
        ):
            old_time_stamp = await self.client._config.fetch_next_execution_update_bundled_playlists()

            await self.client._config.update_next_execution_update_bundled_playlists(
                utcnow() + datetime.timedelta(days=TASK_TIMER_UPDATE_BUNDLED_PLAYLISTS_DAYS)
            )

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
            for playlist_id, (name, url) in id_filtered.items():
                try:
                    ctx = typing.cast(
                        PyLavContext,
                        namedtuple("PyLavContext", "message author")(
                            message=discord.Object(id=playlist_id), author=discord.Object(id=self._client.bot.user.id)
                        ),
                    )
                    playlist = await PlaylistModel.from_yaml(context=ctx, url=url, scope=self._client.bot.user.id)
                except Exception as exc:
                    LOGGER.error("Built-in playlist couldn't be parsed - %s, report this error", name, exc_info=exc)
                    playlist = None
                if not playlist:
                    await self.client._config.update_next_execution_update_bundled_playlists(old_time_stamp)
                    continue

    async def update_bundled_external_playlists(self, *ids: int) -> None:
        from pylav.query import Query

        with contextlib.suppress(
            asyncio.exceptions.CancelledError,
        ):
            old_time_stamp = await self.client._config.fetch_next_execution_update_bundled_external_playlists()
            await self.client._config.update_next_execution_update_bundled_external_playlists(
                utcnow() + datetime.timedelta(days=TASK_TIMER_UPDATE_BUNDLED_EXTERNAL_PLAYLISTS_DAYS)
            )

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
                        "Built-in external playlist couldn't be parsed - %s, report this error", name, exc_info=exc
                    )
                    data = None
                if not data:
                    await self.client._config.update_next_execution_update_bundled_external_playlists(old_time_stamp)
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

        with contextlib.suppress(
            asyncio.exceptions.CancelledError,
        ):
            await self.client._config.update_next_execution_update_external_playlists(
                utcnow() + datetime.timedelta(days=TASK_TIMER_UPDATE_EXTERNAL_PLAYLISTS_DAYS)
            )

            async for playlist in self.get_external_playlists(*ids, ignore_ids=BUNDLED_PLAYLIST_IDS):
                name = await playlist.fetch_name()
                url = await playlist.fetch_url()
                try:
                    LOGGER.info("Updating external playlist - %s (%s)", name, playlist.id)
                    query = await self.client.get_tracks(
                        await Query.from_string(url),
                        bypass_cache=True,
                    )
                    tracks_raw = query.get("tracks", [])
                    track_list = [t_ for t in tracks_raw if (t_ := t.get("track"))]
                    name = query.get("playlistInfo", {}).get("name")
                    if track_list:
                        await playlist.update_tracks(tracks=track_list)
                    if name:
                        await playlist.update_name(name)
                except Exception as exc:
                    LOGGER.error(
                        "External playlist couldn't be updated - %s (%s), report this error",
                        name,
                        playlist.id,
                        exc_info=exc,
                    )

    async def count(self) -> int:
        """Returns the number of playlists in the database."""
        response = await tables.PlaylistRow.raw(
            """
            SELECT COUNT(id) FROM playlist
            """
        )
        return response[0].get("count", 0) if response else 0
