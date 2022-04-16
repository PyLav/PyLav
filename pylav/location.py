from __future__ import annotations

import asyncio
import socket
from math import asin, cos, sqrt

import aiohttp
import ujson

from pylav.constants import REGION_TO_COUNTRY_COORDINATE_MAPPING


def distance(lat1, lon1, lat2, lon2):
    p = 0.017453292519943295
    hav = 0.5 - cos((lat2 - lat1) * p) / 2 + cos(lat1 * p) * cos(lat2 * p) * (1 - cos((lon2 - lon1) * p)) / 2
    return 12742 * asin(sqrt(hav))


def closest(data, v):
    return min(data, key=lambda p: distance(v[0], v[1], p[0], p[1]))


def get_closest_region_name(lat, lon):
    closest_coordinates = closest(REGION_TO_COUNTRY_COORDINATE_MAPPING.values(), (lat, lon))
    return next(k for k, v in REGION_TO_COUNTRY_COORDINATE_MAPPING.items() if v == closest_coordinates)


async def get_coordinates(ip: str | None = None):
    url = "http://ipinfo.io/json"
    if ip:
        url = f"http://ipinfo.io/{ip}/json"

    async with aiohttp.ClientSession(json_serialize=ujson.dumps) as session:
        async with session.get(url) as response:
            data = await response.json(loads=ujson.loads)
            return tuple(map(float, data["loc"].split(",")))


async def get_closest_discord_region(host: str | None = None):
    try:
        host_ip = await asyncio.to_thread(socket.gethostbyname, host)
    except Exception:
        host_ip = None  # If there's any issues getting the ip from the hostname, just use the host ip
    try:
        loc = await get_coordinates(host_ip)
        return get_closest_region_name(*loc)
    except Exception:
        return "london"
