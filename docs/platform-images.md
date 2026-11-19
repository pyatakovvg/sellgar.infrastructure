# Образы общей инфраструктуры

Дата подготовки: 18 ноября 2026 года.
Полные ссылки находятся в `environments/dev/platform/images.yaml` и
`environments/prod/platform/images.yaml`.

| Компонент | Выпуск | Источник |
|---|---|---|
| PostgreSQL | 16.16, standard-trixie | CloudNativePG, готовый operand image |
| RabbitMQ | 4.4.1-management | Docker Official Image |
| MinIO | RELEASE.2025-09-07T16-13-09Z | имеющийся образ, сохранённый в GHCR |
| MinIO Client | RELEASE.2025-08-13T08-35-41Z | имеющийся образ `mc`, сохранённый в GHCR |

## PostgreSQL и RabbitMQ

Используются upstream images без нашей пересборки. Закреплены digest индексов
multi-platform images. Локальные проверки выполняются на `linux/amd64`.

Образ PostgreSQL предназначен для CloudNativePG. Он не является заменой
`postgres` Docker Official Image с его entrypoint и переменными инициализации.
При настройке оператора сохранять tag версии вместе с digest:
CloudNativePG определяет major PostgreSQL из имени образа.

## Сохранение MinIO

Скопированы исполняемые образы, без volumes, данных и credentials.
Исходные registry endpoints на момент подготовки не позволили получить
этот выпуск; публикация сделана из сохранённых локальных images.
Собственная сборка и изменение программы не выполнялись.

| Параметр | MinIO | MinIO Client |
|---|---|---|
| Repository | `ghcr.io/pyatakovvg/sellgar-minio` | `ghcr.io/pyatakovvg/sellgar-minio-client` |
| Исходный image ID | `sha256:69b2ec208575b69597784255eec6fa6a2985ee9e1a47f4411a51f7f5fdd193a9` | `sha256:c2ad77420d33bb4ad8694457d3edf7188076428582bd24e3dd4d09d6a1d52872` |
| Commit программы | `07c3a429bfed433e49018cb0f78a52145d4bedeb` | `7394ce0dd2a80935aded936b09fa12cbb3cb8096` |
| Платформа опубликованного образа | `linux/amd64` | `linux/amd64` |

Digest в inventory получен после публикации в GHCR. Он отличается от digest
старого upstream multi-platform index: сохранена только имеющаяся amd64-платформа.
После публикации оба образа получены из GHCR по digest. Image ID каждого
совпал с исходным: содержимое сохранено без изменений.

`mc` нужен для первоначальной настройки бакетов и функциональной проверки S3.
Приложения продолжают обращаться к MinIO через S3 SDK.

Выбор старого образа принят для локальной отработки. В сентябрьском MinIO
нет исправления проверки session policies из октябрьского релиза
`RELEASE.2025-10-15T17-29-55Z`. До запуска production нужен обновлённый
образ и повторная проверка S3-операций.

## Проверки

Для функциональных проверок создаются отдельные Docker containers с пустыми
tmpfs-хранилищами. Доступ к тестовому management API RabbitMQ ограничивается
`127.0.0.1`; credentials генерируются на время проверки и не сохраняются в Git.
Volumes приложений и данные локальной разработки не используются.

18 ноября 2026 года все перечисленные проверки прошли:

- PostgreSQL: версия, `initdb`, создание таблицы, запись и чтение строки.
- RabbitMQ: авторизация в management API, создание очереди, публикация,
  получение и подтверждение сообщения через management API.
- MinIO: авторизация через `mc`, создание бакета, запись, чтение и удаление
  объекта, удаление бакета.

Фактические версии: PostgreSQL `16.16`, RabbitMQ `4.4.1`,
MinIO `RELEASE.2025-09-07T16-13-09Z`.
Временные контейнеры, сеть, credentials и tmpfs-хранилища удалены после проверки.
YAML обоих inventory разобран; у каждой ссылки проверено наличие tag и SHA-256 digest.

Это проверка выбранных images, а не установки операторов Kubernetes,
AMQP-подключений сервисов Sellgar или production deployment.

## Источники

- [CloudNativePG container images](https://cloudnative-pg.io/documentation/current/container_images/)
- [RabbitMQ releases](https://www.rabbitmq.com/release-information)
- [MinIO: исходники и условия распространения](https://github.com/minio/minio)
- [MinIO: октябрьское исправление](https://github.com/minio/minio/releases/tag/RELEASE.2025-10-15T17-29-55Z)
- [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
