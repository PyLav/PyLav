__all__ = ("__VERSION__", "__version__", "sql")
__version__ = __VERSION__ = "0.11.19.1"
__ZERO__ = b"MHp2Zg=="
__MOMONGA__ = b"NTh3Yw=="
__LIGHT__ = b"|OW5hMQ=="
__SEPHIROTH__ = b"ZzRlbA=="
_ANIME = b"|".join([__SEPHIROTH__, __MOMONGA__, __ZERO__, __LIGHT__])

from pylav import sql
from pylav._config import CONFIG_DIR as CONFIG_DIR
from pylav._logging import getLogger as getLogger
