"""Security helpers: SSRF, auth, rate limiting."""

from __future__ import annotations

import asyncio
import hmac
import ipaddress
import re
import socket
import time
from collections import defaultdict
from urllib.parse import urlparse, urlunparse

from fastapi import HTTPException, Request

_PRIVATE_NETS = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
)

INSECURE_DEFAULT_TOKENS = frozenset(
    {
        "",
        "mesh-local-api",
        "mesh-local-admin",
        "change-me-in-production",
        "change-me-admin",
    }
)


def _ip_blocked(addr: str) -> bool:
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError:
        return True
    if ip.is_loopback or ip.is_link_local or ip.is_private or ip.is_reserved:
        return True
    for net in _PRIVATE_NETS:
        if ip in net:
            return True
    return False


def _url_is_safe_sync(url: str, *, allow_localhost: bool = False) -> bool:
    """DNS-resolving SSRF guard for agent endpoints (blocking — use url_is_safe_async in handlers)."""
    if any(c in url for c in "\r\n\t\x00"):
        return False
    parsed = urlparse(url)
    if parsed.scheme not in ("https", "http"):
        return False
    host = (parsed.hostname or "").lower()
    if not host or host == "metadata.google.internal":
        return False
    if allow_localhost and host in ("localhost", "127.0.0.1") and parsed.scheme == "http":
        return True
    if parsed.scheme != "https":
        return False
    if host in ("localhost", "127.0.0.1"):
        return False
    if re.match(r"^\d+\.\d+\.\d+\.\d+$", host):
        return not _ip_blocked(host)
    try:
        for family, _, _, _, sockaddr in socket.getaddrinfo(host, parsed.port or 443):
            if family in (socket.AF_INET, socket.AF_INET6):
                if _ip_blocked(sockaddr[0]):
                    return False
    except socket.gaierror:
        return False
    return True


class UnsafeTarget(ValueError):
    """The endpoint no longer passes the SSRF check, or cannot be pinned safely."""


def pin_target(url: str, *, allow_localhost: bool = False) -> tuple[str, dict[str, str], dict[str, str]]:
    """Resolve the endpoint host ONCE, validate every address, and return a request
    target that connects to that validated IP.

    Registration ran the SSRF check at registration time and the invoke connected by
    hostname later — so a DNS record that flipped to 127.0.0.1 or the metadata range
    between the two reached internal services with a registered agent's blessing.
    Returns ``(target_url, extra_headers, extensions)``: the netloc is rewritten to the
    pinned IP, ``Host`` carries the original authority, and for https ``sni_hostname``
    keeps TLS SNI and certificate validation on the real hostname. Literal IPs and the
    operator's allowed localhost pass through unchanged (already judged). DNS failure and
    any blocked address raise UnsafeTarget — falling back to a plain hostname request
    would reopen exactly the window this closes.
    """
    if not _url_is_safe_sync(url, allow_localhost=allow_localhost):
        raise UnsafeTarget("endpoint failed the SSRF check at invoke time")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if allow_localhost and host in ("localhost", "127.0.0.1"):
        return url, {}, {}
    try:
        ipaddress.ip_address(host)
        return url, {}, {}                     # literal IP: validated by the check above
    except ValueError:
        pass
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except (socket.gaierror, UnicodeError) as exc:
        raise UnsafeTarget(f"cannot resolve {host}") from exc
    safe_ip = None
    for family, _, _, _, sockaddr in infos:
        if family not in (socket.AF_INET, socket.AF_INET6):
            continue
        if _ip_blocked(sockaddr[0]):
            raise UnsafeTarget(f"{host} resolves to a blocked network")
        if safe_ip is None:
            safe_ip = sockaddr[0]
    if safe_ip is None:
        raise UnsafeTarget(f"{host} resolved to no usable address")
    netloc = f"[{safe_ip}]" if ":" in safe_ip else safe_ip
    if parsed.port:
        netloc += f":{parsed.port}"
    headers = {"Host": parsed.netloc}
    extensions = {"sni_hostname": host} if parsed.scheme == "https" else {}
    return urlunparse(parsed._replace(netloc=netloc)), headers, extensions


def url_is_safe(url: str, *, allow_localhost: bool = False) -> bool:
    """Synchronous SSRF check (unit tests and verification helpers)."""
    return _url_is_safe_sync(url, allow_localhost=allow_localhost)


async def url_is_safe_async(url: str, *, allow_localhost: bool = False) -> bool:
    """Non-blocking SSRF check for async request handlers."""
    return await asyncio.to_thread(_url_is_safe_sync, url, allow_localhost=allow_localhost)


def require_bearer(authorization: str, expected: str, *, disabled_detail: str) -> None:
    if not expected:
        raise HTTPException(status_code=503, detail=disabled_detail)
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization[7:]
    if not hmac.compare_digest(token, expected):
        raise HTTPException(status_code=403, detail="Invalid token")


def assert_production_tokens(
    env: str,
    api_token: str,
    admin_token: str,
    *,
    allow_insecure_tokens: bool = False,
) -> None:
    if env != "production" or allow_insecure_tokens:
        return
    if api_token in INSECURE_DEFAULT_TOKENS or admin_token in INSECURE_DEFAULT_TOKENS:
        raise RuntimeError(
            "MESH_API_TOKEN / MESH_ADMIN_TOKEN must be set to strong unique values in production "
            "(or set MESH_ALLOW_INSECURE_TOKENS=1 only for local dev)"
        )


class RateLimiter:
    """Sliding-window rate limiter per client IP with stale-key pruning."""

    def __init__(self, limit_per_minute: int) -> None:
        self._limit = max(1, limit_per_minute)
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._checks = 0

    def _prune_stale_keys(self, now: float) -> None:
        stale = [
            key
            for key, window in self._hits.items()
            if not window or now - window[-1] >= 60.0
        ]
        for key in stale:
            del self._hits[key]

    def check(self, key: str) -> None:
        now = time.time()
        window = [t for t in self._hits.get(key, []) if now - t < 60.0]
        if len(window) >= self._limit:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        window.append(now)
        if window:
            self._hits[key] = window
        else:
            self._hits.pop(key, None)

        self._checks += 1
        if self._checks % 64 == 0 or len(self._hits) > 4096:
            self._prune_stale_keys(now)


def client_ip(request: Request, *, trust_forwarded: bool = False) -> str:
    """Resolve the address the rate limiter buckets on.

    X-Forwarded-For is attacker-controlled unless the app sits behind a reverse proxy,
    so it is honoured only when MESH_TRUST_FORWARDED_FOR is set (SEC-08). Two things
    about the trusted case that the first version got wrong:

    * Read the chain from the RIGHT. nginx sets the header with
      ``$proxy_add_x_forwarded_for``, which APPENDS the peer it saw to whatever the
      client sent — so a client sending ``X-Forwarded-For: 1.2.3.4`` arrives as
      ``1.2.3.4, <real address>``. Taking ``split(",")[0]`` handed the limiter the forged
      value and let one caller present a fresh address per request; the rightmost entry
      is the one nginx itself observed and cannot be forged from outside.
    * Behind nginx with the flag OFF every request has ``request.client.host`` equal to
      the proxy, so the whole internet shared ONE 120/min bucket: anyone could 429 the
      public API for everyone. The production overlay now sets the flag; this function
      is what makes setting it safe.
    """
    if trust_forwarded:
        forwarded = request.headers.get("x-forwarded-for", "")
        hops = [h.strip() for h in forwarded.split(",") if h.strip()]
        if hops:
            return hops[-1][:64]
    if request.client:
        return request.client.host
    return "unknown"
