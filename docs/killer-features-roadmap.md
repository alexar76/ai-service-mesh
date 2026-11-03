# Core Capabilities Roadmap (Ecosystem)

This roadmap distinguishes the Mesh integrations shipped today from ideas that require additional work.

| Product | Capability | Status in monorepo | Mesh integration |
|---------|------------|-------------------|------------------|
| **aimarket-hub** | Hub search and invocation | Available | Set `MESH_HUB_URL` for federated discovery and routed invocation |
| **aimarket-plugins** | TEE escrow integration | Roadmap | Mesh currently stores USD holds in its database |
| **aimarket-widget** | Agent embed | Widget available separately | Dashboard integration is on the roadmap |
| **aicom** | Factory pipeline | Separate stack | Mesh can invoke compatible agents over HTTP |

## Phase 1 (this folder — v0.1)

- [x] Mesh API with discovery → verify → escrow → invoke → settle
- [x] Activity dashboard (React)
- [x] Security hardening (CORS, SSRF, tokens, rate limit)
- [x] Unit tests + Locust load harness
- [x] Documentation

## Phase 2

- [ ] Wire `aimarket-plugins` TEE escrow for real holds/releases
- [ ] Signed invocation receipts (provenance plugin)
- [ ] mTLS between mesh and agent endpoints

## Phase 3

- [ ] Extract to standalone Git repository
- [ ] Public SDK (`@aimarket/mesh-client`)
- [ ] Multi-tenant org isolation

## Phase 4 (UI)

- [ ] Embed `aimarket-widget` in dashboard for 1-click consumer flows
- [ ] aicom Admin tab: "Mesh runs" linked to activity feed
