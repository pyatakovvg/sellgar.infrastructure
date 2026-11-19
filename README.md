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
не дублируются. Argo CD получает общий chart отсюда, а values — из
репозитория приложения. В Application выбираются ревизии chart/values и digest образа.
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
Ansible и deployment остальных сервисов пока не подключены.
