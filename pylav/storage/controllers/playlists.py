from __future__ import annotations

import asyncio
import contextlib
import datetime
import pathlib
import typing
from collections import namedtuple
from typing import TYPE_CHECKING

import asyncpg
import discord

from pylav.constants.config import (
    TASK_TIMER_UPDATE_BUNDLED_EXTERNAL_PLAYLISTS_DAYS,
    TASK_TIMER_UPDATE_BUNDLED_PLAYLISTS_DAYS,
    TASK_TIMER_UPDATE_EXTERNAL_PLAYLISTS_DAYS,
)
from pylav.constants.playlists import (
    BUNDLED_DEEZER_PLAYLIST_IDS,
    BUNDLED_EXTERNAL_PLAYLISTS,
    BUNDLED_PLAYLIST_IDS,
    BUNDLED_PYLAV_PLAYLISTS,
    BUNDLED_SPOTIFY_PLAYLIST_IDS,
)
from pylav.core.context import PyLavContext
from pylav.exceptions.database import EntryNotFoundException
from pylav.helpers.time import get_now_utc
from pylav.logging import getLogger
from pylav.nodes.api.responses.rest_api import PlaylistResponse
from pylav.players.query.obj import Query
from pylav.players.tracks.obj import Track
from pylav.storage.database.tables.playlists import PlaylistRow
from pylav.storage.models.playlist import Playlist
from pylav.type_hints.bot import DISCORD_BOT_TYPE
from pylav.type_hints.dict_typing import JSON_DICT_TYPE

if TYPE_CHECKING:
    from pylav.core.client import Client
LOGGER = getLogger("PyLav.Database.Controller.Playlist")


try:
    from redbot.core.i18n import Translator  # type: ignore

    _ = Translator("PyLav", pathlib.Path(__file__))
except ImportError:
    Translator = None

    def _(string: str) -> str:
        return string


