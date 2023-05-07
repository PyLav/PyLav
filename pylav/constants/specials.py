from __future__ import annotations

from pylav._internals.functions import fix

_MAPPING = {
    2: ([0, 2, 5], 5),
    1: ([0, 1, 4], 5),
    3: ([0, 1, 4], 5),
    0: ([0, 1, 4, 5], 5),
}


__ZERO__ = fix("Al0YW" "MHp2Zg" "-1d5G", _MAPPING[2], e=True)
# noinspection SpellCheckingInspection
__MOMONGA__ = fix("ZiL4Z" "NTh3Yw" "Y8prT", _MAPPING[1], e=True)
__LIGHT__ = fix("Id58Z" "OW5hMQ" "Hdv24", _MAPPING[0], e=True)
__SEPHIROTH__ = fix("9-Diz" "ZzRlbA" "8Q4H2", _MAPPING[2], e=True)


ANIME = b"|".join([__SEPHIROTH__, __MOMONGA__, __ZERO__, __LIGHT__])
__all__ = ("ANIME",)
