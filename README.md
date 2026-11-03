# AI Service Mesh

<!-- aicom-readme-badges -->
<p align="center">
  <a href="https://github.com/alexar76/ai-service-mesh/actions/workflows/ci.yml"><img src="https://github.com/alexar76/ai-service-mesh/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
  <a href="https://raw.githubusercontent.com/alexar76/ai-service-mesh/refs/heads/main/docs/badges/coverage.svg"><img src="https://raw.githubusercontent.com/alexar76/ai-service-mesh/refs/heads/main/docs/badges/coverage.svg" alt="Test coverage" /></a>
  <a href="https://github.com/alexar76/ai-service-mesh/blob/main/LICENSE"><img src="https://raw.githubusercontent.com/alexar76/ai-service-mesh/refs/heads/main/docs/badges/license.svg" alt="License: MIT" /></a>
</p>
<!-- /aicom-readme-badges -->

<!-- aicom-mirror-notice -->
> 🔄 Synced from the [AI-Factory monorepo](https://github.com/alexar76/aicom) (append-only history). **Pull requests are welcome** — merged PRs are imported back and re-synced here. [Issues](https://github.com/alexar76/ai-service-mesh/issues) · [Pull requests](https://github.com/alexar76/ai-service-mesh/pulls)









**English** · [Русский](docs/README.ru.md) · [Español](docs/README.es.md) · [Français](docs/README.fr.md) · [简体中文](docs/README.zh.md)

[Live dashboard](https://service-mesh.modelmarket.dev/) · [AICOM ecosystem](https://ecosystem.modelmarket.dev/) · [Landing](https://alexar76.github.io/ai-service-mesh/)

AI Service Mesh coordinates agent tasks. It searches verified local registrations and an optional AIMarket Hub, checks a candidate's endpoint, invokes the candidate, and records the result and USD hold in its database. The Mesh runs independently of AI-Factory and talks to the Hub over HTTP.

Local registration uses a private-key signature. A direct call checks the agent's `/health` before `/invoke`. A Hub-routed call checks the Hub manifest before using its invocation endpoint. Mesh accounts for holds in SQLite or PostgreSQL. Hub payments and Base settlement run on separate rails.

## Quick start

### Backend (API)

Requires Python 3.11 or newer. Run from the monorepo:

```bash
cd ai-service-mesh/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
export MESH_ENV=development MESH_HOST=127.0.0.1 MESH_HUB_URL=
export MESH_API_TOKEN="$(openssl rand -hex 32)"
export MESH_ADMIN_TOKEN="$(openssl rand -hex 32)"
python -m ai_service_mesh.main
```

API probe: [http://127.0.0.1:8090/health](http://127.0.0.1:8090/health). Interactive OpenAPI is at `/docs`. An empty `MESH_HUB_URL` keeps discovery local. See the [API reference](docs/api.md) for registering a signed agent and submitting a task.

### Dashboard (frontend)

From the monorepo in a second terminal:

```bash
cd ai-service-mesh/frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) to inspect topology and activity. The browser task route is off by default. Submit tasks from the API with the bearer token. See [deployment](docs/deployment.md) for Compose ports and dashboard write configuration.

## Configuration

| Variable | Description |
|---|---|
| `MESH_API_TOKEN` | Bearer token for `POST /v1/tasks` and private reads |
| `MESH_ADMIN_TOKEN` | Bearer token for registration and optional wallet binding |
| `MESH_CORS_ORIGINS` | Comma-separated browser origins, default `http://localhost:5173` |
| `MESH_PUBLIC_READ` | Application default `1`. Production Compose defaults to `0`. |
| `MESH_ALLOW_UI_WRITES` | Browser task route, off by default. Enable only behind authenticated ingress. |
| `MESH_HUB_URL` | AIMarket Hub for discovery and routing. Empty disables Hub discovery. |
| `MESH_RATE_LIMIT` | Requests per minute per IP, default 120 |
| `AIFACTORY_CRYPTO_ENABLED` | Optional wallet binding, off by default |

See [security](docs/security.md) and [.env.example](.env.example).

## Mesh pipeline

```
Task → Discovery → Preflight → Ledger hold → Invoke → Release or refund
```

Each phase emits events on `/v1/activity` for the dashboard and external observability.

## Tests

```bash
cd ai-service-mesh/backend
pytest -q -m 'not integration'
```

The integration tests expect a running Mesh API, a local agent with signed registration, and matching API/admin tokens. The Hub demo-rejection test also needs a Hub with demo-only matches.

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
| **aimarket-hub** | Capability catalog and invocation API | Federated search and routed invocation |
| **oracles** | Verifiable math (randomness, VDF, consensus, reputation) | Invokable capabilities on the hub catalog |
| **aimarket-widget** | 1-Click Agent Embed | Embeddable consumer UI |
| **aicom** | AI-Factory orchestration | Separate stack |
| **dioscuri** | Twin community agents | MNEMOSYNE Q&A from synced GitHub docs |

## Demo

- **Live dashboard:** [service-mesh.modelmarket.dev](https://service-mesh.modelmarket.dev/)
- **Landing:** [alexar76.github.io/ai-service-mesh](https://alexar76.github.io/ai-service-mesh/)
- Local: see [Quick start](#quick-start)

## Community

The [DIOSCURI](https://github.com/alexar76/dioscuri) twins answer questions from synced GitHub docs.

| Channel | Twin | Best for |
|---------|------|----------|
| [Discord](https://discord.gg/JjWxGhW9pP) | Pollux | Help, ideas, show-and-tell |
| [Telegram](https://t.me/just_for_agents) | Castor | Releases, digests, quick news |

**Ecosystem map:** [Alien Monitor](https://monitor.modelmarket.dev/) · [AICOM](https://magic-ai-factory.com)

## License

Apache-2.0.
