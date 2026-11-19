# Product service: dev deployment

Product владеет `code/`, корневыми Dockerfile/CI и `helm/` values. Infrastructure
владеет Argo CD Application, общей Helm-схемой, ролью и базой PostgreSQL.
Рабочая ветка — `development`. Одна реплика, внутренний HTTP/Service 8080,
без внешнего Ingress. Клиент команд — существующий Admin gateway.

## Данные и конфигурация

Это чистая база `product_srv_v2`, без импорта локальных товаров/справочников.
CloudNativePG создаёт одноимённую роль без superuser из Secret `product-database`.
Database resource сохраняет данные через reclaim policy retain.
Личный пользователь PostgreSQL и его права не изменяются.

Все семь миграций запускаются Sync Job перед Deployment; повторный запуск не
изменяет схему. TypeORM synchronize отключён. ConfigMap приложения монтируется
как `/app/.env`; Secret env refs содержат credentials, отсутствующие в Git/образе.
`PRODUCT_AMQP_URL` собирается Kubernetes env expansion из ранее определённых
`AMQP_USERNAME`/`AMQP_PASSWORD` Secret refs. Нынешние dev credentials URI-safe.
При замене на содержащие URI-разделители потребуется кодирование credentials
для существующего URL-контракта, без помещения пароля в ConfigMap.

Очереди остаются `product.v2.commands` и `product.v2.events`, topic exchange —
`event.exchange`. File events поступают в существующий inbox, исходящие полные
снимки Product — через общую `@sellgar/outbox` в том же процессе.

## Проверки и обновление

CI собирает Node 24 image. Отдельный build stage с PostgreSQL 16 выполняет
104 теста, включая SQL-проекции изображений; семь FTS-тестов запускаются отдельно
по env-флагу. Бинарники PostgreSQL отсутствуют в runtime-образе.

Production-image smoke создаёт только временные PostgreSQL/RabbitMQ, проверяет
пустую базу, семь миграций и повторный запуск, RMQ catalog create/read/update,
поиск, варианты и изображения, получение File events, ответы 400/409 и четыре
упорядоченных полных снимка из outbox. Runtime работает non-root/read-only с
монтируемым `.env`; отключение проверочного RabbitMQ переводит health в 503.

`/health` проверяет PostgreSQL и оба RMQ consumer; liveness проверяет TCP.
Общий chart: RollingUpdate maxSurge 1/maxUnavailable 0, readiness и grace period.
Это не доказательство отсутствия потерь всех активных RMQ-команд при rollout.

После CI закрепить digest/source/CI run в `environments/dev/services/product-service/`.
Проверить Synced/Healthy, Deployment 1/1, таблицу migrations и сценарий создания
товара через dev-админку с последующим повторным чтением. Store/File/Media
разворачиваются отдельно; их готовность этим этапом не подтверждается.
