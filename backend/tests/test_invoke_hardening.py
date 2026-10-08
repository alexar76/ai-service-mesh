"""Outbound invoke: bounded replies and a connection pinned to the address we validated.

Two gaps closed 2026-09-11. `resp.json()` buffered an agent's whole reply before any cap
could apply, so a registered endpoint could answer a task with a gigabyte. And the SSRF
check ran only at registration while the invoke connected by hostname later, so a DNS
record flipped to 127.0.0.1 in between reached internal services with a registered
agent's blessing. The hub already had both guards (outbound_http); this is the mesh's.
"""
from __future__ import annotations

import socket

import httpx
import pytest

from ai_service_mesh import invoke
from ai_service_mesh.security import UnsafeTarget, pin_target

PUBLIC_IP = "93.184.216.34"


def _fake_dns(mapping: dict[str, str]):
    real = socket.getaddrinfo

    def patched(host, port, *a, **k):
        if host in mapping:
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (mapping[host], port or 443))]
        return real(host, port, *a, **k)

    return patched


def _mock_client(handler):
    """Route every outbound request through `handler(request) -> httpx.Response`."""
    def factory(timeout):
        return httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=timeout)
    return factory


# ── pin_target ─────────────────────────────────────────────────────────────────────

def test_pin_rewrites_host_to_validated_ip_and_keeps_sni(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _fake_dns({"agent.example.com": PUBLIC_IP}))
    target, headers, ext = pin_target("https://agent.example.com:8443/invoke")
    assert target == f"https://{PUBLIC_IP}:8443/invoke"
    assert headers == {"Host": "agent.example.com:8443"}
    assert ext == {"sni_hostname": "agent.example.com"}


def test_pin_refuses_a_host_that_now_resolves_privately(monkeypatch):
    """The rebinding case: public at registration, loopback at invoke."""
    monkeypatch.setattr(socket, "getaddrinfo", _fake_dns({"agent.example.com": "127.0.0.1"}))
    with pytest.raises(UnsafeTarget):
        pin_target("https://agent.example.com/invoke")


def test_pin_refuses_when_dns_fails(monkeypatch):
    def boom(*_a, **_k):
        raise socket.gaierror("nope")
    monkeypatch.setattr(socket, "getaddrinfo", boom)
    with pytest.raises(UnsafeTarget):
        pin_target("https://agent.example.com/invoke")


def test_pin_passes_literal_public_ip_and_allowed_localhost_through():
    assert pin_target(f"https://{PUBLIC_IP}/x") == (f"https://{PUBLIC_IP}/x", {}, {})
    assert pin_target("http://127.0.0.1:9000/x", allow_localhost=True) == ("http://127.0.0.1:9000/x", {}, {})
    with pytest.raises(UnsafeTarget):
        pin_target("http://127.0.0.1:9000/x", allow_localhost=False)


# ── invoke_direct ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_invoke_direct_connects_to_the_pinned_ip(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _fake_dns({"agent.example.com": PUBLIC_IP}))
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["host"] = request.url.host
        seen["host_header"] = request.headers.get("host")
        seen["sni"] = request.extensions.get("sni_hostname")
        return httpx.Response(200, json={"result": {"output": "real answer"}})

    monkeypatch.setattr(invoke, "_make_client", _mock_client(handler))
    ok, _lat, detail, data = await invoke.invoke_direct("https://agent.example.com", "do it")
    assert ok and detail == "real answer"
    assert seen == {"host": PUBLIC_IP, "host_header": "agent.example.com", "sni": "agent.example.com"}


@pytest.mark.asyncio
async def test_invoke_direct_never_connects_when_dns_rebound_to_private(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _fake_dns({"agent.example.com": "169.254.169.254"}))
    calls = []

    def handler(request):
        calls.append(request.url)
        return httpx.Response(200, json={})

    monkeypatch.setattr(invoke, "_make_client", _mock_client(handler))
    ok, _lat, detail, data = await invoke.invoke_direct("https://agent.example.com", "do it")
    assert ok is False and detail.startswith("endpoint_unsafe")
    assert calls == [], "the request must not leave the process"
    assert data == {}


@pytest.mark.asyncio
async def test_invoke_direct_refuses_a_declared_oversize_reply_without_reading_it(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _fake_dns({"agent.example.com": PUBLIC_IP}))
    streamed = {"chunks": 0}

    def handler(request):
        def gen():
            for _ in range(1000):
                streamed["chunks"] += 1
                yield b"x" * 65536
        return httpx.Response(200, headers={"content-length": str(1000 * 65536)}, stream=httpx.ByteStream(b""))

    monkeypatch.setattr(invoke, "_make_client", _mock_client(handler))
    ok, _lat, detail, data = await invoke.invoke_direct(
        "https://agent.example.com", "x", max_bytes=1024 * 1024
    )
    assert ok is False and detail == "response_too_large" and data == {}


@pytest.mark.asyncio
async def test_invoke_direct_cuts_an_undeclared_oversize_stream(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _fake_dns({"agent.example.com": PUBLIC_IP}))
    served = {"bytes": 0}

    class Big(httpx.AsyncByteStream):
        async def __aiter__(self):
            for _ in range(200):          # 200 × 64 KiB = 12.8 MiB on offer
                served["bytes"] += 65536
                yield b"y" * 65536

    def handler(request):
        return httpx.Response(200, stream=Big())   # no Content-Length

    monkeypatch.setattr(invoke, "_make_client", _mock_client(handler))
    ok, _lat, detail, _ = await invoke.invoke_direct(
        "https://agent.example.com", "x", max_bytes=256 * 1024
    )
    assert ok is False and detail == "response_too_large"
    assert served["bytes"] < 12 * 1024 * 1024, "the whole stream was consumed before refusing"


@pytest.mark.asyncio
async def test_invoke_direct_still_returns_a_normal_reply_under_the_cap(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _fake_dns({"agent.example.com": PUBLIC_IP}))
    monkeypatch.setattr(
        invoke, "_make_client",
        _mock_client(lambda r: httpx.Response(200, json={"result": {"output": "ok " * 100}})),
    )
    ok, _lat, detail, data = await invoke.invoke_direct("https://agent.example.com", "x")
    assert ok and data["result"]["output"].startswith("ok")


# ── invoke_via_hub: the operator's own hub is capped but NOT pinned ────────────────

@pytest.mark.asyncio
async def test_hub_path_allows_loopback_and_caps_the_reply(monkeypatch):
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"success": True, "result": {"output": "via hub"}})

    monkeypatch.setattr(invoke, "_make_client", _mock_client(handler))
    ok, _lat, detail, _ = await invoke.invoke_via_hub("http://127.0.0.1:9083", "p", "c", "intent")
    assert ok and detail == "via hub"
    assert seen["url"] == "http://127.0.0.1:9083/ai-market/v2/invoke"

    monkeypatch.setattr(
        invoke, "_make_client",
        _mock_client(lambda r: httpx.Response(200, headers={"content-length": "99999999"}, content=b"")),
    )
    ok, _lat, detail, _ = await invoke.invoke_via_hub("http://127.0.0.1:9083", "p", "c", "intent")
    assert ok is False and detail == "response_too_large"
