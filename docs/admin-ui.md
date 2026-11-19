# Dev-развёртывание админки

Ingress: `dev.sellgar.io/admin`. Кластер — локальная VM `192.168.122.10`,
namespace — `sellgar-dev`, release — `admin-ui`. В dev используется одна реплика.

## Доставка

CI админки публикует проверенный образ и самостоятельный Helm-пакет
`ghcr.io/pyatakovvg/helm/sellgar-ui-admin-dev`. Пакет содержит общий chart,
image digest и общие/dev values из source commit образа. ConfigMap с `config.js`
остаётся в `helm/dev/values.yaml` админки, в инфраструктуру не копируется.

`environments/dev/services/admin-ui/application.yaml` — постоянное подключение
Argo CD к этому OCI repository. Версионный диапазон `>=0.0.0` выбирает новый
опубликованный dev-пакет. Automated sync, self-heal и pruning включены.
Обновление image/config не требует коммита в инфраструктурный Git или ручного restart.

Корневой Application `sellgar-dev` управляет самим подключением, а новые выпуски
админки доставляются через GHCR. Secret `argocd/sellgar-helm-ghcr` предоставляет
repo-server чтение приватных Helm-пакетов; пароль не хранится в Git.
Настройка выполняется `bootstrap/dev/configure-helm-repository.py` с использованием
существующего read credential `sellgar-dev/ghcr-pull`, только с разрешения владельца.

Полный контракт и порядок выпуска: [helm-delivery.md](helm-delivery.md).
Prod-кластер пока не подключён. Workflow админки умеет публиковать отдельный
prod-пакет только по ручному запуску из master с проверенным release-кандидатом.

## Проверки

```bash
kubectl -n argocd get application dev-admin-ui
kubectl -n sellgar-dev rollout status deployment/admin-ui --timeout=180s
kubectl -n sellgar-dev get deployment admin-ui -o jsonpath='{.spec.template.spec.containers[0].image}'
curl --resolve dev.sellgar.io:80:192.168.122.10 http://dev.sellgar.io/admin/
```

Новая публикация обнаруживается штатным refresh Argo CD. Успех CI означает
публикацию пакета; готовность пода подтверждается Sync/Health и rollout.
Для browser-проверки домен должен разрешаться в адрес VM.
Bootstrap и административный port-forward Argo CD описаны в
[../bootstrap/README.md](../bootstrap/README.md).
