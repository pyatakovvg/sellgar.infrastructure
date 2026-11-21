# Dev-развёртывание админки

Ingress: `https://admin.dev.sellgar.ru/`. Кластер — локальная VM `192.168.122.10`,
namespace — `sellgar-dev`, Helm release — `admin-ui`. В dev одна реплика.

## Доставка

Push в `development` запускает `unit → build → publish → deploy`.
Миграционной и компонентной jobs нет. Unit/build/publish работают на GitHub-hosted
runners; deploy — на одном общем organization runner `sellgar-dev`.
Падение юнит-тестов блокирует сборку и все последующие этапы.

Приложение хранит `helm/values.app.yaml` и `helm/dev/values.yaml`, включая ConfigMap
с `config.js`. Общий chart принадлежит infrastructure. Runtime image закреплён digest;
`imagePullSecrets: ghcr-pull` разрешает Kubernetes читать приватный пакет
`ghcr.io/sellgar/sellgar.ui.admin`.

Helm выполняет upgrade, ждёт готовность и проверяет фактический digest. Argo CD
управляет платформой; Application админки удалён с orphan propagation, ресурсы сохранены.
Отдельный Helm OCI-пакет на выпуск не создаётся. Коммит в infrastructure и ручной
restart для нового образа не требуются.

Полный контракт: [application-delivery.md](application-delivery.md).
Production не развёрнут; ручной release требует отдельной готовой среды.

## Проверки

```bash
helm status admin-ui -n sellgar-dev
kubectl -n sellgar-dev rollout status deployment/admin-ui --timeout=180s
kubectl -n sellgar-dev get deployment admin-ui -o jsonpath='{.spec.template.spec.containers[0].image}'
curl --resolve admin.dev.sellgar.ru:443:192.168.122.10 https://admin.dev.sellgar.ru/healthz
```

Успех build/publish означает готовность образа, а не завершённую доставку.
Завершение подтверждают успешная deploy job, Helm status deployed и новый готовый pod.
