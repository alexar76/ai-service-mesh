"""Runtime configuration from environment."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _resolve_env_file() -> str | None:
    """Locate .env without assuming a fixed package depth."""
    explicit = os.environ.get("MESH_ENV_FILE", "").strip()
    if explicit:
        p = Path(explicit)
        if p.is_file():
            return str(p)
    here = Path(__file__).resolve()
    candidates = (
        here.parents[2] / ".env",
        here.parents[1] / ".env",
        Path.cwd() / ".env",
    )
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None


_ENV_FILE = _resolve_env_file()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MESH_",
        env_file=_ENV_FILE,
        extra="ignore",
    )

    host: str = "0.0.0.0"
    port: int = 8090
    env: str = "production"
    cors_origins: str = "http://localhost:5173"
    api_token: str = ""
    admin_token: str = ""
    hub_url: str = "http://127.0.0.1:9080"
    skip_demo_capabilities: bool = True
    reject_demo_invoke_output: bool = True
    allow_localhost_agents: bool = False
    allow_insecure_tokens: bool = False
    data_dir: Path = Path(".mesh_data")
    database_url: str = ""
    rate_limit: int = 120
    max_agent_attempts: int = 12
    task_stale_seconds: int = 600
    # Security hardening knobs
    allow_ui_writes: bool = False  # SEC-01: browser BFF /v1/ui/tasks fail-closed by default
    trust_forwarded_for: bool = False  # SEC-08: only honor X-Forwarded-For behind a trusted proxy
    public_read: bool = True  # SEC-08b: when False, read endpoints require MESH_API_TOKEN
    health_verbose: bool = False  # SEC-10: expose backend/internal details on /health
    # Ecosystem master crypto switch — OFF by default. Reads the shared
    # AIFACTORY_CRYPTO_ENABLED (not MESH_*) so one var governs every component.
    # When off, agent wallet binding is refused and wallet fields are blanked;
    # agents still register and run tasks. Internal USD escrow is NOT a crypto
    # surface and keeps working regardless.
    enable_crypto: bool = Field(default=False, validation_alias="AIFACTORY_CRYPTO_ENABLED")


@lru_cache
def get_settings() -> Settings:
    return Settings()
