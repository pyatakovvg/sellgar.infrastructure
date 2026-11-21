# Общий chart приложения

Создаёт Deployment, ClusterIP Service, опциональный Ingress/Middleware и ConfigMap.
Chart не содержит настроек конкретного приложения. Его values принадлежат сервису:
`helm/values.app.yaml`, `helm/dev/values.yaml`, `helm/prod/values.yaml`.

`image.repository` и `image.digest` закрепляют опубликованный образ. Пустой или
неверный digest отклоняется. `releaseId` и `sourceRevision` связывают runtime
с конкретной попыткой доставки; RollingUpdate использует `maxUnavailable: 0`.

## Runtime-конфигурация

`environmentFile.enabled: true` создаёт immutable ConfigMap с именем
`<release>-env-<releaseId>`. `environmentFile.data` приходит из values среды;
`filename` по умолчанию `.env`, `mountPath` — `/app/.env`.
Admin UI использует `config.js` и `/usr/share/nginx/html/config.js`,
Next — `.env` и `/app/clients/desktop/.env`.
ConfigMap сохраняется в истории (`helm.sh/resource-policy: keep`), поэтому старый
pod не получает новую конфигурацию при повторном запуске.
Credentials задаются только `env.*.valueFrom.secretKeyRef`, не содержимым файла.

Legacy `configmaps`/ручные volumes пока поддерживаются для старых закреплённых
пакетов, но новые CI-потребители используют `environmentFile`.

## Раздельные workloads

- `workload: application` рендерит ресурсы приложения без миграций при
  `migration.enabled: false`.
- `workload: migration` рендерит только ConfigMap и Kubernetes Job из отдельного
  `migration.image`. Этот image содержит CLI и миграции. БД credentials задаются
  отдельным `migration.env`; доступы брокера/подписи приложению не нужны в Job.

Миграции выполняются и ожидаются отдельной GitHub job перед Helm upgrade.
Для gateway без БД и UI migration workload не вызывается.
Прежний `migration.enabled: true` оставлен для старых Argo Sync-пакетов,
но новая доставка им не пользуется. Ни один ресурс не исполняет DB rollback.

## Проверка

Из checkout infrastructure, `APP` — checkout приложения, `DIGEST` — digest образа:

```bash
helm lint --strict charts/application \
  -f "$APP/helm/values.app.yaml" -f "$APP/helm/dev/values.yaml" \
  --set-string image.digest="$DIGEST" --set-string releaseId=check
helm template application charts/application \
  -f "$APP/helm/values.app.yaml" -f "$APP/helm/dev/values.yaml" \
  --set-string image.digest="$DIGEST" --set-string releaseId=check
```

TLS и pull Secrets передаются по именам. Внутренний HTTP-порт — 8080;
внешний доступ принадлежит Traefik. Админка обслуживает корень собственного домена.
Полный контракт: [доставка приложений](../../docs/application-delivery.md).
