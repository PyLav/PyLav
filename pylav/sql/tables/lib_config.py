from __future__ import annotations

from piccolo.columns import JSONB, BigInt, Boolean, Text, Timestamptz
from piccolo.table import Table

from pylav._config import CONFIG_DIR
from pylav.envvars import USE_BUNDLED_EXTERNAL_LAVA_LINK_NODE, USE_BUNDLED_EXTERNAL_PYLAV_NODE
from pylav.sql.tables.init import DB


class LibConfigRow(Table, db=DB, tablename="lib_config"):
    id = BigInt(index=True)
    bot = BigInt(primary_key=True, index=True)
    config_folder = Text(null=False, default=str(CONFIG_DIR))
    java_path = Text(null=False, default="java")
    enable_managed_node = Boolean(null=False, default=True)
    auto_update_managed_nodes = Boolean(null=False, default=True)
    localtrack_folder = Text(null=True, default=str(CONFIG_DIR / "music"))
    download_id = BigInt(index=True, default=0)
    update_bot_activity = Boolean(null=False, default=False)
    use_bundled_pylav_external = Boolean(null=False, default=USE_BUNDLED_EXTERNAL_PYLAV_NODE)
    use_bundled_lava_link_external = Boolean(null=False, default=USE_BUNDLED_EXTERNAL_LAVA_LINK_NODE)

    extras: JSONB = JSONB(null=False, default={})
    next_execution_update_bundled_playlists = Timestamptz(null=True, default=None)
    next_execution_update_bundled_external_playlists = Timestamptz(null=True, default=None)
    next_execution_update_external_playlists = Timestamptz(null=True, default=None)
