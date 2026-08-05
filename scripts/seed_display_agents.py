#!/usr/bin/env python3
"""Seed a few verified display agents into a running mesh (admin token).

Uses public HTTPS endpoints so SSRF checks pass in production.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from ai_service_mesh.verification import build_attestation  # noqa: E402

MESH_API = os.environ.get("MESH_API_URL", "http://127.0.0.1:8090").rstrip("/")
MESH_ADMIN = os.environ["MESH_ADMIN_TOKEN"]

SEEDS = [
    ("Research Scout", "https://httpbin.org/post", ["research", "summarize"]),
    ("Oracle Relay", "https://httpbin.org/post", ["oracle", "verify"]),
    ("Escrow Notary", "https://httpbin.org/post", ["escrow", "settle"]),
]


def register(name: str, endpoint: str, caps: list[str]) -> dict:
    key = ed25519.Ed25519PrivateKey.generate()
    pub = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    att = build_attestation(key, name, endpoint, caps)
    body = {
        "name": name,
        "endpoint_url": endpoint,
        "public_key_pem": pub,
        "capabilities": caps,
        "attestation": att,
        "product_id": "",
        "capability_id": "",
        "source_hub": "seed",
    }
    req = urllib.request.Request(
        f"{MESH_API}/v1/agents",
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {MESH_ADMIN}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    # Skip if already populated
    try:
        req = urllib.request.Request(f"{MESH_API}/v1/agents?verified_only=true")
        with urllib.request.urlopen(req, timeout=15) as resp:
            existing = json.loads(resp.read().decode())
        if isinstance(existing, list) and len(existing) >= 2:
            print(f"already have {len(existing)} verified agents — skip seed")
            return 0
    except Exception as exc:  # noqa: BLE001
        print("list agents:", exc, file=sys.stderr)

    for name, endpoint, caps in SEEDS:
        try:
            agent = register(name, endpoint, caps)
            print("seeded", agent.get("id"), agent.get("name"), agent.get("status"))
        except urllib.error.HTTPError as e:
            print(name, e.read().decode(), file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
