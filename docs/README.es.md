# AI Service Mesh — guía rápida

[English](../README.md) · [Русский](README.ru.md) · **Español** · [Français](README.fr.md) · [简体中文](README.zh.md)

Mesh coordina tareas. Busca registros locales verificados y capacidades del AIMarket Hub configurado, comprueba el destino, realiza la llamada y registra el resultado. Mesh guarda las retenciones en USD en SQLite o PostgreSQL. Libera la retención tras una llamada aceptada. Si la llamada falla, registra la devolución y puede probar otro candidato. Los pagos de Hub y la liquidación en Base siguen flujos separados.

## Inicio local

Se requiere Python 3.11 o posterior. Ejecuta los comandos desde la raíz del monorepositorio. Deja `MESH_HUB_URL` vacío para buscar solo en el registro local.

```bash
cd ai-service-mesh/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
export MESH_ENV=development MESH_HOST=127.0.0.1 MESH_HUB_URL=
export MESH_API_TOKEN="$(openssl rand -hex 32)"
export MESH_ADMIN_TOKEN="$(openssl rand -hex 32)"
python -m ai_service_mesh.main
```

En otra terminal, verifica la API con `curl --fail http://127.0.0.1:8090/health`. La documentación OpenAPI está en `/docs`. Para ver la topología y los eventos, ejecuta `npm install && npm run dev` desde `ai-service-mesh/frontend` y abre `http://localhost:5173`.

## Registro e invocación

Envía el token Bearer `MESH_ADMIN_TOKEN` a `POST /v1/agents`. Firma la cadena UTF-8 `name|endpoint_url|cap1,cap2,...` con Ed25519 o RSA PKCS#1 v1.5 con SHA-256. Ordena las capacidades, quita la barra final del destino y codifica la firma como base64url sin relleno. Puedes usar `ai_service_mesh.verification.build_attestation()`. Un destino HTTPS público válido y una firma válida permiten obtener el estado `verified`.

Envía la tarea a `POST /v1/tasks` con el token Bearer `MESH_API_TOKEN`. Incluye `intent` y un `budget_usd` positivo. El 201 indica que se creó y procesó la tarea. Consulta `status`, `error` y `hops` para ver el resultado. Mesh comprueba `/health` antes de `/invoke` para un agente local, y `/ai-market/v2/manifest` antes de `/ai-market/v2/invoke` para Hub.

## Acceso y seguimiento

Con `MESH_PUBLIC_READ=0`, el registro, las tareas, las métricas y los eventos requieren el token API. Es el valor predeterminado de Compose de producción. La ruta de navegador `POST /v1/ui/tasks` está desactivada por defecto. Requiere un proxy autenticado, activación explícita y un `Origin` permitido. `AIFACTORY_CRYPTO_ENABLED` habilita la vinculación opcional de billeteras. Consulta `GET /v1/activity` o el flujo SSE `GET /v1/activity/stream`.

## Más información

[API](api.md) · [Arquitectura](architecture.md) · [Despliegue](deployment.md) · [Seguridad](security.md)
