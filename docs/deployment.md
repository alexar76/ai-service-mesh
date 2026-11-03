# Deploy AI Service Mesh

## Local development

Use the [backend and Vite quick start](../README.md#quick-start) to run the API at `127.0.0.1:8090` and the dashboard at `localhost:5173`.

The local Compose stack uses the monorepo to build the bundled Hub. Use strong `MESH_API_TOKEN` and `MESH_ADMIN_TOKEN` values in the Mesh project environment. Supply `MESH_POSTGRES_PASSWORD` when Compose validates the PostgreSQL service configuration. The automatically loaded `docker-compose.override.yml` maps the Mesh API to `127.0.0.1:8095` and the Hub is mapped to port 9083. The Compose dashboard image defaults to an Nginx proxy that expects the API on the same network namespace at `127.0.0.1:8090`. Use the Vite quick start or provide an Nginx config that resolves `mesh-api:8090` for a separate dashboard container.

## Production Compose

Run from the `ai-service-mesh/` directory. Start with `.env.example`, replace the placeholder tokens and set the existing Hub URL explicitly. This Compose file injects an explicit allowlist of settings from the Mesh project environment.

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.dashboard.yml up -d --build
```

The API and dashboard bind to `127.0.0.1:8090` and `127.0.0.1:8091`, respectively. Terminate TLS at the edge and route `/health`, `/docs`, `/openapi.json` and `/v1/` to the API. Route the rest to the static dashboard. Keep proxy buffering disabled for `/v1/activity/stream`.

The production template defaults to private API reads and browser writes disabled. For a public dashboard, explicitly decide which reads to expose. Send authenticated task requests through `POST /v1/tasks`. If a private dashboard needs browser task submission, use an authenticated proxy and configure the UI write switch and origin allowlist there. Never place the bearer tokens in public frontend assets.

Configure `MESH_DATABASE_URL` to use PostgreSQL with the `postgres` package extra. The default SQLite database lives under `MESH_DATA_DIR`. Both store the task history, activity and internal USD holds.

## Verify

1. Check `GET /health`.
2. Call `GET /v1/stats` with the API token when reads are private.
3. Confirm dashboard activity polling or SSE from the expected origin.
4. Submit a bounded test task only when the environment has an appropriate candidate. Inspect its status and hops.

Run the load tests against staging:

```bash
locust -f backend/load/locustfile.py --host https://mesh.staging.example \
  --headless -u 50 -r 10 -t 2m
```

Federated discovery uses the configured Hub's `/ai-market/v2/search`. An empty `MESH_HUB_URL` restricts discovery to locally registered agents.