class PlaylistController:
    __slots__ = ("_client",)

    def __init__(self, client: Client) -> None:
        self._client = client

    @property
    def client(self) -> Client:
        return self._client

    @staticmethod
    def get_playlist(**kwargs: typing.Any) -> Playlist:
        if identifier := kwargs.pop("identifier", kwargs.pop("id", None)):
            return Playlist(id=identifier)
        else:
            raise ValueError("Playlist identifier not provided")

    async def get_bundled_playlists(self) -> list[Playlist]:
        return [
            p for playlist in BUNDLED_PLAYLIST_IDS if (p := self.get_playlist(identifier=playlist)) and await p.exists()
        ]

    async def get_playlist_by_name(self, playlist_name: str, limit: int = None) -> list[Playlist]:
        query = (
            PlaylistRow.select(PlaylistRow.id)
            .where(PlaylistRow.name.ilike(f"%{playlist_name.lower()}%"))
            .output(load_json=True, nested=True)
        )
        if limit is not None:
            query = query.limit(limit)
        playlists = await query
        if not playlists:
            raise EntryNotFoundException(
                _("laylist with the name {playlist_name_variable_do_not_translate} was not found.").format(
                    playlist_name_variable_do_not_translate=playlist_name
                )
            )
        return [self.get_playlist(**playlist) for playlist in playlists]

    async def get_playlist_by_id(self, playlist_id: int | str) -> Playlist:
        try:
            playlist_id = int(playlist_id)
            response = await PlaylistRow.exists().where(PlaylistRow.id == playlist_id)
        except ValueError as e:
            raise EntryNotFoundException(f"Playlist with id {playlist_id} not found") from e
        if response:
            return self.get_playlist(identifier=playlist_id)
        else:
            raise EntryNotFoundException(f"Playlist with id {playlist_id} not found")

    async def get_playlist_by_name_or_id(self, playlist_name_or_id: int | str, limit: int = None) -> list[Playlist]:
        try:
            return [await self.get_playlist_by_id(playlist_name_or_id)]
        except EntryNotFoundException:
            return await self.get_playlist_by_name(playlist_name_or_id, limit=limit)

    async def get_playlists_by_author(self, author: int, return_empty: bool = True) -> list[Playlist]:
        playlists = (
            await PlaylistRow.select(PlaylistRow.id)
            .where(PlaylistRow.author == author)
            .output(load_json=True, nested=True)
        )
        if playlists or return_empty:
            return [self.get_playlist(**playlist) for playlist in playlists]
        else:
            raise EntryNotFoundException(f"Playlist with author {author} not found")

    async def get_playlists_by_scope(self, scope: int, return_empty: bool = True) -> list[Playlist]:
        playlists = (
            await PlaylistRow.select(PlaylistRow.id)
            .where(PlaylistRow.scope == scope)
            .output(load_json=True, nested=True)
        )
        if playlists or return_empty:
            return [self.get_playlist(**playlist) for playlist in playlists]
        else:
            raise EntryNotFoundException(f"Playlist with scope {scope} not found")

    async def get_all_playlists(self) -> typing.AsyncIterator[Playlist]:
        for entry in await PlaylistRow.select(PlaylistRow.id).output(load_json=True, nested=True):
            yield self.get_playlist(**entry)

    async def get_external_playlists(self, *ids: int, ignore_ids: list[int] = None) -> typing.AsyncIterator[Playlist]:
        if ignore_ids is None:
            ignore_ids = []
        base_query = PlaylistRow.select(PlaylistRow.id).output(load_json=True, nested=True)
        if ids and ignore_ids:
            query = base_query.where(
                PlaylistRow.url.is_not_null() & PlaylistRow.id.in_(ids) & PlaylistRow.id.not_in(ignore_ids)
            )
        elif ignore_ids:
            query = base_query.where(PlaylistRow.url.is_not_null() & PlaylistRow.id.not_in(ignore_ids))
        else:
            query = base_query.where(PlaylistRow.url.is_not_null() & PlaylistRow.id.is_in(ids))

        for entry in await query:
            yield self.get_playlist(**entry)

    async def create_or_update_playlist(
        self,
        identifier: int,
        scope: int,
        author: int,
        name: str,
        url: str | None = None,
        tracks: list[str | JSON_DICT_TYPE | Track] = None,
    ) -> Playlist:
        playlist = self.get_playlist(identifier=identifier)
        await playlist.bulk_update(
            scope=scope,
            author=author,
            name=name,
            url=url,
            tracks=tracks or [],
        )
        return playlist

    async def delete_playlist(self, playlist_id: int) -> None:
        await self.get_playlist(identifier=playlist_id).delete()

    async def create_or_update_global_playlist(
        self, identifier: int, author: int, name: str, url: str | None = None, tracks: list[str | Track] = None
    ) -> Playlist:
        return await self.create_or_update_playlist(
            identifier=identifier, scope=self._client.bot.user.id, author=author, name=name, url=url, tracks=tracks
        )

    async def create_or_update_user_playlist(
        self, identifier: int, author: int, name: str, url: str | None = None, tracks: list[str | Track] = None
    ) -> Playlist:
        return await self.create_or_update_playlist(
            identifier=identifier, scope=author, author=author, name=name, url=url, tracks=tracks
        )

    async def create_or_update_channel_playlist(
        self,
        channel: discord.abc.MessageableChannel,
        author: int,
        name: str,
        url: str | None = None,
        tracks: list[str] = None,
    ) -> Playlist:
        return await self.create_or_update_playlist(
            identifier=channel.id, scope=channel.id, author=author, name=name, url=url, tracks=tracks
        )

    async def create_or_update_guild_playlist(
        self, guild: discord.Guild, author: int, name: str, url: str | None = None, tracks: list[str] = None
    ) -> Playlist:
        return await self.create_or_update_playlist(
            identifier=guild.id, scope=guild.id, author=author, name=name, url=url, tracks=tracks
        )

    async def create_or_update_vc_playlist(
        self,
        vc: discord.channel.VocalGuildChannel,
        author: int,
        name: str,
        url: str | None = None,
        tracks: list[str] = None,
    ) -> Playlist:
        return await self.create_or_update_playlist(
            identifier=vc.id, scope=vc.id, author=author, name=name, url=url, tracks=tracks
        )

    async def get_all_for_user(
        self,
        requester: int,
        empty: bool = False,
        *,
        vc: discord.channel.VocalGuildChannel = None,
        guild: discord.Guild = None,
        channel: discord.abc.MessageableChannel = None,
    ) -> tuple[list[Playlist], list[Playlist], list[Playlist], list[Playlist], list[Playlist]]:
        """
        Gets all playlists a user has access to in a given context.
        Globals, User specific, Guild specific, Channel specific, VC specific.
        """
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
        self, requester: discord.abc.User, bot: DISCORD_BOT_TYPE, *, name_or_id: str | None = None
    ) -> list[Playlist]:
        if name_or_id:
            try:
                playlists = await self.get_playlist_by_name_or_id(name_or_id)
            except EntryNotFoundException:
                playlists = []
        else:
            try:
                playlists = [p async for p in self.get_all_playlists()]
            except EntryNotFoundException:
                playlists = []
        returning_list = []
        if playlists:
            for playlist in playlists:
                if await playlist.can_manage(requester=requester, bot=bot):
                    returning_list.append(playlist)
        return returning_list

    async def _update_bundled_playlists(self, playlist_id, url, source, name, old_time_stamp):
        try:
            ctx = typing.cast(
                PyLavContext,
                namedtuple("PyLavContext", "message author")(
                    message=discord.Object(id=playlist_id), author=discord.Object(id=self._client.bot.user.id)
                ),
            )
            playlist = await Playlist.from_yaml(context=ctx, url=url, scope=self._client.bot.user.id)
            LOGGER.info("Updating bundled playlist - %s - %s", playlist_id, f"[{source}] {name}")
        except Exception as exc:
            LOGGER.error(
                "Built-in playlist couldn't be parsed - %s, report this error",
                f"[{source}] {name}",
                exc_info=exc,
            )
            playlist = None
        if not playlist:
            # noinspection PyProtectedMember
            await self.client._config.update_next_execution_update_bundled_playlists(old_time_stamp)
            return

    async def update_bundled_playlists(self, *playlist_ids: int) -> None:
        # NOTICE: Update the BUNDLED_PLAYLIST_IDS constant in the constants.py file
        with contextlib.suppress(asyncio.exceptions.CancelledError, asyncpg.exceptions.CannotConnectNowError):
            await self.client.node_manager.wait_until_ready()
            # noinspection PyProtectedMember
            await self.client._maybe_wait_until_bundled_node(await self.client.managed_node_is_enabled())
            # noinspection PyProtectedMember
            old_time_stamp = await self.client._config.fetch_next_execution_update_bundled_playlists()
            id_filtered = {
                playlist_id: BUNDLED_PYLAV_PLAYLISTS[playlist_id]
                for playlist_id in playlist_ids
                if playlist_id in BUNDLED_PYLAV_PLAYLISTS
            }
            if not id_filtered:
                id_filtered = BUNDLED_PYLAV_PLAYLISTS
            count = 0
            tasks = []
            for playlist_id, (name, url, source) in id_filtered.items():
                tasks.append(self._update_bundled_playlists(playlist_id, url, source, name, old_time_stamp))
                if count % 10 == 0:
                    await asyncio.gather(*tasks)
                    tasks = []
                count += 1
            if tasks:
                await asyncio.gather(*tasks)
            # noinspection PyProtectedMember
            await self.client._config.update_next_execution_update_bundled_playlists(
                get_now_utc() + datetime.timedelta(days=TASK_TIMER_UPDATE_BUNDLED_PLAYLISTS_DAYS)
            )
            # noinspection PyProtectedMember
            self.client._wait_for_playlists.set()

            LOGGER.info("Finished updating bundled playlists")

    async def _update_bundled_external_playlist(self, playlist_id, album_playlist, identifier, name, old_time_stamp):
        if (playlist_id in BUNDLED_SPOTIFY_PLAYLIST_IDS and not self.client._spotify_auth) or (
            playlist_id in BUNDLED_DEEZER_PLAYLIST_IDS and not self.client._has_deezer_support
        ):
            return
        elif playlist_id in BUNDLED_SPOTIFY_PLAYLIST_IDS:
            url = f"https://open.spotify.com/{album_playlist}/{identifier}"
        elif playlist_id in BUNDLED_DEEZER_PLAYLIST_IDS:
            url = f"https://www.deezer.com/en/{album_playlist}/{identifier}"
        else:
            LOGGER.debug("Unknown playlist id: %s", playlist_id)
            return
        tracks_raw = []
        data = None
        try:
            LOGGER.info("Updating bundled external playlist - %s - %s", playlist_id, name)
            query = await Query.from_string(url)
            data: PlaylistResponse = await self.client.get_tracks(query, bypass_cache=True)
            name = (
                f"[{query.source_abbreviation}] {data.data.info.name}"
                if data.data.info.name
                else f"[{query.source_abbreviation}] {name}"
            )
            tracks_raw = data.data.tracks
        except Exception as exc:
            LOGGER.error("Built-in external playlist couldn't be parsed - %s, report this error", name, exc_info=exc)
            LOGGER.debug("Built-in external playlist couldn't be parsed - %s (%r)", name, data, exc_info=exc)
            data = None
        if not data:
            # noinspection PyProtectedMember
            await self.client._config.update_next_execution_update_bundled_external_playlists(old_time_stamp)
            return
        if tracks_raw:
            await self.create_or_update_global_playlist(
                identifier=playlist_id, name=name, tracks=tracks_raw, author=self._client.bot.user.id, url=url
            )
        else:
            await self.delete_playlist(playlist_id=playlist_id)

    async def update_bundled_external_playlists(self, *playlist_ids: int) -> None:
        with contextlib.suppress(asyncio.exceptions.CancelledError, asyncpg.exceptions.CannotConnectNowError):
            await self.client.node_manager.wait_until_ready()
            # noinspection PyProtectedMember
            await self.client._maybe_wait_until_bundled_node(await self.client.managed_node_is_enabled())
            # noinspection PyProtectedMember
            old_time_stamp = await self.client._config.fetch_next_execution_update_bundled_external_playlists()
            # NOTICE: Update the BUNDLED_PLAYLIST_IDS constant in the constants.py file
            id_filtered = {
                playlist_id: BUNDLED_EXTERNAL_PLAYLISTS[playlist_id]
                for playlist_id in playlist_ids
                if playlist_id in BUNDLED_EXTERNAL_PLAYLISTS
            }
            if not id_filtered:
                id_filtered = BUNDLED_EXTERNAL_PLAYLISTS
            tasks = []
            count = 0
            for playlist_id, (identifier, name, album_playlist) in id_filtered.items():
                tasks.append(
                    self._update_bundled_external_playlist(
                        playlist_id, album_playlist, identifier, name, old_time_stamp
                    )
                )
                if count % 10 == 0:
                    await asyncio.gather(*tasks)
                    tasks = []
                count += 1
            if tasks:
                await asyncio.gather(*tasks)

            # noinspection PyProtectedMember
            await self.client._config.update_next_execution_update_bundled_external_playlists(
                get_now_utc() + datetime.timedelta(days=TASK_TIMER_UPDATE_BUNDLED_EXTERNAL_PLAYLISTS_DAYS)
            )
            LOGGER.info("Finished updating bundled external playlists")

    async def update_external_playlists(self, *playlist_ids: int) -> None:
        with contextlib.suppress(asyncio.exceptions.CancelledError, asyncpg.exceptions.CannotConnectNowError):
            await self.client.node_manager.wait_until_ready()
            # noinspection PyProtectedMember
            await self.client._maybe_wait_until_bundled_node(await self.client.managed_node_is_enabled())
            count = 0
            tasks = []
            async for playlist in self.get_external_playlists(*playlist_ids, ignore_ids=BUNDLED_PLAYLIST_IDS):
                tasks.append(self._update_external_playlist(playlist))
                if count % 10 == 0:
                    await asyncio.gather(*tasks)
                    tasks = []
                count += 1
            if tasks:
                await asyncio.gather(*tasks)
            # noinspection PyProtectedMember
            await self.client._config.update_next_execution_update_external_playlists(
                get_now_utc() + datetime.timedelta(days=TASK_TIMER_UPDATE_EXTERNAL_PLAYLISTS_DAYS)
            )
            LOGGER.info("Finished updating external playlists")

    async def _update_external_playlist(self, playlist):
        name = await playlist.fetch_name()
        url = await playlist.fetch_url()
        query = await Query.from_string(url)
        try:
            LOGGER.info("Updating external playlist - %s (%s)", name, playlist.id)
            response: PlaylistResponse = await self.client.get_tracks(
                query,
                bypass_cache=True,
            )
            tracks_raw = response.data.tracks
            new_name = response.data.info.name
            new_name = f"[{query.source_abbreviation}] {new_name}" if new_name else None
            if tracks_raw:
                await playlist.update_tracks(tracks=tracks_raw)
            if new_name and new_name != name:
                await playlist.update_name(new_name)
        except Exception as exc:
            LOGGER.error(
                "External playlist couldn't be updated - %s (%s), report this error",
                name,
                playlist.id,
                exc_info=exc,
            )

    @staticmethod
    async def count() -> int:
        """Returns the number of playlists in the database."""
        return await PlaylistRow.count()
