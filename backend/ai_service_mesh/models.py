"""Domain models and API schemas."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class AgentStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    SUSPENDED = "suspended"


class TaskStatus(str, Enum):
    QUEUED = "queued"
    DISCOVERING = "discovering"
    VERIFYING = "verifying"
    ESCROWED = "escrowed"
    INVOKING = "invoking"
    COMPLETED = "completed"
    FAILED = "failed"


class ActivityKind(str, Enum):
    AGENT_REGISTERED = "agent.registered"
    AGENT_VERIFIED = "agent.verified"
    TASK_CREATED = "task.created"
    DISCOVERY = "mesh.discovery"
    VERIFICATION = "mesh.verification"
    ESCROW = "mesh.escrow"
    INVOKE = "mesh.invoke"
    SETTLE = "mesh.settle"
    ERROR = "mesh.error"


_EVM_ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")
# base58 (Bitcoin alphabet, no 0OIl) — a Solana pubkey is 32 bytes ⇒ 32–44 chars.
_SOLANA_PUBKEY_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")


class AgentRegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    endpoint_url: str
    public_key_pem: str = Field(min_length=32, max_length=4096)
    capabilities: list[str] = Field(default_factory=list, max_length=32)
    attestation: str = ""
    product_id: str = Field(default="", max_length=80)
    capability_id: str = Field(default="", max_length=80)
    source_hub: str = Field(default="local", max_length=256)
    # Optional on-chain identities. When present (and the agent is verified), the
    # AIMarket lottery treats this agent as a self-custodial participant — tickets
    # are attributed to this wallet rather than a relayer-held demo key.
    evm_address: str = Field(default="", max_length=42)
    solana_pubkey: str = Field(default="", max_length=44)

    @field_validator("endpoint_url")
    @classmethod
    def endpoint_https(cls, v: str) -> str:
        if v.startswith("https://"):
            return v.rstrip("/")
        if v.startswith("http://127.0.0.1") or v.startswith("http://localhost"):
            return v.rstrip("/")
        raise ValueError("endpoint_url must use https:// (or http://127.0.0.1 / localhost for local agents)")

    @field_validator("evm_address")
    @classmethod
    def valid_evm(cls, v: str) -> str:
        if v and not _EVM_ADDRESS_RE.match(v):
            raise ValueError("evm_address must be a 0x-prefixed 20-byte hex address")
        return v

    @field_validator("solana_pubkey")
    @classmethod
    def valid_solana(cls, v: str) -> str:
        if v and not _SOLANA_PUBKEY_RE.match(v):
            raise ValueError("solana_pubkey must be a base58-encoded 32-byte public key")
        return v


class WalletBindRequest(BaseModel):
    """Attach on-chain identities to an existing agent (e.g. the UNI auto-bound wallet)."""
    evm_address: str = Field(default="", max_length=42)
    solana_pubkey: str = Field(default="", max_length=44)

    @field_validator("evm_address")
    @classmethod
    def valid_evm(cls, v: str) -> str:
        if v and not _EVM_ADDRESS_RE.match(v):
            raise ValueError("evm_address must be a 0x-prefixed 20-byte hex address")
        return v

    @field_validator("solana_pubkey")
    @classmethod
    def valid_solana(cls, v: str) -> str:
        if v and not _SOLANA_PUBKEY_RE.match(v):
            raise ValueError("solana_pubkey must be a base58-encoded 32-byte public key")
        return v


class AgentOut(BaseModel):
    id: str
    name: str
    endpoint_url: str
    status: AgentStatus
    trust_score: float
    capabilities: list[str]
    product_id: str = ""
    capability_id: str = ""
    source_hub: str = "local"
    evm_address: str = ""
    solana_pubkey: str = ""
    verified_at: Optional[str] = None
    created_at: str


class TaskCreateRequest(BaseModel):
    intent: str = Field(min_length=3, max_length=2000)
    budget_usd: float = Field(gt=0, le=10_000)
    consumer_agent_id: str = ""
    preferred_capabilities: list[str] = Field(default_factory=list, max_length=16)


class MeshHopOut(BaseModel):
    agent_id: str
    agent_name: str
    phase: str
    price_usd: float
    latency_ms: int
    success: bool
    detail: str = ""


class TaskOut(BaseModel):
    id: str
    intent: str
    budget_usd: float
    status: TaskStatus
    selected_agent_id: Optional[str] = None
    total_spent_usd: float = 0.0
    hops: list[MeshHopOut] = Field(default_factory=list)
    created_at: str
    completed_at: Optional[str] = None
    error: Optional[str] = None


class ActivityEventOut(BaseModel):
    id: str
    kind: ActivityKind
    message: str
    task_id: Optional[str] = None
    agent_id: Optional[str] = None
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: str


class MeshStatsOut(BaseModel):
    agents_total: int
    agents_verified: int
    tasks_24h: int
    mesh_hops_24h: int
    success_rate_24h: float
    volume_usd_24h: float


def new_id(prefix: str = "") -> str:
    uid = uuid4().hex[:16]
    return f"{prefix}{uid}" if prefix else uid
