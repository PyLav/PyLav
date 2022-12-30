from __future__ import annotations

import asyncio
import contextlib
import socket
import typing

import aiohttp
from cashews import Cache

from pylav.exceptions.base import PyLavException
from pylav.logging import getLogger

CACHE = Cache("RADIOCACHE")
CACHE.setup("mem://?check_interval=10&size=10000", enable=True)

LOGGER = getLogger("PyLav.extension.RadioBrowser")


class Error(PyLavException):
    """Base class for all exceptions raised by this module"""


class RDNSLookupError(Error):
    __slots__ = ("ip", "port")

    def __init__(self, ip: str) -> None:
        self.ip = ip
        self.error_msg = f"There was a problem with performing reverse dns lookup for ip: {ip}"
        super().__init__(self.error_msg)


@CACHE.cache(ttl=3600, prefix="radio_browser", key=f"{__name__}.fetch_servers")
async def fetch_servers() -> set[str]:
    """
    Get IP of all currently available `Radio Browser` servers.
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


@CACHE.cache(ttl=600, prefix="radio_browser")
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


@CACHE.cache(ttl=600, prefix="radio_browser", key=f"{__name__}.fetch_hosts")
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


@CACHE.cache(ttl=300, prefix="radio_browser", key=f"{__name__}.pick_base_url")
async def pick_base_url(session: aiohttp.ClientSession) -> str | None:
    hosts = await fetch_hosts()
    for host in hosts:
        with contextlib.suppress(Exception):
            async with session.get(f"https://{host}/json/stats") as response:
                if response.status == 200:
                    return f"https://{host}"
                LOGGER.verbose("Error interacting with %s: %s", host, response.status)
    LOGGER.error("All the following hosts for the RadioBrowser API are broken: %s", ", ".join(hosts))
