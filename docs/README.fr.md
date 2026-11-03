# AI Service Mesh — guide de démarrage

[English](../README.md) · [Русский](README.ru.md) · [Español](README.es.md) · **Français** · [简体中文](README.zh.md)

Mesh orchestre les tâches. Il recherche les agents vérifiés du registre local et les capacités du Hub AIMarket configuré, vérifie la disponibilité du candidat, l’appelle et consigne le résultat. Mesh conserve les réservations en USD dans SQLite ou PostgreSQL. Il libère la réservation si l’appel est accepté et la marque comme remboursée en cas d’échec avant de tenter un autre candidat. Les paiements du Hub et le règlement sur Base suivent des circuits distincts.

## Démarrage local

Python 3.11 ou supérieur est requis. Exécutez les commandes à la racine du monorepo. Laissez `MESH_HUB_URL` vide pour limiter la recherche au registre local.

```bash
cd ai-service-mesh/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
export MESH_ENV=development MESH_HOST=127.0.0.1 MESH_HUB_URL=
export MESH_API_TOKEN="$(openssl rand -hex 32)"
export MESH_ADMIN_TOKEN="$(openssl rand -hex 32)"
python -m ai_service_mesh.main
```

Dans un deuxième terminal, vérifiez l’API avec `curl --fail http://127.0.0.1:8090/health`. La documentation OpenAPI se trouve à `/docs`. Pour consulter la topologie et les événements, exécutez `npm install && npm run dev` dans `ai-service-mesh/frontend`, puis ouvrez `http://localhost:5173`.

## Inscription et appel

Envoyez le jeton Bearer `MESH_ADMIN_TOKEN` à `POST /v1/agents`. Signez la chaîne UTF-8 `name|endpoint_url|cap1,cap2,...` avec Ed25519 ou RSA PKCS#1 v1.5 et SHA-256. Triez les capacités, retirez la barre oblique finale de l’URL et encodez la signature en base64url sans remplissage. Vous pouvez utiliser `ai_service_mesh.verification.build_attestation()`. Une URL HTTPS publique valide et une signature valide permettent d’obtenir le statut `verified`.

Soumettez une tâche via `POST /v1/tasks` avec le jeton Bearer `MESH_API_TOKEN`. Fournissez `intent` et un `budget_usd` positif. Le code 201 confirme la création et le traitement de la tâche. Consultez `status`, `error` et `hops` pour connaître le résultat. Mesh vérifie `/health` avant `/invoke` pour un agent local et `/ai-market/v2/manifest` avant `/ai-market/v2/invoke` pour le Hub.

## Accès et suivi

Avec `MESH_PUBLIC_READ=0`, la consultation du registre, des tâches, des mesures et des événements requiert le jeton API. C’est le réglage par défaut du Compose de production. La route navigateur `POST /v1/ui/tasks` est désactivée par défaut. Elle exige un proxy authentifié, une activation explicite et un en-tête `Origin` autorisé. `AIFACTORY_CRYPTO_ENABLED` active l’association facultative d’un portefeuille. Consultez `GET /v1/activity` ou le flux SSE `GET /v1/activity/stream`.

## Pour aller plus loin

[API](api.md) · [Architecture](architecture.md) · [Déploiement](deployment.md) · [Sécurité](security.md)
