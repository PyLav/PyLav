from __future__ import annotations

import asyncio
import socket
import typing
from math import asin, cos, sqrt

import aiohttp
import asyncstdlib
import ujson

from pylav.constants import REGION_TO_COUNTRY_COORDINATE_MAPPING


def distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p = 0.017453292519943295
    hav = 0.5 - cos((lat2 - lat1) * p) / 2 + cos(lat1 * p) * cos(lat2 * p) * (1 - cos((lon2 - lon1) * p)) / 2
    return 12742 * asin(sqrt(hav))


async def closest(
    data: typing.ItemsView[str, tuple[float, float]], v: tuple[float, float], *, region_pool: set[str] = None
) -> tuple[str, tuple[float, float]]:
    if region_pool is None:
        region_pool = set()
    entries = typing.cast(
        list[tuple[str, tuple[float, float]]],
        await asyncstdlib.list(asyncstdlib.filter(lambda x: not region_pool or x[0] in region_pool, data)),
    )
    return await asyncstdlib.min(
        entries,
        key=lambda p: distance(v[0], v[1], p[1][0], p[1][1]),
    )


async def get_closest_region_name_and_coordinate(
    lat: float, lon: float, region_pool: set[str] = None
) -> tuple[str, tuple[float, float]]:
    closest_region, closest_coordinates = await closest(
        REGION_TO_COUNTRY_COORDINATE_MAPPING.items(), (lat, lon), region_pool=region_pool
    )
    name, coordinate = await asyncstdlib.anext(
        asyncstdlib.iter((k, v) for k, v in REGION_TO_COUNTRY_COORDINATE_MAPPING.items() if v == closest_coordinates)
    )
    return name, coordinate


async def get_coordinates(ip: str | None = None):
    url = f"https://ipinfo.io/{ip}/json" if ip else "https://ipinfo.io/json"
    async with aiohttp.ClientSession(json_serialize=ujson.dumps) as session:
        async with session.get(url) as response:
            data = await response.json(loads=ujson.loads)
            return tuple(map(float, data["loc"].split(",")))


async def get_closest_discord_region(host: str | None = None) -> tuple[str, tuple[float, float]]:
    try:
        if host in ["localhost", "127.0.0.1", "::1", "0.0.0.0", "::"]:
            host_ip = None
        else:
            host_ip = await asyncio.to_thread(socket.gethostbyname, host)
    except Exception:
        host_ip = None  # If there's any issues getting the ip from the hostname, just use the host ip
    try:
        loc = await get_coordinates(host_ip)
        return await get_closest_region_name_and_coordinate(*loc)
    except Exception:
        return "unknown_pylav", (0, 0)
