# Общий chart приложения

Версия 0.1.0. Создаёт Deployment, ClusterIP Service, опциональный Ingress и
ConfigMaps из переданных values. Chart не содержит настроек конкретного сервиса.

Приложение хранит:

```text
helm/
  values.app.yaml
  dev/values.yaml
  prod/values.yaml
```

`values.app.yaml` задаёт порт приложения, mounts, volumes, probes, resources и
путь Ingress. Values среды задают реплики, host/TLS и `configmaps`, включая
`nameOverride`, `enabled`, `filename` и содержимое файла в `data`.
Общий chart создаёт ресурс ConfigMap; его данные принадлежат приложению.

`image.repository` / `image.digest` берутся из CI Artifact `image-values.yaml`.
Пустой или неверный digest отклоняется. При обновлении ConfigMaps меняется
checksum pod template, запускающий rolling update с `maxUnavailable: 0`.

Пример проверки с checkout админки и image-values новой CI-сборки:

```bash
helm lint --strict charts/application \
  -f "$ADMIN/helm/values.app.yaml" \
  -f "$ADMIN/helm/dev/values.yaml" \
  -f "$RELEASE/image-values.yaml"

helm template admin-ui charts/application \
  -f "$ADMIN/helm/values.app.yaml" \
  -f "$ADMIN/helm/dev/values.yaml" \
  -f "$RELEASE/image-values.yaml"
```

`ADMIN` — checkout `sellgar.ui.admin`, `RELEASE` — скачанный Artifact CI.
Перед deployment фиксируются ревизии chart и values. Для админки нужен образ,
собранный для `/admin/`, а не предыдущий образ с корневым URL `/`.
TLS Secret и imagePullSecrets передаются по именам; credentials не добавляются
в values. Prod values админки пока не содержат адресов API/CDN и не включают
Ingress. Dev values сохраняют текущие localhost-адреса до развёртывания gateway.

Bootstrap Argo CD и подключение dev описаны в [../../bootstrap/README.md](../../bootstrap/README.md).
