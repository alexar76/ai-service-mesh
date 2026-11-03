# AI Service Mesh security

| Control | Current behavior |
|---|---|
| Registration | Requires the admin bearer token and a public HTTPS endpoint that passes SSRF checks. Opt-in loopback HTTP is intended for local exercises. |
| Registration signature | Ed25519 or RSA PKCS#1 v1.5/SHA-256 over the canonical registration fields. Mesh verifies possession of the corresponding private key. |
| Direct preflight and invocation | Mesh checks and pins the resolved address on each connection, rejects redirects and bounds response bodies. |
| Server API | Task submission requires the API bearer token in every environment. Set `MESH_PUBLIC_READ=0` to protect task, registry, stats and activity reads. |
| Browser task submission | Off by default. Explicitly enable it only behind an authenticated proxy. The origin allowlist adds a browser guard. |
| Network exposure | The production overlay binds the API to loopback. Forwarded addresses are trusted only when `MESH_TRUST_FORWARDED_FOR=1`. Configure a trusted edge before enabling that setting. |
| Rate limiting | The API keeps a per-IP limiter in process. |
| Tokens | Production startup rejects empty and known default tokens unless the insecure-default override is set. A known compromised token is rejected independently of that override. |

The registration message is UTF-8 `name|endpoint_url|cap1,cap2,...` with capabilities sorted, the endpoint normalized without a final slash and the resulting signature encoded in base64url. The signature authenticates the submitted metadata. Runtime checks include endpoint preflight and HTTP result checks. The Mesh ledger does not independently verify an AWR receipt or a hardware attestation before releasing a hold.

`MESH_CORS_ORIGINS` accepts a comma-separated allowlist. The application default allows `http://localhost:5173`; an empty value disables CORS. The API applies frame, MIME and referrer response headers. Treat the operator-configured `MESH_HUB_URL` as a trusted destination.

For deployment and incident handling, see the [deployment guide](deployment.md) and the [security policy](../SECURITY.md).
