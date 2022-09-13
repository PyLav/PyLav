from __future__ import annotations

import asyncio
import contextlib
import socket
import typing

import aiohttp
from aiocache import Cache, cached

from pylav._logging import getLogger

LOGGER = getLogger("PyLav.RadioBrowser")


class Error(Exception):
    """Base class for all exceptions raised by this module"""


class RDNSLookupError(Error):
    __slots__ = ("ip", "port")

    def __init__(self, ip):
        self.ip = ip
        self.error_msg = f"There was a problem with performing " f"reverse dns lookup for ip: {ip}"
        super().__init__(self.error_msg)


@cached(ttl=3600, cache=Cache.MEMORY, namespace="radio_browser", key=f"{__name__}.fetch_servers")
async def fetch_servers() -> set[str]:
    """
    Get IP of all currently available `Radiob Browser` servers.
    Returns:
        set: List of IPs
    """
    ips = set()
    try:
        data = await asyncio.to_thread(socket.getaddrinfo, "all.api.radio-browser.info", 80, 0, 0, socket.IPPROTO_TCP)
    except socket.gaierror:
        return set()
    else:
        ips.update({i[4][0] for i in data})
    return typing.cast(set[str], ips)


@cached(ttl=600, cache=Cache.MEMORY, namespace="radio_browser")
async def rdns_lookup(ip: str) -> str:
    """
    Reverse DNS lookup.
    Returns:
        str: hostname
    """

    try:
        hostname, _, _ = await asyncio.to_thread(socket.gethostbyaddr, ip)
    except socket.herror as exc:
        raise RDNSLookupError(ip) from exc
    return hostname


@cached(ttl=600, cache=Cache.MEMORY, namespace="radio_browser", key=f"{__name__}.fetch_hosts")
async def fetch_hosts() -> list[str]:
    names = []
    servers = await fetch_servers()

    for ip in servers:
        try:
            host_name = await rdns_lookup(ip)
        except RDNSLookupError as exc:
            LOGGER.trace(exc.error_msg, exc_info=True)
        else:
            names.append(host_name)
    return names


@cached(ttl=300, cache=Cache.MEMORY, namespace="radio_browser", key=f"{__name__}.pick_base_url")
async def pick_base_url(session: aiohttp.ClientSession) -> str | None:
    hosts = await fetch_hosts()
    for host in hosts:
        with contextlib.suppress(Exception):
            async with session.get(f"https://{host}/json/stats") as response:
                if response.status == 200:
                    return f"https://{host}"
                LOGGER.verbose("Error interacting with %s: %s", host, response.status)
    LOGGER.error("All the following hosts for the RadioBrowser API are broken: %s", ", ".join(hosts))
