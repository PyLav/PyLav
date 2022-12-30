from __future__ import annotations

import asyncio
import ssl
import urllib.request

from pylav.extension.m3u.parser import urljoin


def parsed_url(url: str) -> str | bytes:
    return urljoin(url, ".")


class DefaultHTTPClient:
    __slots__ = ("proxies",)

    def __init__(self, proxies: dict[str, list[str]] = None) -> None:
        self.proxies = proxies

    async def download(
        self, uri: str, timeout: float | None = None, headers: dict[str, str] | None = None, verify_ssl: bool = True
    ) -> tuple[str, str]:
        if headers is None:
            headers = {}
        proxy_handler = await asyncio.to_thread(urllib.request.ProxyHandler, self.proxies)
        https_handler = await asyncio.to_thread(HTTPSHandler, verify_ssl=verify_ssl)
        opener = await asyncio.to_thread(urllib.request.build_opener, proxy_handler, https_handler)
        opener.addheaders = headers.items()
        resource = await asyncio.to_thread(opener.open, uri, timeout=timeout)
        base_uri = parsed_url(await asyncio.to_thread(resource.geturl))
        content = (await asyncio.to_thread(resource.read)).decode(
            await asyncio.to_thread(resource.headers.get_content_charset, failobj="utf-8")
        )
        return content, base_uri


class HTTPSHandler:
    __slots__ = ()

    def __new__(cls, verify_ssl: bool = True) -> urllib.request.HTTPSHandler:
        context = ssl.create_default_context()
        if not verify_ssl:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        return urllib.request.HTTPSHandler(context=context)
