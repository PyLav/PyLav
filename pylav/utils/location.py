from __future__ import annotations

import asyncio
import socket
from math import atan2, cos, radians, sin, sqrt

import aiohttp
from yarl import URL

from pylav.compat import json
from pylav.constants.coordinates import REGION_TO_COUNTRY_COORDINATE_MAPPING


def distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the distance between two coordinates on the earth"""
    dlat = radians(lat2) - radians(lat1)
    dlon = radians(lon2) - radians(lon1)
    a = sin(dlat / 2) * sin(dlat / 2) + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) * sin(dlon / 2)
    return 6371 * 2 * atan2(sqrt(a), sqrt(1 - a))


async def closest(
    data: dict[str, tuple[float, float]], compare_to: tuple[float, float], *, region_pool: set[str] | None = None
) -> tuple[str, tuple[float, float]]:
    """Get the closest region to the given coordinates"""
    if region_pool is None:
        region_pool = set()
    entries = [(k, v) for k, v in data.items() if not region_pool or k in region_pool]
    return min(
        entries,
        key=lambda p: distance(compare_to[0], compare_to[1], p[1][0], p[1][1]),
    )


async def get_closest_region_name_and_coordinate(
    lat: float, lon: float, region_pool: set[str] | None = None
) -> tuple[str, tuple[float, float]]:
    """Get the closest region name and coordinate to the given coordinates"""
    closest_region, closest_coordinates = await closest(
        REGION_TO_COUNTRY_COORDINATE_MAPPING, compare_to=(lat, lon), region_pool=region_pool
    )
    name, coordinate = next(
        iter((k, v) for k, v in REGION_TO_COUNTRY_COORDINATE_MAPPING.items() if v == closest_coordinates)
    )
    return name, coordinate


async def get_coordinates(ip: str | None = None) -> tuple[float, ...]:
    """Get the coordinates of the given ip address"""
    url = URL("https://ipinfo.io")
    if ip:
        url /= ip
    url /= "json"
    async with aiohttp.ClientSession(json_serialize=json.dumps) as session:
        async with session.get(url) as response:
            data = await response.json(loads=json.loads)
            return tuple(map(float, data["loc"].split(",")))


async def get_closest_discord_region(host: str | None = None) -> tuple[str, tuple[float, float]]:
    """Get the closest discord region to the given host"""
    try:
        if host is None or host in ["localhost", "127.0.0.1", "::1", "0.0.0.0", "::"]:
            host_ip = None
        else:
            host_ip = await asyncio.to_thread(socket.gethostbyname, host)
    except Exception:  # noqa
        host_ip = None  # If there's any issues getting the ip from the hostname, just use the host ip
    try:
        latitude, longitude = await get_coordinates(host_ip)
        return await get_closest_region_name_and_coordinate(lat=latitude, lon=longitude)
    except Exception:  # noqa
        return "unknown_pylav", (0, 0)
