from __future__ import annotations

from piccolo.utils.pydantic import create_pydantic_model

from pylav.sql.tables import bot, cache, equalizers, init, lib_config, nodes, player_states, players, playlists, queries
from pylav.sql.tables.bot import BotVersionRow
from pylav.sql.tables.cache import AioHttpCacheRow
from pylav.sql.tables.equalizers import EqualizerRow
from pylav.sql.tables.init import DB
from pylav.sql.tables.lib_config import LibConfigRow
from pylav.sql.tables.m2m import TrackToPlaylists, TrackToQueries
from pylav.sql.tables.nodes import NodeRow
from pylav.sql.tables.player_states import PlayerStateRow
from pylav.sql.tables.players import PlayerRow
from pylav.sql.tables.playlists import PlaylistRow
from pylav.sql.tables.queries import QueryRow
from pylav.sql.tables.tracks import TrackRow

__all__ = (
    "bot",
    "cache",
    "equalizers",
    "init",
    "lib_config",
    "nodes",
    "player_states",
    "players",
    "playlists",
    "queries",
    "BotVersionRow",
    "AioHttpCacheRow",
    "EqualizerRow",
    "DB",
    "LibConfigRow",
    "PlayerStateRow",
    "NodeRow",
    "PlayerRow",
    "PlaylistRow",
    "QueryRow",
    "TrackRow",
    "TrackToPlaylists",
    "TrackToQueries",
)

PlaylistPDModel = create_pydantic_model(PlaylistRow, nested=True, deserialize_json=True)
LibConfigPDModel = create_pydantic_model(LibConfigRow, nested=True, deserialize_json=True)
EqualizerPDModel = create_pydantic_model(EqualizerRow, nested=True, deserialize_json=True)
PlayerStatePDModel = create_pydantic_model(PlayerStateRow, nested=True, deserialize_json=True)
PlayerPDModel = create_pydantic_model(PlayerRow, nested=True, deserialize_json=True)
NodePDModel = create_pydantic_model(NodeRow, nested=True, deserialize_json=True)
QueryPDModel = create_pydantic_model(QueryRow, nested=True, deserialize_json=True)
BotVersioPDModel = create_pydantic_model(BotVersionRow, nested=True, deserialize_json=True)
AioHttpCachePDModel = create_pydantic_model(AioHttpCacheRow, nested=True, deserialize_json=True)
TrackPDModel = create_pydantic_model(TrackRow, nested=True, deserialize_json=True)
