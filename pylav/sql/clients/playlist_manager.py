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

import pylav.sql.tables.init
import pylav.sql.tables.playlists
from pylav._logging import getLogger
from pylav.constants import BUNDLED_PLAYLIST_IDS, BUNDLED_SPOTIFY_PLAYLIST_IDS
from pylav.envvars import (
    TASK_TIMER_UPDATE_BUNDLED_EXTERNAL_PLAYLISTS_DAYS,
    TASK_TIMER_UPDATE_BUNDLED_PLAYLISTS_DAYS,
    TASK_TIMER_UPDATE_EXTERNAL_PLAYLISTS_DAYS,
)
from pylav.exceptions import EntryNotFoundError
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

    def _(string: str) -> str:
        return string


class PlaylistConfigManager:
    __slots__ = ("_client",)

    def __init__(self, client: Client):
        self._client = client

    @property
    def client(self) -> Client:
        return self._client

    @staticmethod
    def get_playlist(id: int) -> PlaylistModel:
        return PlaylistModel(id=id)

    async def get_bundled_playlists(self) -> list[PlaylistModel]:
        return [p for playlist in BUNDLED_PLAYLIST_IDS if (p := self.get_playlist(playlist))]

    async def get_playlist_by_name(self, playlist_name: str, limit: int = None) -> list[PlaylistModel]:
        query = (
            pylav.sql.tables.playlists.PlaylistRow.select(pylav.sql.tables.playlists.PlaylistRow.id)
            .where(pylav.sql.tables.playlists.PlaylistRow.name.ilike(f"%{playlist_name.lower()}%"))
            .output(load_json=True, nested=True)
        )
        if limit is not None:
            query = query.limit(limit)
        playlists = await query
        if not playlists:
            raise EntryNotFoundError(
                _("Playlist with name {playlist_name} not found").format(playlist_name=playlist_name)
            )
        return [self.get_playlist(**playlist) for playlist in playlists]

    async def get_playlist_by_id(self, playlist_id: int | str) -> PlaylistModel:
        try:
            playlist_id = int(playlist_id)
            response = await pylav.sql.tables.playlists.PlaylistRow.exists().where(
                pylav.sql.tables.playlists.PlaylistRow.id == playlist_id
            )
        except ValueError as e:
            raise EntryNotFoundError(f"Playlist with id {playlist_id} not found") from e
        if response:
            return self.get_playlist(playlist_id)
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
        playlists = (
            await pylav.sql.tables.playlists.PlaylistRow.select(pylav.sql.tables.playlists.PlaylistRow.id)
            .where(pylav.sql.tables.playlists.PlaylistRow.author == author)
            .output(load_json=True, nested=True)
        )
        if playlists or return_empty:
            return [self.get_playlist(**playlist) for playlist in playlists]
        else:
            raise EntryNotFoundError(f"Playlist with author {author} not found")

    async def get_playlists_by_scope(self, scope: int, return_empty: bool = True) -> list[PlaylistModel]:
        playlists = (
            await pylav.sql.tables.playlists.PlaylistRow.select(pylav.sql.tables.playlists.PlaylistRow.id)
            .where(pylav.sql.tables.playlists.PlaylistRow.scope == scope)
            .output(load_json=True, nested=True)
        )
        if playlists or return_empty:
            return [self.get_playlist(**playlist) for playlist in playlists]
        else:
            raise EntryNotFoundError(f"Playlist with scope {scope} not found")

    async def get_all_playlists(self) -> AsyncIterator[PlaylistModel]:
        for entry in await pylav.sql.tables.playlists.PlaylistRow.select(
            pylav.sql.tables.playlists.PlaylistRow.id
        ).output(load_json=True, nested=True):
            yield self.get_playlist(**entry)

    async def get_external_playlists(self, *ids: int, ignore_ids: list[int] = None) -> AsyncIterator[PlaylistModel]:
        if ignore_ids is None:
            ignore_ids = []
        base_query = pylav.sql.tables.playlists.PlaylistRow.select(pylav.sql.tables.playlists.PlaylistRow.id).output(
            load_json=True, nested=True
        )
        if ids and ignore_ids:
            query = base_query.where(
                pylav.sql.tables.playlists.PlaylistRow.url.is_not_null()
                & pylav.sql.tables.playlists.PlaylistRow.id.in_(ids)
                & pylav.sql.tables.playlists.PlaylistRow.id.not_in(ignore_ids)
            )
        elif ignore_ids:
            query = base_query.where(
                pylav.sql.tables.playlists.PlaylistRow.url.is_not_null()
                & pylav.sql.tables.playlists.PlaylistRow.id.not_in(ignore_ids)
            )
        else:
            query = base_query.where(
                pylav.sql.tables.playlists.PlaylistRow.url.is_not_null()
                & pylav.sql.tables.playlists.PlaylistRow.id.is_in(ids)
            )

        for entry in await query:
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
            await self.client.node_manager.wait_until_ready()
            await self.client._maybe_wait_until_bundled_node(
                await self.client.lib_db_manager.get_config().fetch_enable_managed_node()
            )
            old_time_stamp = await self.client._config.fetch_next_execution_update_bundled_playlists()
            curated_data = {
                1: (
                    "[YT] Aikaterna's curated tracks",
                    "https://gist.githubusercontent.com/Drapersniper/"
                    "cbe10d7053c844f8c69637bb4fd9c5c3/raw/playlist.pylav",
                ),
                2: (
                    "[YT] Anime OPs/EDs",
                    "https://gist.githubusercontent.com/Drapersniper/"
                    "2ad7c4cdd4519d9707f1a65d685fb95f/raw/anime_pl.pylav",
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
            await self.client._config.update_next_execution_update_bundled_playlists(
                utcnow() + datetime.timedelta(days=TASK_TIMER_UPDATE_BUNDLED_PLAYLISTS_DAYS)
            )
            self.client._wait_for_playlists.set()

    async def update_bundled_external_playlists(self, *ids: int) -> None:
        from pylav.query import Query

        with contextlib.suppress(
            asyncio.exceptions.CancelledError,
        ):
            await self.client.node_manager.wait_until_ready()
            await self.client._maybe_wait_until_bundled_node(
                await self.client.lib_db_manager.get_config().fetch_enable_managed_node()
            )
            old_time_stamp = await self.client._config.fetch_next_execution_update_bundled_external_playlists()
            # NOTICE: Update the BUNDLED_PLAYLIST_IDS constant in the constants.py file
            curated_data = {
                1000001: (
                    # Predä
                    ("{sp_pl}2seaovjQuA2cMgltyLQUtd", "[SP] CYBER//", "SP")
                ),
                1000002: (
                    # Predä
                    ("{sp_pl}0rSd8LoXBD5tEBbSsbXqbc", "[SP] PHONK//", "SP")
                ),
                1000003: (
                    # Predä
                    ("{sp_pl}21trhbHm5hVgosPS1YpwSM", "[SP] bangers", "SP")
                ),
                1000004: ("{sp_pl}0BbMjMQZ43vtdz7al266XH", "[SP] ???", "SP"),
                2000001: ("{dz_pl}3155776842", "[DZ] Top Worldwide", "DZ"),
                2000002: ("{dz_pl}1652248171", "[DZ] Top Canada", "DZ"),
                2000003: ("{dz_pl}1362528775", "[DZ] Top South Africa", "DZ"),
                2000004: ("{dz_pl}1362527605", "[DZ] Top Venezuela", "DZ"),
                2000005: ("{dz_pl}1362526495", "[DZ] Top Ukraine", "DZ"),
                2000006: ("{dz_pl}1362525375", "[DZ] Top Tunisia", "DZ"),
                2000007: ("{dz_pl}1362524475", "[DZ] Top Thailand", "DZ"),
                2000008: ("{dz_pl}1362523615", "[DZ] Top El Salvador", "DZ"),
                2000009: ("{dz_pl}1362523075", "[DZ] Top Senegal", "DZ"),
                2000010: ("{dz_pl}1362522355", "[DZ] Top Slovenia", "DZ"),
                2000011: ("{dz_pl}1362521285", "[DZ] Top Saudi Arabia", "DZ"),
                2000012: ("{dz_pl}1362520135", "[DZ] Top Paraguay", "DZ"),
                2000013: ("{dz_pl}1362519755", "[DZ] Top Portugal", "DZ"),
                2000014: ("{dz_pl}1362518895", "[DZ] Top Philippines", "DZ"),
                2000015: ("{dz_pl}1362518525", "[DZ] Top Peru", "DZ"),
                2000016: ("{dz_pl}1362516565", "[DZ] Top Nigeria", "DZ"),
                2000017: ("{dz_pl}1362510315", "[DZ] Top South Korea", "DZ"),
                2000018: ("{dz_pl}1362511155", "[DZ] Top Lebanon", "DZ"),
                2000019: ("{dz_pl}1362512715", "[DZ] Top Morocco", "DZ"),
                2000020: ("{dz_pl}1362515675", "[DZ] Top Malaysia", "DZ"),
                2000021: ("{dz_pl}1362509215", "[DZ] Top Kenya", "DZ"),
                2000022: ("{dz_pl}1362508955", "[DZ] Top Japan", "DZ"),
                2000023: ("{dz_pl}1362508765", "[DZ] Top Jordan", "DZ"),
                2000024: ("{dz_pl}1362508575", "[DZ] Top Jamaica", "DZ"),
                2000025: ("{dz_pl}1362501235", "[DZ] Top Ecuador", "DZ"),
                2000026: ("{dz_pl}1362501615", "[DZ] Top Egypt", "DZ"),
                2000027: ("{dz_pl}1362506695", "[DZ] Top Hungary", "DZ"),
                2000028: ("{dz_pl}1362507345", "[DZ] Top Israel", "DZ"),
                2000029: ("{dz_pl}1362501015", "[DZ] Top Algeria", "DZ"),
                2000030: ("{dz_pl}1362497945", "[DZ] Top Ivory Coast", "DZ"),
                2000031: ("{dz_pl}1362495515", "[DZ] Top Bolivia", "DZ"),
                2000032: ("{dz_pl}1362494565", "[DZ] Top Bulgaria", "DZ"),
                2000033: ("{dz_pl}1362491345", "[DZ] Top United Arab Emirates", "DZ"),
                2000034: ("{dz_pl}1313621735", "[DZ] Top USA", "DZ"),
                2000035: ("{dz_pl}1313620765", "[DZ] Top Singapore", "DZ"),
                2000036: ("{dz_pl}1313620305", "[DZ] Top Sweden", "DZ"),
                2000037: ("{dz_pl}1313619885", "[DZ] Top Norway", "DZ"),
                2000038: ("{dz_pl}1313619455", "[DZ] Top Ireland", "DZ"),
                2000039: ("{dz_pl}1313618905", "[DZ] Top Denmark", "DZ"),
                2000040: ("{dz_pl}1313618455", "[DZ] Top Costa Rica", "DZ"),
                2000041: ("{dz_pl}1313617925", "[DZ] Top Switzerland", "DZ"),
                2000042: ("{dz_pl}1313616925", "[DZ] Top Australia", "DZ"),
                2000043: ("{dz_pl}1313615765", "[DZ] Top Austria", "DZ"),
                2000044: ("{dz_pl}1279119721", "[DZ] Top Argentina", "DZ"),
                2000045: ("{dz_pl}1279119121", "[DZ] Top Chile", "DZ"),
                2000046: ("{dz_pl}1279118671", "[DZ] Top Guatemala", "DZ"),
                2000047: ("{dz_pl}1279117071", "[DZ] Top Romania", "DZ"),
                2000048: ("{dz_pl}1266973701", "[DZ] Top Slovakia", "DZ"),
                2000049: ("{dz_pl}1266972981", "[DZ] Top Serbia", "DZ"),
                2000050: ("{dz_pl}1266972311", "[DZ] Top Poland", "DZ"),
                2000051: ("{dz_pl}1266971851", "[DZ] Top Netherlands", "DZ"),
                2000052: ("{dz_pl}1266971131", "[DZ] Top Croatia", "DZ"),
                2000053: ("{dz_pl}1266969571", "[DZ] Top Czech Republic", "DZ"),
                2000054: ("{dz_pl}1266968331", "[DZ] Top Belgium", "DZ"),
                2000055: ("{dz_pl}1221037511", "[DZ] Top Latvia", "DZ"),
                2000056: ("{dz_pl}1221037371", "[DZ] Top Lithuania", "DZ"),
                2000057: ("{dz_pl}1221037201", "[DZ] Top Estonia", "DZ"),
                2000058: ("{dz_pl}1221034071", "[DZ] Top Finland", "DZ"),
                2000059: ("{dz_pl}1116190301", "[DZ] Top Honduras", "DZ"),
                2000060: ("{dz_pl}1116190041", "[DZ] Top Spain", "DZ"),
                2000061: ("{dz_pl}1116189381", "[DZ] Top Russia", "DZ"),
                2000062: ("{dz_pl}1116189071", "[DZ] Top Turkey", "DZ"),
                2000063: ("{dz_pl}1116188761", "[DZ] Top Indonesia", "DZ"),
                2000064: ("{dz_pl}1116188451", "[DZ] Top Colombia", "DZ"),
                2000065: ("{dz_pl}1116187241", "[DZ] Top Italy", "DZ"),
                2000066: ("{dz_pl}1111143121", "[DZ] Top Germany", "DZ"),
                2000067: ("{dz_pl}1111142361", "[DZ] Top Mexico", "DZ"),
                2000068: ("{dz_pl}1111142221", "[DZ] Top UK", "DZ"),
                2000069: ("{dz_pl}1111141961", "[DZ] Top Brazil", "DZ"),
                2000070: ("{dz_pl}1111141961", "[DZ] Top France", "DZ"),
                2000071: (
                    "{dz_pl}7490833544",
                    "[DZ] Best Anime Openings, Endings & Inserts",
                    "DZ",
                ),
                2000072: ("{dz_pl}5206929684", "[DZ] Japan Anime Hits", "DZ"),
            }
            id_filtered = {id: curated_data[id] for id in ids}
            if not id_filtered:
                id_filtered = curated_data
            for id, (url, name, source) in id_filtered.items():
                if (
                    id in BUNDLED_SPOTIFY_PLAYLIST_IDS
                    and (self.client._spotify_auth and self.client._spotify_auth.client_id)
                    or not self.client._spotify_auth
                ):
                    continue
                if "dz_pl" in url:
                    url = url.replace("{dz_pl}", "https://www.deezer.com/en/playlist/")
                elif "sp_pl" in url:
                    url = url.replace("{sp_pl}", "https://open.spotify.com/playlist/")

                track_list = []
                try:
                    LOGGER.info("Updating bundled external playlist - %s", id)
                    data = await self.client.get_tracks(await Query.from_string(url), bypass_cache=True)
                    name = f"[{source}] {data.playlistInfo.name}" if data.playlistInfo.name else name
                    tracks_raw = data.tracks
                    track_list = [t_ for t in tracks_raw if (t_ := t.encoded)]
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
            await self.client._config.update_next_execution_update_bundled_external_playlists(
                utcnow() + datetime.timedelta(days=TASK_TIMER_UPDATE_BUNDLED_EXTERNAL_PLAYLISTS_DAYS)
            )

    async def update_external_playlists(self, *ids: int) -> None:
        from pylav.constants import BUNDLED_PLAYLIST_IDS
        from pylav.query import Query

        with contextlib.suppress(
            asyncio.exceptions.CancelledError,
        ):
            await self.client.node_manager.wait_until_ready()
            await self.client._maybe_wait_until_bundled_node(
                await self.client.lib_db_manager.get_config().fetch_enable_managed_node()
            )

            async for playlist in self.get_external_playlists(*ids, ignore_ids=BUNDLED_PLAYLIST_IDS):
                name = await playlist.fetch_name()
                url = await playlist.fetch_url()
                try:
                    LOGGER.info("Updating external playlist - %s (%s)", name, playlist.id)
                    response = await self.client.get_tracks(
                        await Query.from_string(url),
                        bypass_cache=True,
                    )
                    tracks_raw = response.tracks
                    track_list = [t_ for t in tracks_raw if (t_ := t.encoded)]
                    name = response.playlistInfo.name
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
            await self.client._config.update_next_execution_update_external_playlists(
                utcnow() + datetime.timedelta(days=TASK_TIMER_UPDATE_EXTERNAL_PLAYLISTS_DAYS)
            )

    @staticmethod
    async def count() -> int:
        """Returns the number of playlists in the database."""
        return await pylav.sql.tables.playlists.PlaylistRow.count()
