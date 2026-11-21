# Sellgar Infrastructure

Начинай с `README.md`. Рабочая ветка — `development`, ветка выпуска — `master`; отдельные ветки без запроса
пользователя не создавать.

- Репозиторий владеет конфигурацией окружений, подготовкой узлов и GitOps bootstrap.
- Общий переиспользуемый chart находится в `charts/application/`.
- Product использует `.github/workflows/build-service.yml` для сборки/публикации
  и `.github/workflows/deliver-service.yml` для прямой Helm-доставки.
  Этапы migrate/deploy видны в GitHub; Argo не должен управлять теми же ресурсами.
  JavaScript actions должны объявлять Node 24 или новее в собственном manifest;
  принудительный запуск устаревшего action на новом runtime не заменяет обновление.
  Переход работающей среды выполняется отдельно, с сохранением ресурсов:
  `docs/product-delivery.md`. Другие сервисы сохраняют Helm OCI-доставку.
  Репозиторий приложения хранит `helm/values.app.yaml` и
  `helm/<dev|prod>/values.yaml`, включая содержимое ConfigMap своей среды.
  Не копировать эти values в инфраструктурный репозиторий.
- Общие компоненты среды находятся в `environments/<environment>/platform/`.
- Не хранить credentials, kubeconfig, Docker config, данные БД и бакетов в Git.
  Ссылки на Secrets допустимы; значения — только после настройки шифрования.
- Образы закреплять через `repository:tag@sha256:digest`. При продвижении в prod
  сохранять digest, проверенный в dev.
- Для приложений, переведённых на Helm OCI, Application хранит постоянный источник
  пакетов своей среды и semver-диапазон. Не фиксировать digest отдельной сборки
  или source SHA в инфраструктурном Git: они входят в версионный пакет,
  публикуемый CI сервиса. Общий механизм: `.github/actions/publish-helm`,
  контракт и порядок перехода: `docs/helm-delivery.md`.
- Изменение inventory не означает развёртывание. Установку, миграцию данных
  и удаление ресурсов выполнять только в разрешённом scope.
- Проверять YAML, доступность закреплённых образов и затронутый runtime-сценарий.
  Не останавливать приложения и не подключать их volumes к проверочным контейнерам.

- Внутренний HTTP-порт приложений и Kubernetes Services — 8080. Ingress снаружи
  обслуживает стандартные HTTP/HTTPS порты. PostgreSQL, RabbitMQ и MinIO
  сохраняют штатные протокольные порты.
