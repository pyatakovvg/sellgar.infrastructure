# Sellgar Infrastructure

Желаемое состояние двух сред Sellgar: `dev` в локальной K3s VM и `prod` на VPS.
Обе среды описаны отдельными каталогами. Рабочая ветка — `development`,
ветка выпуска — `master`.

## Размещение файлов

```text
ansible/                         подготовка серверов и K3s
bootstrap/                       первоначальная настройка GitOps
charts/application/             общий chart stateless HTTP-приложений
environments/<dev|prod>/
  platform/                      PostgreSQL, RabbitMQ, MinIO и общие компоненты
    images.yaml                  закреплённые образы на этапе подготовки
  services/<service>/
    application.yaml             источник chart и назначение Argo CD
docs/
  platform-images.md             происхождение образов и результаты проверок
```

Сейчас реализован этап подготовки образов: `platform/images.yaml` для двух сред.
Это inventory, а не Kubernetes manifests и не готовый Helm release.
Остальные каталоги создаются вместе с соответствующей реализацией.
Файлы `images.yaml` не нужно применять через `kubectl apply`.

Общий chart находится в `charts/application/`. Приложение хранит общие values
в `helm/values.app.yaml`, а параметры dev/prod и ConfigMap — в
`helm/<environment>/values.yaml` своего репозитория. Это принятая структура по
примеру `payment-terminal.app.ui/helm`. Kubernetes templates в каждом приложении
не дублируются. Для Helm OCI доставки CI включает общий chart и values в версионный пакет GHCR.
Argo CD следит за пакетами среды; инфраструктурный Git не меняется при каждом выпуске.
Контракт: [helm-delivery.md](docs/helm-delivery.md). Админка переводится на этот механизм;
остальные приложения пока используют прежние multi-source Applications с закреплённым digest.
Конфигурация операторов и общих хранилищ принадлежит `platform/`.

## Образы

PostgreSQL использует образ CloudNativePG для будущего запуска через оператор.
RabbitMQ использует официальный образ с management plugin.
MinIO и `mc` сохранены в GHCR из имеющихся образов без пересборки.
Версии и digest перечислены в `environments/<environment>/platform/images.yaml`.

Inventory среды меняется отдельно: обновление dev не должно автоматически менять prod.
Продвижение переносит проверенный digest без повторной сборки.
На этапе реализации Helm/операторов закреплённые ссылки станут параметрами
развёртывания; отдельную несинхронизированную копию inventory сохранять не нужно.

Данные с локальной машины не переносятся: инфраструктура создаётся с пустыми
хранилищами и новыми credentials. Образы содержат исполняемые программы.

Для закрытых GHCR packages кластеру потребуется доступ на чтение через Secret.
Авторизация Docker на рабочей машине автоматически в K3s не передаётся.
Значения Secrets и Docker config в этот репозиторий не добавляются.

## Текущий результат

Получение образов и проверки на пустых временных хранилищах описаны
в [platform-images.md](docs/platform-images.md).
MinIO из этого inventory предназначен для текущей локальной отработки;
перед production требуется обновление с исправлением безопасности.
Файлы prod пока фиксируют базовый набор образов и не запускают deployment.

Следующий этап — установка операторов PostgreSQL и RabbitMQ, конфигурация MinIO,
PersistentVolumes и Secrets для dev, затем подключение GitOps.
Общий chart подготовлен и описан в [charts/application/README.md](charts/application/README.md).
Bootstrap Argo CD находится в `bootstrap/argocd`, корневой dev Application —
в `bootstrap/dev`. Порядок установки: [bootstrap/README.md](bootstrap/README.md).
Dev Application админки находится в `environments/dev/services/admin-ui/`;
обновление версии и проверки описаны в [docs/admin-ui.md](docs/admin-ui.md).
Dev-подключение витрины описано в [docs/storefront.md](docs/storefront.md).
Ansible и deployment backend-сервисов пока не подключены.

## Development platform and credentials

`environments/dev/platform/` deploys PostgreSQL (CloudNativePG), RabbitMQ
(Cluster Operator), and MinIO with fresh local-path PVCs. All endpoints are
ClusterIP-only. Data is retained independently of application releases;
`dev-platform` intentionally disables automated pruning.

First install `bootstrap/operators/` in documented order. Then run
`python3 bootstrap/dev/create-platform-secrets.py kubectl --kubeconfig <path>`.
This creates missing random credentials directly in Kubernetes and preserves
existing Secrets. PostgreSQL bootstraps `socket_srv` database/owner from
`socket-database`; RabbitMQ operator creates `rabbitmq-default-user`.
`socket-auth` is shared by all three gateway ticket implementations;
`admin-auth` is admin fingerprint signing, `minio-root` is storage administration.
Private GHCR images require a separately provisioned `ghcr-pull` dockerconfigjson
Secret with registry pull access. Never commit Docker config or credentials.
Changing a Secret does not itself rotate database/broker passwords; rotation
must update both the owning platform and clients deliberately.

The app chart accepts literal env values or `valueFrom.secretKeyRef`. ConfigMaps
contain only non-secret `.env` data. Socket migration runs as a Sync hook after
its ConfigMap (wave -2) and before Deployment (wave 0). Migration failure blocks
rollout; the old ready deployment remains available during a normal upgrade.
Traefik strips `/api/admin` and `/api/client`; `/socket.io` is preserved for
physical channel paths. Kubernetes readiness removes unready pods from routing.
Socket transports are WebSocket-only and require no polling sticky sessions.

To administer services use authenticated `kubectl port-forward` or SSH tunnel,
not public database/broker/MinIO console Ingress. Examples:
`kubectl -n sellgar-dev port-forward service/postgresql-rw 15432:5432`,
`kubectl -n sellgar-dev port-forward service/rabbitmq 15672:15672`,
`kubectl -n sellgar-dev port-forward service/minio 19001:9001`.
Retrieve credentials through your authorized Kubernetes client; never paste them
into issues or logs. These manifests do not provision domain service databases
or restore any existing host data.

Internal application HTTP listeners and ClusterIP Services use port `8080`.
The chart derives the Service port from `applicationPort` (default `8080`);
Ingress routes use its named `http` port. Internal app URLs include `:8080`.
Infrastructure protocols retain their standard ports. Local host development
ports remain distinct so applications can run together outside Kubernetes.

## Identity development deployment

Identity service is configured in `environments/dev/services/identity-service/`.
CloudNativePG owns its separate database/role, Secrets are bootstrapped without
Git values, and the service migrates before rollout. Fresh installation and the
explicitly requested one-account import are described in [docs/identity-service.md](docs/identity-service.md).

Shop follows the same deployment contract in `environments/dev/services/shop-service/`
and has its own database/role `shop_srv`. Details and checks:
[docs/shop-service.md](docs/shop-service.md).

Product service: [dev deployment](docs/product-service.md), отдельная база `product_srv_v2`.

Store service: [dev deployment](docs/store-service.md), отдельная база `store_srv` с Unicode locale.
