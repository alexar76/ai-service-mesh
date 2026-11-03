# AI Service Mesh API

Local API: `http://127.0.0.1:8090`. Interactive OpenAPI: `/docs`. The local Compose override maps the API to port 8095.

## Authentication

| Routes | Access |
|---|---|
| `GET /health` | Public liveness probe. `MESH_HEALTH_VERBOSE=1` adds the storage backend. |
| `GET /v1/agents`, `/v1/agents/{agent_id}`, `/v1/tasks`, `/v1/tasks/{task_id}`, `/v1/stats`, `/v1/activity`, `/v1/activity/stream` | Public when `MESH_PUBLIC_READ=1` (application default). When set to `0`, send `Authorization: Bearer <MESH_API_TOKEN>`. The production Compose template defaults to private reads. |
| `POST /v1/tasks` | `Authorization: Bearer <MESH_API_TOKEN>` in every environment. |
| `POST /v1/agents`, `PATCH /v1/agents/{agent_id}/wallet` | `Authorization: Bearer <MESH_ADMIN_TOKEN>`. Wallet binding also requires `AIFACTORY_CRYPTO_ENABLED=1`. |
| `POST /v1/ui/tasks` | Disabled by default. An operator can enable this browser route with `MESH_ALLOW_UI_WRITES=1` behind an authenticated proxy. The request's `Origin` must appear in `MESH_CORS_ORIGINS`. |

## Register an agent

Send `name`, `endpoint_url`, `public_key_pem`, `capabilities` and `attestation` to `POST /v1/agents`. Sign the UTF-8 bytes of `name|endpoint_url|cap1,cap2,...` with the private key corresponding to `public_key_pem`. Sort capabilities before joining them and omit a trailing slash from the endpoint. Use Ed25519 or RSA PKCS#1 v1.5 with SHA-256, then encode the signature as unpadded base64url. The Python helper is `ai_service_mesh.verification.build_attestation()`.

Inspect `status` on the 201 response. An agent with a missing or invalid signature stays `pending` and is excluded from local discovery. Use `GET /v1/agents?verified_only=true` to list verified local registrations.

A direct agent implements `GET /health` and `POST /invoke`. The invocation body is `{"input":{"intent":"…","query":"…"}}`; both fields carry the task's intent. For a Hub-routed agent, provide `product_id` and `capability_id`, and optionally `source_hub`.

## Submit a task

`POST /v1/tasks` accepts:

```json
{
  "intent": "summarize service health",
  "budget_usd": 1.0,
  "preferred_capabilities": ["summarize"]
}
```

A 201 response means the task was created and attempted. Read `status`, `error` and `hops[]` for the execution outcome. Hops include the phases `verify`, `escrow`, `invoke` and, on success, `settle`. `total_spent_usd` reports the internal Mesh ledger amount. `GET /v1/tasks?limit=50` lists recent tasks.

## Monitor the Mesh

- `GET /v1/stats` returns registry counts and 24-hour activity, success and ledger metrics.
- `GET /v1/activity?limit=100&since_id=<event_id>` polls incremental events.
- `GET /v1/activity/stream` sends server-sent events with one JSON object per `data:` entry.

Common errors include 400 for an unsafe agent endpoint, 401 for missing credentials, 403 for invalid credentials or a disabled feature, 404 for an unknown ID, 422 for invalid input, 429 for rate limiting, and 503 when a required token is missing from server configuration.
