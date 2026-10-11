"""Real capability invocation — AIMarket Hub protocol or direct agent endpoint."""

from __future__ import annotations

import time
from typing import Any, Optional

import httpx

from ai_service_mesh.security import UnsafeTarget, pin_target

DEFAULT_MAX_RESPONSE_BYTES = 1_048_576


class ResponseTooLarge(Exception):
    """The reply was refused before all of it was buffered."""


def _make_client(timeout: float) -> httpx.AsyncClient:
    """One place to build the outbound client (tests swap in a MockTransport here)."""
    return httpx.AsyncClient(timeout=timeout, follow_redirects=False)


async def _send_capped(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    max_bytes: int,
    json: Optional[dict] = None,
    headers: Optional[dict[str, str]] = None,
    extensions: Optional[dict[str, Any]] = None,
) -> tuple[int, bytes]:
    """Send and read at most ``max_bytes`` of the body.

    ``resp.json()`` buffers the whole reply first, so a cap applied after it is a cap on
    nothing. Declared Content-Length is refused up front (an honest header costs one
    round-trip), and a stream that overruns is cut mid-body (a dishonest one costs
    ``max_bytes`` and no more).
    """
    request = client.build_request(method, url, json=json, headers=headers, extensions=extensions or None)
    resp = await client.send(request, stream=True, follow_redirects=False)
    try:
        declared = resp.headers.get("content-length")
        if declared:
            try:
                declared_len = int(declared)
            except ValueError as exc:
                raise ResponseTooLarge("invalid Content-Length") from exc
            if declared_len < 0 or declared_len > max_bytes:
                raise ResponseTooLarge(f"declared {declared_len} > {max_bytes}")
        body = bytearray()
        async for chunk in resp.aiter_bytes(chunk_size=16384):
            body.extend(chunk)
            if len(body) > max_bytes:
                raise ResponseTooLarge(f"body exceeds {max_bytes} bytes")
        return resp.status_code, bytes(body)
    finally:
        await resp.aclose()


def _decode(body: bytes) -> dict[str, Any]:
    import json as _json
    try:
        data = _json.loads(body.decode("utf-8", errors="replace") or "null")
    except ValueError:
        data = None
    if isinstance(data, dict):
        return data
    return {"raw": body[:500].decode("utf-8", errors="replace")}


def response_is_demo_marked(data: dict, detail: str) -> bool:
    """Detect hub/factory demo execution — mesh treats this as failed invoke in production."""
    blob = detail or ""
    result = data.get("result")
    if isinstance(result, dict):
        out = result.get("output")
        if isinstance(out, str):
            blob += " " + out
    raw = data.get("raw")
    if isinstance(raw, str):
        blob += " " + raw
    return "[DEMO]" in blob.upper() or "demo execution" in blob.lower()


async def preflight_hub(hub_url: str) -> tuple[bool, int, str]:
    """Lightweight hub health check before routing paid hub invocations."""
    t0 = time.perf_counter()
    url = f"{hub_url.rstrip('/')}/ai-market/v2/manifest"
    try:
        async with _make_client(8.0) as client:
            status, _ = await _send_capped(client, "GET", url, max_bytes=DEFAULT_MAX_RESPONSE_BYTES)
        latency = int((time.perf_counter() - t0) * 1000)
        if status == 200:
            return True, latency, "hub_manifest_ok"
        return False, latency, f"hub_status_{status}"
    except ResponseTooLarge:
        return False, int((time.perf_counter() - t0) * 1000), "response_too_large"
    except httpx.HTTPError as exc:
        latency = int((time.perf_counter() - t0) * 1000)
        return False, latency, str(exc)[:160]


