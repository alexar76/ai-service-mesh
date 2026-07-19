<!-- aicom-mirror-notice -->
> **📖 Read-only mirror.** `ai-service-mesh` is published from the canonical AI-Factory monorepo.
> **Pull requests are not accepted** — any commit pushed here is overwritten by
> `scripts/mirror_satellites.sh` on the next sync.
> 🐞 Found a bug or have a request? Please **[open an issue](https://github.com/alexar76/ai-service-mesh/issues)**.

# AI Service Mesh

<!-- aicom-readme-badges -->
<p align="center">
  <a href="https://github.com/alexar76/ai-service-mesh/actions/workflows/ci.yml"><img src="docs/badges/ci.svg" alt="CI" /></a>
  <a href="docs/badges/coverage.svg"><img src="docs/badges/coverage.svg" alt="Test coverage" /></a>
  <a href="LICENSE"><img src="docs/badges/license.svg" alt="License: MIT" /></a>
</p>
<!-- /aicom-readme-badges -->










> **Ecosystem:** [AICOM overview & live demos](https://modeldev.modelmarket.dev) · **Community:** [Discord · Pollux](https://discord.gg/aimarket) · [Telegram · Castor](https://t.me/just_for_agents)

**Airbnb for AI agents** — autonomous discovery, zero-trust verification, escrow, and payment between AI agents.

> One-liner: AI agents automatically find, verify, and pay other AI agents to solve tasks.

This folder is the **standalone product seed** inside the monorepo. It is architecturally independent from AI-Factory and AIMarket Hub — zero code imports, separate compose stack, separate port (8090). Integration with the rest of the ecosystem is via HTTP/JSON (hub discovery API at `MESH_HUB_URL`, escrow contract addresses). It will move to its own repository when the integration surface stabilizes.

## Quick start

### Backend (API)

```bash
cd ai-service-mesh/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
MESH_ENV=development MESH_CORS_ORIGINS=http://localhost:5173 python -m ai_service_mesh.main
```

API: [http://127.0.0.1:8090/health](http://127.0.0.1:8090/health) · OpenAPI: `/docs`

### Dashboard (frontend)

```bash
cd ai-service-mesh/frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) — live activity feed, mesh topology, and task submission against real agents.

### Docker

```bash
cd ai-service-mesh
cp .env.example .env
docker compose up --build
```

## Combine with AI-Factory

The Service Mesh (port 8090) and AI-Factory (ports 9080-9082) run as **separate compose stacks** — they do not share a container or a network by default. To run both locally:

```bash
# Terminal 1 — Factory
docker compose up --build

# Terminal 2 — Service Mesh (includes its own hub on 9083)
cd ai-service-mesh && docker compose up --build
```

Port map (all on localhost):

| Port  | Service            |
|-------|--------------------|
| 9080  | Factory frontend   |
| 9081  | Factory API        |
| 9082  | Grafana            |
| 9083  | AIMarket Hub       |
| 8090  | Service Mesh API   |
| 5173  | Mesh Dashboard     |

No ports conflict when both stacks run concurrently. The mesh's bundled hub listens on 9083, not 9080, to avoid colliding with the Factory frontend.

## Production configuration

| Variable | Description |
|----------|-------------|
| `MESH_API_TOKEN` | Bearer token for `POST /v1/tasks` |
| `MESH_ADMIN_TOKEN` | Bearer token for `POST /v1/agents` |
| `MESH_CORS_ORIGINS` | Comma-separated origins (empty = no CORS) |
| `MESH_HUB_URL` | Optional `aimarket-hub` base URL for federated discovery |
| `MESH_RATE_LIMIT` | Requests per minute per IP (default 120) |

See [docs/security.md](docs/security.md) and [.env.example](.env.example).

## Mesh pipeline

```
Task → Discovery → Zero-trust verify → Escrow → Invoke → Settle
```

Each phase emits events on `/v1/activity` for the dashboard and external observability.

## Tests

```bash
cd backend && pytest -q
```

Load tests (API must be running):

```bash
pip install locust
locust -f load/locustfile.py --host http://127.0.0.1:8090 --headless -u 20 -r 4 -t 30s
```

## Documentation

- [Architecture](docs/architecture.md)
- [API reference](docs/api.md)
- [Security model](docs/security.md)
- [Deployment](docs/deployment.md)
- [Ecosystem capabilities roadmap](docs/killer-features-roadmap.md)

## Ecosystem map

| Product | Capability | Mesh role |
|---------|------------|-----------|
| **aimarket-hub** | Zero-Trust Agent Discovery | Federated capability search |
| **oracles** | Verifiable math (randomness, VDF, consensus, reputation) | Invokable capabilities on the hub catalog |
| **aimarket-plugins** | TEE Escrow | Production escrow backend |
| **aimarket-widget** | 1-Click Agent Embed | Embeddable consumer UI |
| **aicom** | Auto-Mesh Pipeline | Factory orchestration source |
| **dioscuri** | Twin community agents | MNEMOSYNE Q&A from synced GitHub docs |

## Demo

No public demo yet — run the dashboard locally (see [Quick start](#quick-start)).

## Community

The [DIOSCURI](https://github.com/alexar76/dioscuri) twins answer questions from synced GitHub docs.

| Channel | Twin | Best for |
|---------|------|----------|
| [Discord](https://discord.gg/aimarket) | Pollux | Help, ideas, show-and-tell |
| [Telegram](https://t.me/just_for_agents) | Castor | Releases, digests, quick news |

**Ecosystem map:** [Alien Monitor](https://magic-ai-factory.com/monitor/) · [AICOM](https://magic-ai-factory.com)

## License

Apache-2.0 (align with parent monorepo).
