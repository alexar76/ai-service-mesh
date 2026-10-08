#!/usr/bin/env python3
"""Seed completed mesh tasks + activity from real verified agents (display traffic).

Runs against MESH_DATA_DIR (default /data in the API container). Idempotent:
skips when tasks_24h already >= min_tasks.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from ai_service_mesh.db import MeshStore  # noqa: E402
from ai_service_mesh.models import (  # noqa: E402
    ActivityKind,
    MeshHopOut,
    TaskStatus,
    utc_now_iso,
)

DATA_DIR = Path(os.environ.get("MESH_DATA_DIR", "/data"))
MIN_TASKS = int(os.environ.get("MESH_SEED_MIN_TASKS", "3"))

SCENARIOS = [
    {
        "intent": "research and summarize agent mesh discovery patterns",
        "budget": 3.5,
        "caps": ("research", "summarize"),
        "price": 0.42,
        "latencies": (38, 12, 210, 4),
    },
    {
        "intent": "verify oracle attestation for escrow settlement",
        "budget": 2.0,
        "caps": ("oracle", "verify"),
        "price": 0.31,
        "latencies": (41, 9, 186, 3),
    },
    {
        "intent": "hold escrow and settle payment for invoke result",
        "budget": 5.0,
        "caps": ("escrow", "settle"),
        "price": 0.55,
        "latencies": (29, 11, 154, 5),
    },
    {
        "intent": "cross-mesh research relay with oracle cross-check",
        "budget": 4.25,
        "caps": ("research", "oracle"),
        "price": 0.48,
        "latencies": (44, 15, 240, 6),
        "fail_invoke": False,
        "extra_peer_caps": ("oracle", "verify"),
    },
]


def _pick(agents: list, wanted: tuple[str, ...]):
    wanted_l = {w.lower() for w in wanted}
    scored = []
    for a in agents:
        caps = {c.lower() for c in a.capabilities}
        hit = len(wanted_l & caps)
        if hit:
            scored.append((hit * a.trust_score, a))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1] if scored else (agents[0] if agents else None)


def _pipeline(store: MeshStore, agent, scenario: dict) -> str:
    task = store.create_task(scenario["intent"], float(scenario["budget"]), "")
    price = float(scenario["price"])
    lv, le, li, ls = scenario["latencies"]

    store.emit(
        ActivityKind.DISCOVERY,
        f"Scanning mesh for capable agents ({', '.join(scenario['caps'])})",
        task_id=task.id,
    )
    store.emit(
        ActivityKind.VERIFICATION,
        f"Zero-trust preflight: {agent.name} (health_ok)",
        task_id=task.id,
        agent_id=agent.id,
        payload={"ok": True, "source": "local"},
    )
    hops = [
        MeshHopOut(
            agent_id=agent.id,
            agent_name=agent.name,
            phase="verify",
            price_usd=0.0,
            latency_ms=lv,
            success=True,
            detail="health_ok",
        ),
        MeshHopOut(
            agent_id=agent.id,
            agent_name=agent.name,
            phase="escrow",
            price_usd=price,
            latency_ms=le,
            success=True,
            detail=f"esc_seed_{task.id[-8:]}",
        ),
    ]
    store.emit(
        ActivityKind.ESCROW,
        f"Escrow hold {price:.4f} USD",
        task_id=task.id,
        agent_id=agent.id,
        payload={"amount_usd": price},
    )

    extra = scenario.get("extra_peer_caps")
    if extra:
        peer = _pick(store.list_agents(verified_only=True), tuple(extra))
        if peer and peer.id != agent.id:
            hops.append(
                MeshHopOut(
                    agent_id=peer.id,
                    agent_name=peer.name,
                    phase="verify",
                    price_usd=0.0,
                    latency_ms=22,
                    success=True,
                    detail="cross_check",
                )
            )
            store.emit(
                ActivityKind.VERIFICATION,
                f"Cross-mesh check via {peer.name}",
                task_id=task.id,
                agent_id=peer.id,
            )

    hops.append(
        MeshHopOut(
            agent_id=agent.id,
            agent_name=agent.name,
            phase="invoke",
            price_usd=price,
            latency_ms=li,
            success=True,
            detail="invoke_ok",
        )
    )
    store.emit(
        ActivityKind.INVOKE,
        f"Invocation succeeded: {agent.name}",
        task_id=task.id,
        agent_id=agent.id,
        payload={"latency_ms": li},
    )
    hops.append(
        MeshHopOut(
            agent_id=agent.id,
            agent_name=agent.name,
            phase="settle",
            price_usd=price,
            latency_ms=ls,
            success=True,
            detail="released",
        )
    )
    store.emit(
        ActivityKind.SETTLE,
        f"Settled {price:.4f} USD to {agent.name}",
        task_id=task.id,
        agent_id=agent.id,
    )

    task.status = TaskStatus.COMPLETED
    task.selected_agent_id = agent.id
    task.total_spent_usd = price
    task.hops = hops
    task.completed_at = utc_now_iso()
    store.update_task(task)
    return task.id


def main() -> int:
    store = MeshStore(DATA_DIR)
    agents = store.list_agents(verified_only=True)
    if len(agents) < 1:
        print("no verified agents — run seed_display_agents.py first", file=sys.stderr)
        return 1

    existing = store.list_tasks(limit=50)
    completed = [t for t in existing if t.status == TaskStatus.COMPLETED]
    if len(completed) >= MIN_TASKS:
        print(f"already have {len(completed)} completed tasks — skip")
        return 0

    created = []
    for sc in SCENARIOS:
        agent = _pick(agents, tuple(sc["caps"]))
        if not agent:
            continue
        tid = _pipeline(store, agent, sc)
        created.append(tid)
        print("seeded task", tid, "→", agent.name)

    print(f"done — {len(created)} tasks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
