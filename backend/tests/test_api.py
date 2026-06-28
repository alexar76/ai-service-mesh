"""API integration tests."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.usefixtures("resolve_example_agent_hosts")

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from ai_service_mesh.verification import build_attestation


def _agent_payload(
    name: str,
    endpoint: str,
    caps: list[str],
    *,
    product_id: str = "prod_test",
    capability_id: str = "cap_test",
) -> dict:
    key = ed25519.Ed25519PrivateKey.generate()
    pub = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    att = build_attestation(key, name, endpoint, caps)
    return {
        "name": name,
        "endpoint_url": endpoint,
        "public_key_pem": pub,
        "capabilities": caps,
        "attestation": att,
        "product_id": product_id,
        "capability_id": capability_id,
        "source_hub": "local",
    }


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_register_and_list_agents(client):
    body = _agent_payload("Test Agent", "https://agent.example.com", ["search", "nlp"])
    r = client.post(
        "/v1/agents",
        json=body,
        headers={"Authorization": "Bearer test-admin"},
    )
    assert r.status_code == 201
    agent = r.json()
    assert agent["status"] == "verified"

    listed = client.get("/v1/agents", params={"verified_only": True})
    assert listed.status_code == 200
    assert any(a["id"] == agent["id"] for a in listed.json())


def test_register_with_wallets_round_trips(client):
    body = _agent_payload("Wallet Bot", "https://wallet.example.com", ["search"])
    body["evm_address"] = "0x" + "A1" * 20
    body["solana_pubkey"] = "11111111111111111111111111111111"
    r = client.post("/v1/agents", json=body, headers={"Authorization": "Bearer test-admin"})
    assert r.status_code == 201, r.text
    agent = r.json()
    assert agent["evm_address"] == "0x" + "A1" * 20
    assert agent["solana_pubkey"] == "11111111111111111111111111111111"

    listed = client.get("/v1/agents", params={"verified_only": True}).json()
    me = next(a for a in listed if a["id"] == agent["id"])
    assert me["evm_address"] and me["solana_pubkey"]  # persisted + served


def test_register_rejects_malformed_wallet(client):
    body = _agent_payload("Bad Wallet", "https://badwallet.example.com", ["search"])
    body["evm_address"] = "0xnothex"
    r = client.post("/v1/agents", json=body, headers={"Authorization": "Bearer test-admin"})
    assert r.status_code == 422  # pydantic validation rejects before persistence


def test_bind_wallet_patch_round_trips(client):
    body = _agent_payload("Bindable", "https://bind.example.com", ["search"])
    agent = client.post("/v1/agents", json=body, headers={"Authorization": "Bearer test-admin"}).json()
    r = client.patch(
        f"/v1/agents/{agent['id']}/wallet",
        json={"evm_address": "0x" + "b" * 40},
        headers={"Authorization": "Bearer test-admin"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["evm_address"] == "0x" + "b" * 40
    assert client.get(f"/v1/agents/{agent['id']}").json()["evm_address"] == "0x" + "b" * 40  # persisted


def test_bind_wallet_requires_admin(client):
    body = _agent_payload("NoAuthBind", "https://noauthbind.example.com", ["search"])
    agent = client.post("/v1/agents", json=body, headers={"Authorization": "Bearer test-admin"}).json()
    r = client.patch(f"/v1/agents/{agent['id']}/wallet", json={"evm_address": "0x" + "c" * 40})
    assert r.status_code in (401, 403)  # admin-gated


def test_mesh_task_pipeline(client):
    body = _agent_payload("Pipeline Bot", "https://pipeline.example.com", ["research", "summarize"])
    client.post("/v1/agents", json=body, headers={"Authorization": "Bearer test-admin"})

    task = client.post(
        "/v1/tasks",
        json={
            "intent": "research latest AI agent mesh patterns",
            "budget_usd": 5.0,
            "preferred_capabilities": ["research"],
        },
        headers={"Authorization": "Bearer test-api"},
    )
    assert task.status_code == 201
    data = task.json()
    assert data["status"] in ("completed", "failed")
    assert len(data["hops"]) >= 1

    activity = client.get("/v1/activity", params={"limit": 20})
    assert activity.status_code == 200
    kinds = {e["kind"] for e in activity.json()}
    assert "task.created" in kinds


def test_stats(client):
    r = client.get("/v1/stats")
    assert r.status_code == 200
    assert "agents_total" in r.json()


def test_admin_required_for_register(client):
    r = client.post(
        "/v1/agents",
        json=_agent_payload("No Auth Agent", "https://noauth.example.com", ["a"]),
    )
    assert r.status_code in (401, 403, 503)


def test_register_rejects_forged_attestation(client):
    # SEC-03: attestation signed with the wrong key must not verify.
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519

    from ai_service_mesh.verification import build_attestation

    name, endpoint, caps = "Forger", "https://forger.example.com", ["search"]
    real_key = ed25519.Ed25519PrivateKey.generate()
    pub = real_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    attacker_key = ed25519.Ed25519PrivateKey.generate()  # not matching pub
    body = {
        "name": name,
        "endpoint_url": endpoint,
        "public_key_pem": pub,
        "capabilities": caps,
        "attestation": build_attestation(attacker_key, name, endpoint, caps),
        "product_id": "p",
        "capability_id": "c",
        "source_hub": "local",
    }
    r = client.post("/v1/agents", json=body, headers={"Authorization": "Bearer test-admin"})
    # Registration is accepted but the agent must NOT be verified.
    if r.status_code == 201:
        assert r.json()["status"] != "verified"
    else:
        assert r.status_code in (400, 422)


def test_ui_writes_fail_closed(monkeypatch):
    # SEC-01: /v1/ui/tasks disabled unless explicitly enabled.
    from fastapi.testclient import TestClient

    from ai_service_mesh.api import create_app
    from ai_service_mesh.config import Settings

    settings = Settings(
        env="test",
        cors_origins="http://test",
        api_token="test-api",
        admin_token="test-admin",
        hub_url="",
        allow_localhost_agents=True,
        allow_ui_writes=False,
    )
    with TestClient(create_app(settings)) as c:
        r = c.post("/v1/ui/tasks", json={"intent": "test intent", "budget_usd": 1.0})
        assert r.status_code == 403


def test_ui_writes_require_allowed_origin(client):
    # allow_ui_writes=True in fixture; origin must be in the CORS allowlist.
    bad = client.post(
        "/v1/ui/tasks",
        json={"intent": "test intent", "budget_usd": 1.0},
        headers={"Origin": "http://evil.example"},
    )
    assert bad.status_code == 403
    ok = client.post(
        "/v1/ui/tasks",
        json={"intent": "test intent", "budget_usd": 1.0},
        headers={"Origin": "http://test"},
    )
    assert ok.status_code == 201


def test_read_auth_can_be_locked_down():
    # SEC-08b: with public_read=False, reads require the API token.
    from fastapi.testclient import TestClient

    from ai_service_mesh.api import create_app
    from ai_service_mesh.config import Settings

    settings = Settings(
        env="test",
        cors_origins="http://test",
        api_token="test-api",
        admin_token="test-admin",
        hub_url="",
        allow_localhost_agents=True,
        public_read=False,
    )
    with TestClient(create_app(settings)) as c:
        assert c.get("/v1/agents").status_code in (401, 403)
        ok = c.get("/v1/agents", headers={"Authorization": "Bearer test-api"})
        assert ok.status_code == 200
