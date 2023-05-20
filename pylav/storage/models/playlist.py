from __future__ import annotations

import contextlib
import gzip
import io
import pathlib
import random
import sys
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass

import aiohttp
import brotli  # type: ignore
import discord
import yaml
from dacite import from_dict

from pylav.compat import json
from pylav.constants.config import BROTLI_ENABLED, READ_CACHING_ENABLED
from pylav.constants.playlists import BUNDLED_PLAYLIST_IDS
from pylav.constants.regex import SQUARE_BRACKETS
from pylav.core.context import PyLavContext
from pylav.exceptions.playlist import InvalidPlaylistException
from pylav.helpers.singleton import SingletonCachedByKey
from pylav.logging import getLogger
from pylav.nodes.api.responses.track import Track
from pylav.storage.database.cache.decodators import maybe_cached
from pylav.storage.database.cache.model import CachedModel
from pylav.storage.database.tables.playlists import PlaylistRow
from pylav.storage.database.tables.tracks import TrackRow
from pylav.type_hints.bot import DISCORD_BOT_TYPE
from pylav.type_hints.dict_typing import JSON_DICT_TYPE

LOGGER = getLogger("PyLav.Database.Playlist")


try:
    from redbot.core.i18n import Translator  # type: ignore

    _ = Translator("PyLav", pathlib.Path(__file__))
except ImportError:
    Translator = None

    def _(string: str) -> str:
        return string


