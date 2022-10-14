from __future__ import annotations

from piccolo.utils.pydantic import create_pydantic_model

from pylav.sql.tables.bot import BotVersionRow as BotVersionRow
from pylav.sql.tables.cache import AioHttpCacheRow as AioHttpCacheRow
from pylav.sql.tables.equalizers import EqualizerRow as EqualizerRow
from pylav.sql.tables.init import DB as DB
from pylav.sql.tables.init import run_low_level_migrations as run_low_level_migrations
from pylav.sql.tables.lib_config import LibConfigRow as LibConfigRow
from pylav.sql.tables.nodes import NodeRow as NodeRow
from pylav.sql.tables.player_states import PlayerStateRow as PlayerStateRow
from pylav.sql.tables.players import PlayerRow as PlayerRow
from pylav.sql.tables.playlists import PlaylistRow as PlaylistRow
from pylav.sql.tables.queries import QueryRow as QueryRow

PlaylistPDModel = create_pydantic_model(PlaylistRow, nested=True, deserialize_json=True)
LibConfigPDModel = create_pydantic_model(LibConfigRow, nested=True, deserialize_json=True)
EqualizerPDModel = create_pydantic_model(EqualizerRow, nested=True, deserialize_json=True)
PlayerStatePDModel = create_pydantic_model(PlayerStateRow, nested=True, deserialize_json=True)
PlayerPDModel = create_pydantic_model(PlayerRow, nested=True, deserialize_json=True)
NodePDModel = create_pydantic_model(NodeRow, nested=True, deserialize_json=True)
QueryPDModel = create_pydantic_model(QueryRow, nested=True, deserialize_json=True)
BotVersioPDModel = create_pydantic_model(BotVersionRow, nested=True, deserialize_json=True)
AioHttpCachePDModel = create_pydantic_model(AioHttpCacheRow, nested=True, deserialize_json=True)
