# Cart, File и Media в dev

Исходники и Yarn root каждого сервиса находятся в `code/`, Dockerfile и CI — в
корне, ConfigMap `.env` и ссылки на Secrets — в `helm/`. Одна реплика,
внутренний HTTP-порт 8080. Публичные бизнес-операции проходят через gateway.

| Сервис | Данные | Проверка готовности |
|---|---|---|
| Cart | База/роль `cart_srv`, Secret `cart-database` | PostgreSQL и оба RMQ consumers |
| File | База/роль `file_srv`, Secret `file-database` | PostgreSQL и оба RMQ consumers |
| Media | Бакет `sellgar`, пользователь `sellgar-media`, Secret `media-storage` | RMQ consumer и доступность бакета |

Cart и File используют явные миграции; Job выполняется перед Deployment,
`synchronize` отключён. Новые базы создаёт CloudNativePG из template0 с UTF8 и
C.UTF-8; каждая роль ограничена собственной базой и не является superuser.

`ansible/secrets.yml` создаёт только отсутствующие Secrets; существующие значения
сохраняются. SeaweedFS создаёт бакет `sellgar` штатным hook официального Helm chart,
а S3 identities получает из конфигурации с Secret env refs. Media ограничен своим
бакетом и не получает административные credentials. Подробнее: [SeaweedFS](seaweedfs.md).

Ingress Media публикует только `/images` на `https://cdn.dev.sellgar.ru`. Загрузка
`/internal/objects` доступна admin gateway по `http://media-service:8080`;
внешнего Ingress к этому пути нет. File и Cart Ingress не имеют.

Каждый push development проходит build/tests, production-image smoke, image
publication и publication Helm-пакета своей среды. Постоянные Argo Applications
следят за `>=0.0.0` OCI-пакетов. Infrastructure Git не меняется на каждый выпуск.
Prod promotion сохраняет digest проверенного кандидата и запускается вручную
из master; production среда пока не развёрнута.

Cart Docker verifier выполняет unit и integration tests на временной PostgreSQL.
Cart/File smoke проверяет чистую базу, повтор миграций, RMQ и readiness. Media
smoke проверяет Sharp, RMQ и отказ readiness при недоступном MinIO; положительный
storage flow проверяется отдельно на dev MinIO при приёмке. Ни одна CI job не
получает credentials dev-кластера и не использует его данные.


## Приёмка dev, 2026-11-20

Проверен полный путь: сохранение товара через админку, коррекция остатка до 5,
получение предложения витриной и добавление одной штуки в тестовую корзину.
Приватный сокет доставил полный снимок Cart schemaVersion 2 с названием, ценой
1250 RUB, количеством 1 и доступным остатком 5; HTTP-перечитывание после записи
для проверки не использовалось. Карточка этой корзины открывается в админке.

Тестовый PNG загружен через File/Media: metadata получила status ready, публичный
GET `/images/:uuid` вернул image/png и исходные байты. Внешний Ingress по-прежнему
публикует только чтение `/images`, внутренний upload не открыт.

Повторные выпуски gateway и UI обнаружены Argo автоматически, без индивидуального
refresh Application, перезапуска Deployment или коммита версии в infrastructure.
