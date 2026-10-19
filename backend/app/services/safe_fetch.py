from __future__ import annotations

import asyncio
import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import httpx


@dataclass(frozen=True)
class FetchResult:
    status: int | None
    final_url: str | None
    tls_ok: bool
    headers: dict[str, str]
    text: str
    available: bool
    error: str | None = None


def _validate_scheme(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Only absolute http/https URLs are allowed")


async def _validated_ips(hostname: str) -> list[str]:
    loop = asyncio.get_running_loop()
    infos = await loop.run_in_executor(None, socket.getaddrinfo, hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
    addresses = sorted({info[4][0] for info in infos})
    if not addresses:
        raise ValueError("Host did not resolve")
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
            raise ValueError("URL resolves to a restricted IP address")
    return addresses


async def fetch(url: str, *, max_redirects: int = 3, max_bytes: int = 500_000) -> FetchResult:
    current = url
    try:
        for _ in range(max_redirects + 1):
            _validate_scheme(current)
            parsed = urlparse(current)
            await _validated_ips(parsed.hostname or "")
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(8.0), follow_redirects=False, cookies={}, verify=True,
                headers={"User-Agent": "DhanRakshak-MerchantResearch/1.0"},
            ) as client:
                response = await client.get(current)
            if response.is_redirect:
                location = response.headers.get("location")
                if not location:
                    break
                current = urljoin(current, location)
                continue
            raw = response.content[:max_bytes]
            return FetchResult(
                status=response.status_code, final_url=str(response.url),
                tls_ok=parsed.scheme == "https", headers={
                    key: value for key, value in response.headers.items()
                    if key.lower() in {"content-type", "content-length", "server"}
                },
                text=raw.decode(response.encoding or "utf-8", errors="replace"),
                available=response.is_success,
            )
        raise ValueError("Too many redirects")
    except (ValueError, httpx.HTTPError, socket.gaierror, OSError) as exc:
        return FetchResult(None, None, False, {}, "", False, str(exc))