async def preflight_agent(
    endpoint_url: str, *, allow_localhost: bool = False
) -> tuple[bool, int, str]:
    """Verify agent endpoint responds before routing a paid task."""
    t0 = time.perf_counter()
    url = f"{endpoint_url.rstrip('/')}/health"
    try:
        target, headers, ext = pin_target(url, allow_localhost=allow_localhost)
        async with _make_client(8.0) as client:
            status, _ = await _send_capped(
                client, "GET", target, headers=headers, extensions=ext,
                max_bytes=DEFAULT_MAX_RESPONSE_BYTES,
            )
        latency = int((time.perf_counter() - t0) * 1000)
        if status == 200:
            return True, latency, "health_ok"
        return False, latency, f"health_status_{status}"
    except UnsafeTarget as exc:
        return False, int((time.perf_counter() - t0) * 1000), f"endpoint_unsafe: {exc}"[:160]
    except ResponseTooLarge:
        return False, int((time.perf_counter() - t0) * 1000), "response_too_large"
    except httpx.HTTPError as exc:
        latency = int((time.perf_counter() - t0) * 1000)
        return False, latency, str(exc)[:160]


async def invoke_via_hub(
    hub_url: str,
    product_id: str,
    capability_id: str,
    intent: str,
    source_hub: str = "local",
    *,
    reject_demo_output: bool = True,
    max_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
) -> tuple[bool, int, str, dict[str, Any]]:
    t0 = time.perf_counter()
    url = f"{hub_url.rstrip('/')}/ai-market/v2/invoke"
    body = {
        "product_id": product_id,
        "capability_id": capability_id,
        "source_hub": source_hub,
        "input": {"intent": intent, "query": intent},
    }
    try:
        # The hub is the OPERATOR's configured destination (loopback in prod), so it is
        # not SSRF-checked or pinned — only its reply is bounded.
        async with _make_client(45.0) as client:
            status, raw = await _send_capped(client, "POST", url, json=body, max_bytes=max_bytes)
        latency = int((time.perf_counter() - t0) * 1000)
        data = _decode(raw)
        if status == 200 and data.get("success") is not False:
            detail = "invoke_ok"
            if isinstance(data.get("result"), dict) and data["result"].get("output"):
                detail = str(data["result"]["output"])[:160]
            if reject_demo_output and response_is_demo_marked(data, detail):
                return False, latency, "demo_output_rejected", data
            return True, latency, detail, data
        err = data.get("error") or data.get("reason") or data.get("raw", "")[:120]
        return False, latency, str(err), data
    except ResponseTooLarge:
        return False, int((time.perf_counter() - t0) * 1000), "response_too_large", {}
    except httpx.HTTPError as exc:
        latency = int((time.perf_counter() - t0) * 1000)
        return False, latency, str(exc)[:160], {}


async def invoke_direct(
    endpoint_url: str,
    intent: str,
    *,
    reject_demo_output: bool = True,
    allow_localhost: bool = False,
    max_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
) -> tuple[bool, int, str, dict[str, Any]]:
    """POST /invoke on a registered agent endpoint (factory-style).

    The endpoint was SSRF-checked when the operator registered it; that check is run
    AGAIN here and the connection is pinned to the address it validates, so a DNS record
    flipped to a private range since registration cannot reach internal services. The
    reply is read up to ``max_bytes`` and refused beyond that.
    """
    t0 = time.perf_counter()
    url = f"{endpoint_url.rstrip('/')}/invoke"
    try:
        target, headers, ext = pin_target(url, allow_localhost=allow_localhost)
        async with _make_client(45.0) as client:
            status, raw = await _send_capped(
                client, "POST", target,
                json={"input": {"intent": intent, "query": intent}},
                headers=headers, extensions=ext, max_bytes=max_bytes,
            )
        latency = int((time.perf_counter() - t0) * 1000)
        data = _decode(raw)
        if status == 200:
            detail = "invoke_ok"
            if isinstance(data.get("result"), dict) and data["result"].get("output"):
                detail = str(data["result"]["output"])[:160]
            # SEC-11: a direct agent must not return demo/stub output in production.
            if reject_demo_output and response_is_demo_marked(data, detail):
                return False, latency, "demo_output_rejected", data
            return True, latency, detail, data
        return False, latency, f"status_{status}", data
    except UnsafeTarget as exc:
        return False, int((time.perf_counter() - t0) * 1000), f"endpoint_unsafe: {exc}"[:160], {}
    except ResponseTooLarge:
        return False, int((time.perf_counter() - t0) * 1000), "response_too_large", {}
    except httpx.HTTPError as exc:
        latency = int((time.perf_counter() - t0) * 1000)
        return False, latency, str(exc)[:160], {}
