# AI Service Mesh — краткое руководство

[English](../README.md) · **Русский** · [Español](README.es.md) · [Français](README.fr.md) · [简体中文](README.zh.md)

Mesh координирует задачи. Он ищет проверенные локальные регистрации и возможности в настроенном AIMarket Hub, проверяет доступность кандидата, делает вызов и записывает результат. Mesh хранит резервы в USD в SQLite или PostgreSQL. При успешном вызове резерв закрывается, при сбое освобождается, и Mesh может попробовать следующего кандидата. Платежи Hub и расчёты в Base идут отдельно.

## Локальный запуск

Нужен Python 3.11 или новее. Выполните из корня монорепозитория. Пустой `MESH_HUB_URL` ограничивает поиск локальным реестром.

```bash
cd ai-service-mesh/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
export MESH_ENV=development MESH_HOST=127.0.0.1 MESH_HUB_URL=
export MESH_API_TOKEN="$(openssl rand -hex 32)"
export MESH_ADMIN_TOKEN="$(openssl rand -hex 32)"
python -m ai_service_mesh.main
```

Во втором терминале проверьте API через `curl --fail http://127.0.0.1:8090/health`. Схема OpenAPI доступна по `/docs`. Для просмотра топологии и событий запустите `npm install && npm run dev` из `ai-service-mesh/frontend` и откройте `http://localhost:5173`.

## Регистрация и вызов

Для регистрации отправьте в `POST /v1/agents` токен `MESH_ADMIN_TOKEN` в заголовке Bearer. Подпишите строку UTF-8 `name|endpoint_url|cap1,cap2,...` ключом Ed25519 или RSA PKCS#1 v1.5 с SHA-256. Отсортируйте возможности, уберите завершающий слеш из адреса и закодируйте подпись в base64url без заполнения. Помощник Python — `ai_service_mesh.verification.build_attestation()`. Допустимый публичный HTTPS-адрес и верная подпись позволяют получить статус `verified`.

Подайте задачу через `POST /v1/tasks` с `MESH_API_TOKEN` в заголовке Bearer. Передайте `intent` и положительный `budget_usd`. Ответ 201 означает, что задача создана и обработана. Итог проверяйте по `status`, `error` и `hops`. Для локального агента Mesh проверяет `/health` перед `/invoke`. Для Hub он проверяет `/ai-market/v2/manifest` перед `/ai-market/v2/invoke`.

## Доступ и наблюдение

При `MESH_PUBLIC_READ=0` чтение реестра, задач, метрик и событий требует токен API. В производственном Compose это значение задано по умолчанию. Браузерный `POST /v1/ui/tasks` выключен по умолчанию. Для него нужны прокси с аутентификацией, явное включение и разрешённый `Origin`. `AIFACTORY_CRYPTO_ENABLED` включает привязку кошелька, которая по умолчанию отключена. Проверяйте историю в `GET /v1/activity` или через поток SSE `GET /v1/activity/stream`.

## Далее

[API](api.md) · [Архитектура](architecture.md) · [Развёртывание](deployment.md) · [Безопасность](security.md)