@dataclass(eq=True, slots=True, unsafe_hash=True, order=True, kw_only=True, frozen=True)
class Playlist(CachedModel, metaclass=SingletonCachedByKey):
    id: int

    def get_cache_key(self) -> str:
        return f"{self.id}"

    @maybe_cached
    async def exists(self) -> bool:
        """Check if the config exists.

        Returns
        -------
        bool
            Whether the config exists.
        """

        return await PlaylistRow.exists().where(PlaylistRow.id == self.id)

    @maybe_cached
    async def fetch_all(self) -> JSON_DICT_TYPE:
        """Fetch all playlists from the database.

        Returns
        -------
        dict
            The playlists.
        """
        data = (
            await PlaylistRow.select(
                PlaylistRow.id,
                PlaylistRow.name,
                PlaylistRow.tracks(TrackRow.encoded, TrackRow.info, TrackRow.pluginInfo, load_json=True),
                PlaylistRow.scope,
                PlaylistRow.author,
                PlaylistRow.url,
            )
            .where(PlaylistRow.id == self.id)
            .first()
            .output(load_json=True, nested=True)
        )
        return data or {
            "id": self.id,
            "name": PlaylistRow.name.default,
            "tracks": [],
            "scope": PlaylistRow.scope.default,
            "author": PlaylistRow.author.default,
            "url": PlaylistRow.url.default,
        }

    @maybe_cached
    async def fetch_scope(self) -> int | None:
        """Fetch the scope of the playlist.

        Returns
        -------
        int
            The scope of the playlist.
        """
        response = (
            await PlaylistRow.select(PlaylistRow.scope)
            .where(PlaylistRow.id == self.id)
            .first()
            .output(load_json=True, nested=True)
        )
        return response["scope"] if response else PlaylistRow.scope.default

    async def update_scope(self, scope: int):
        """Update the scope of the playlist.

        Parameters
        ----------
        scope : int
            The new scope of the playlist.
        """
        await PlaylistRow.insert(PlaylistRow(id=self.id, scope=scope)).on_conflict(
            action="DO UPDATE", target=PlaylistRow.id, values=[PlaylistRow.scope]
        )
        await self.update_cache((self.fetch_scope, scope), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_author(self) -> int | None:
        """Fetch the author of the playlist.

        Returns
        -------
        int
            The author of the playlist.
        """
        response = (
            await PlaylistRow.select(PlaylistRow.author)
            .where(PlaylistRow.id == self.id)
            .first()
            .output(load_json=True, nested=True)
        )
        return response["author"] if response else PlaylistRow.author.default

    async def update_author(self, author: int) -> None:
        """Update the author of the playlist.

        Parameters
        ----------
        author : int
            The new author of the playlist.
        """
        await PlaylistRow.insert(PlaylistRow(id=self.id, author=author)).on_conflict(
            action="DO UPDATE", target=PlaylistRow.id, values=[PlaylistRow.author]
        )
        await self.update_cache((self.fetch_author, author), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_name(self) -> str | None:
        """Fetch the name of the playlist.

        Returns
        -------
        str
            The name of the playlist.
        """
        response = (
            await PlaylistRow.select(PlaylistRow.name)
            .where(PlaylistRow.id == self.id)
            .first()
            .output(load_json=True, nested=True)
        )
        return response["name"] if response else PlaylistRow.name.default

    async def update_name(self, name: str) -> None:
        """Update the name of the playlist.

        Parameters
        ----------
        name : str
            The new name of the playlist.
        """
        await PlaylistRow.insert(PlaylistRow(id=self.id, name=name)).on_conflict(
            action="DO UPDATE", target=PlaylistRow.id, values=[PlaylistRow.name]
        )
        await self.update_cache((self.fetch_name, name), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_url(self) -> str | None:
        """Fetch the url of the playlist.

        Returns
        -------
        str
            The url of the playlist.
        """
        response = (
            await PlaylistRow.select(PlaylistRow.url)
            .where(PlaylistRow.id == self.id)
            .first()
            .output(load_json=True, nested=True)
        )
        return response["url"] if response else PlaylistRow.url.default

    async def update_url(self, url: str) -> None:
        """Update the url of the playlist.

        Parameters
        ----------
        url : str
            The new url of the playlist.
        """
        await PlaylistRow.insert(PlaylistRow(id=self.id, url=url)).on_conflict(
            action="DO UPDATE", target=PlaylistRow.id, values=[PlaylistRow.url]
        )
        await self.update_cache((self.fetch_url, url), (self.exists, True))
        await self.invalidate_cache(self.fetch_all)

    @maybe_cached
    async def fetch_tracks(self) -> list[str | JSON_DICT_TYPE]:
        """Fetch the tracks of the playlist.

        Returns
        -------
        list[str]
            The tracks of the playlist.
        """
        response = (
            await PlaylistRow.select(
                PlaylistRow.tracks(TrackRow.encoded, TrackRow.info, TrackRow.pluginInfo, load_json=True)
            )
            .where(PlaylistRow.id == self.id)
            .first()
            .output(load_json=True, nested=True)
        )
        data = response["tracks"] if response else []
        return data

    async def update_tracks(self, tracks: list[str | JSON_DICT_TYPE | Track]) -> None:
        """Update the tracks of the playlist.

        Parameters
        ----------
        tracks : list[str]
            The new tracks of the playlist.
        """
        playlist_row = await PlaylistRow.objects().get_or_create(PlaylistRow.id == self.id)
        try:
            old_tracks = await playlist_row.get_m2m(PlaylistRow.tracks)
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
            await playlist_row.remove_m2m(*old_tracks, m2m=PlaylistRow.tracks)
        if new_tracks:
            await playlist_row.add_m2m(*new_tracks, m2m=PlaylistRow.tracks)

        await self.invalidate_cache(self.fetch_tracks, self.fetch_first)
        await self.update_cache(
            (self.exists, True),
            (self.size, len(tracks)),
        )
        await self.invalidate_cache(self.fetch_all)

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

    async def add_track(self, tracks: list[str | Track | JSON_DICT_TYPE]) -> None:
        """Add a track to the playlist.

        Parameters
        ----------
        tracks : list[str | Track]
            The tracks to add.
        """
        playlist_row = await PlaylistRow.objects().get_or_create(PlaylistRow.id == self.id)
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
        if new_tracks:
            await playlist_row.add_m2m(*new_tracks, m2m=PlaylistRow.tracks)
        await self.invalidate_cache(self.fetch_tracks, self.fetch_all, self.size, self.fetch_first, self.exists)

    async def bulk_remove_tracks(self, tracks: list[str]) -> None:
        """Remove disc jockey users from the player.

        Parameters
        ----------
        tracks : list[str]
            The track to remove
        """
        if not tracks:
            return
        playlist = await PlaylistRow.objects().where(PlaylistRow.id == self.id).first()
        tracks = await TrackRow.objects().where(TrackRow.encoded.is_in(tracks))
        if tracks:
            await playlist.remove_m2m(*tracks, m2m=PlaylistRow.tracks)
        await self.invalidate_cache(self.fetch_tracks, self.fetch_all, self.size, self.fetch_first, self.exists)

    async def remove_track(self, track: str) -> None:
        """Remove a track from the playlist.

        Parameters
        ----------
        track : str
            The track to remove
        """
        return await self.bulk_remove_tracks([track])

    async def remove_all_tracks(self) -> None:
        """Remove all tracks from the playlist."""
        playlist = await PlaylistRow.objects().where(PlaylistRow.id == self.id).first()
        try:
            tracks = await playlist.get_m2m(PlaylistRow.tracks)
        except ValueError:
            tracks = []
        if tracks:
            await playlist.remove_m2m(*tracks, m2m=PlaylistRow.tracks)
        await self.update_cache((self.fetch_tracks, []), (self.size, 0), (self.exists, True), (self.fetch_first, None))
        await self.invalidate_cache(self.fetch_all)

    async def delete(self) -> None:
        """Delete the playlist from the database"""
        await PlaylistRow.delete().where(PlaylistRow.id == self.id)
        await self.invalidate_cache()

    async def can_manage(self, bot: DISCORD_BOT_TYPE, requester: discord.abc.User) -> bool:  # noqa
        """Check if the requester can manage the playlist.

        Parameters
        ----------
        bot : DISCORD_BOT_TYPE
            The bot instance.
        requester : discord.abc.User
            The requester.

        Returns
        -------
        bool
            Whether the requester can manage the playlist.
        """
        if self.id in BUNDLED_PLAYLIST_IDS:
            return False
        if requester.id in ((ids := getattr(bot, "owner_ids")) or ()) or requester.id == bot.owner_id:  # noqa
            return True
        if await self.fetch_scope() == bot.user.id:
            return False
        return await self.fetch_author() == requester.id

    async def get_scope_name(self, bot: DISCORD_BOT_TYPE, mention: bool = True, guild: discord.Guild = None) -> str:
        """Get the name of the scope of the playlist.

        Parameters
        ----------
        bot : DISCORD_BOT_TYPE
            The bot instance.
        mention : bool
            Whether to add a mention if it is mentionable.
        guild : discord.Guild
            The guild to get the scope name for.

        Returns
        -------
        str
            The name of the scope of the playlist.
        """
        original_scope = await self.fetch_scope()
        if bot.user.id == original_scope:
            return _("(Global) {user_name_variable_do_not_translate}").format(
                user_name_variable_do_not_translate=bot.user.mention if mention else bot.user
            )
        elif guild_ := bot.get_guild(original_scope):
            if guild_:
                guild = guild_
            return _("(Server) {guild_name_variable_do_not_translate}").format(
                guild_name_variable_do_not_translate=guild.name
            )
        elif guild and (channel := guild.get_channel_or_thread(original_scope)):
            return _("(Channel) {channel_name_variable_do_not_translate}").format(
                channel_name_variable_do_not_translate=channel.mention if mention else channel.name
            )
        elif (
            (guild := guild_ or guild)
            and (guild and (scope := guild.get_member(original_scope)))  # noqa
            or (scope := bot.get_user(original_scope))
        ):
            return _("(User) {user_name_variable_do_not_translate}").format(
                user_name_variable_do_not_translate=scope.mention if mention else scope
            )
        else:
            return _("(Invalid) {scope_name_variable_do_not_translate}").format(
                scope_name_variable_do_not_translate=original_scope
            )

    async def get_author_name(self, bot: DISCORD_BOT_TYPE, mention: bool = True) -> str | None:
        """Get the name of the author of the playlist.

        Parameters
        ----------
        bot : DISCORD_BOT_TYPE
            The bot instance.
        mention : bool
            Whether to add a mention if it is mentionable.

        Returns
        -------
        str | None
            The name of the author of the playlist.
        """
        author = await self.fetch_author()
        if user := bot.get_user(author):
            return f"{user.mention}" if mention else f"{user}"
        return f"{author}"

    async def get_name_formatted(self, with_url: bool = True, escape: bool = True) -> str:
        """Get the name of the playlist formatted.

        Parameters
        ----------
        with_url : bool
            Whether to include the url in the name.
        escape: bool
            Whether to markdown escape the response
        Returns
        -------
        str
            The formatted name.
        """
        name = SQUARE_BRACKETS.sub("", await self.fetch_name()).strip()
        if with_url:
            url = await self.fetch_url()
            if url and url.startswith("http"):
                return f"**[{discord.utils.escape_markdown(name) if escape else name}]({url})**"
        return f"**{discord.utils.escape_markdown(name) if escape else name}**"

    @contextlib.asynccontextmanager
    async def to_yaml(self, guild: discord.Guild) -> Iterator[tuple[io.BytesIO, str | None]]:
        """Serialize the playlist to a YAML file.

        yields a tuple of (io.BytesIO, bool) where the bool is whether the playlist file was compressed using Gzip

        Parameters
        ----------
        guild : discord.Guild
            The guild where the yaml will be sent to.

        Yields
        ------
        tuple[io.BytesIO, str | None]
            The YAML file and the compression type.
        """
        data = await self.fetch_all()
        name = data["name"]
        compression = None
        with io.BytesIO() as bio:
            yaml.safe_dump(data, bio, default_flow_style=False, sort_keys=False, encoding="utf-8")
            bio.seek(0)
            LOGGER.debug("SIZE UNCOMPRESSED playlist (%s): %s", name, sys.getsizeof(bio))
            if sys.getsizeof(bio) > guild.filesize_limit:
                with io.BytesIO() as cbio:
                    if BROTLI_ENABLED:
                        compression = "brotli"
                        cbio.write(brotli.compress(yaml.dump(data, encoding="utf-8")))
                    else:
                        compression = "gzip"
                        with gzip.GzipFile(fileobj=cbio, mode="wb", compresslevel=9) as gzip_file:
                            yaml.safe_dump(data, gzip_file, default_flow_style=False, sort_keys=False, encoding="utf-8")
                    cbio.seek(0)
                    LOGGER.debug("SIZE COMPRESSED playlist [%s] (%s): %s", compression, name, sys.getsizeof(cbio))
                    yield cbio, compression
                    return
            yield bio, compression

    async def bulk_update(
        self, scope: int, name: str, author: int, url: str | None, tracks: list[str | JSON_DICT_TYPE | Track]
    ) -> None:
        """Bulk update the playlist."""
        defaults = {
            PlaylistRow.name: name,
            PlaylistRow.author: author,
            PlaylistRow.scope: scope,
            PlaylistRow.url: url,
        }

        playlist_row = await PlaylistRow.objects().get_or_create(PlaylistRow.id == self.id, defaults)
        # noinspection PyProtectedMember
        if not playlist_row._was_created:
            await PlaylistRow.update(defaults).where(PlaylistRow.id == self.id)
        try:
            old_tracks = await playlist_row.get_m2m(PlaylistRow.tracks)
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
            await playlist_row.remove_m2m(*old_tracks, m2m=PlaylistRow.tracks)
        if new_tracks:
            await playlist_row.add_m2m(*new_tracks, m2m=PlaylistRow.tracks)
        await self.invalidate_cache()

    @classmethod
    async def from_yaml(cls, context: PyLavContext, scope: int, url: str) -> Playlist:
        """Deserialize a playlist from a YAML file.

        Parameters
        ----------
        context : PyLavContext
            The context.
        scope : int
            The scope of the playlist.
        url : str
            The url of the playlist.

        Returns
        -------
        Playlist
            The playlist.
        """
        try:
            async with aiohttp.ClientSession(auto_decompress=False, json_serialize=json.dumps) as session:
                async with session.get(url) as response:
                    data = await response.read()
                    if ".gz.pylav" in url:
                        data = gzip.decompress(data)
                    elif ".br.pylav" in url:
                        data = brotli.decompress(data)
                    data = yaml.safe_load(data)
        except Exception as e:
            raise InvalidPlaylistException(f"Invalid playlist file - {e}") from e
        playlist = cls(
            id=context.message.id,
        )
        await playlist.bulk_update(
            scope=scope, name=data["name"], url=data["url"], tracks=data["tracks"], author=context.author.id
        )
        return playlist

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
