# AI Service Mesh 快速入门

[English](../README.md) · [Русский](README.ru.md) · [Español](README.es.md) · [Français](README.fr.md) · **简体中文**

Mesh 负责任务编排。它从本地已验证的注册记录和配置的 AIMarket Hub 中查找能力，检查候选服务是否可用，发起调用并记录结果。Mesh 在 SQLite 或 PostgreSQL 中保存以美元计价的预留记录。调用成功后释放预留，失败时标记为退款并尝试下一个候选。Hub 支付和 Base 链上结算使用独立流程。

## 本地启动

需要 Python 3.11 或更高版本。从单体仓库根目录运行以下命令。将 `MESH_HUB_URL` 留空可只搜索本地注册表。

```bash
cd ai-service-mesh/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
export MESH_ENV=development MESH_HOST=127.0.0.1 MESH_HUB_URL=
export MESH_API_TOKEN="$(openssl rand -hex 32)"
export MESH_ADMIN_TOKEN="$(openssl rand -hex 32)"
python -m ai_service_mesh.main
```

在另一个终端运行 `curl --fail http://127.0.0.1:8090/health` 检查 API。OpenAPI 文档位于 `/docs`。若要查看拓扑和事件，在 `ai-service-mesh/frontend` 中执行 `npm install && npm run dev`，然后打开 `http://localhost:5173`。

## 注册与调用

向 `POST /v1/agents` 发送 Bearer 令牌 `MESH_ADMIN_TOKEN`。使用 Ed25519 或 RSA PKCS#1 v1.5 与 SHA-256 对 UTF-8 字符串 `name|endpoint_url|cap1,cap2,...` 签名。先对能力列表排序，移除网址末尾的斜杠，再将签名编码为无填充的 base64url。也可以调用 Python 函数 `ai_service_mesh.verification.build_attestation()`。可通过检查的公网 HTTPS 地址和有效签名可获得 `verified` 状态。

用 Bearer 令牌 `MESH_API_TOKEN` 向 `POST /v1/tasks` 提交任务，传入 `intent` 和正值 `budget_usd`。HTTP 201 表示任务已创建并处理。通过 `status`、`error` 和 `hops` 查看结果。直接调用前，Mesh 先检查智能体的 `/health`，再访问 `/invoke`。经 Hub 路由时，Mesh 先检查 `/ai-market/v2/manifest`，再调用 `/ai-market/v2/invoke`。

## 访问控制与监控

设置 `MESH_PUBLIC_READ=0` 后，读取注册表、任务、指标和事件需要 API 令牌。生产 Compose 默认采用此设置。浏览器端 `POST /v1/ui/tasks` 默认关闭。启用时需要带身份验证的代理、显式配置和允许的 `Origin`。可通过 `AIFACTORY_CRYPTO_ENABLED` 启用可选的钱包绑定。使用 `GET /v1/activity` 或 SSE 流 `GET /v1/activity/stream` 查看事件。

## 进一步阅读

[API](api.md) · [架构](architecture.md) · [部署](deployment.md) · [安全](security.md)
