# Dev-развёртывание админки

Ingress: `dev.sellgar.io/admin`. Кластер — локальная VM `192.168.122.10`,
namespace — `sellgar-dev`, release — `admin-ui`.

## Источники

`environments/dev/services/admin-ui/application.yaml` закрепляет:

- SHA общего chart из `charts/application` инфраструктурного репозитория;
- SHA `helm/values.app.yaml` и `helm/dev/values.yaml` репозитория админки;
- `image.repository` и `image.digest` успешной CI-сборки;
- commit образа и ID запуска CI для проверки происхождения.

ConfigMap с `config.js` описывается в `helm/dev/values.yaml` админки.
Он не копируется в инфраструктуру. Values могут обновляться отдельно от образа:
UID/GID, ресурсы и настройки API не требуют пересборки JavaScript.

Корневой Application `sellgar-dev` следит за веткой `development` инфраструктуры.
Изменение dev Application в Git запускает sync `dev-admin-ui`; в нём включены
self-heal и pruning. Chart, values и образ выбираются по конкретным ревизиям.

## Обновление версии

После успешного CI админки перенести digest из Summary/`release-manifest`
в `spec.sources[0].helm.parameters` dev Application. При изменении Helm values
обновить `spec.sources[1].targetRevision`; при изменении общего chart —
`spec.sources[0].targetRevision`. Сохранить commit образа и ID CI в annotations.
После commit/push в `development` Argo CD применит desired state.

CI пока не изменяет инфраструктурный Git автоматически. Kubernetes credentials
в GitHub CI не передаются. Prod deployment этим этапом не подключается.

## Проверки

```bash
kubectl -n argocd get applications
kubectl -n sellgar-dev rollout status deployment/admin-ui --timeout=180s
kubectl -n sellgar-dev get pods,services,ingresses
curl --resolve dev.sellgar.io:80:192.168.122.10 http://dev.sellgar.io/admin/
```

Для браузера `dev.sellgar.io` должен разрешаться в адрес VM. Публичный DNS,
TLS и перенос gateway/CDN — отдельные настройки; сейчас dev ConfigMap сохраняет
локальные адреса этих сервисов. Готовность Nginx не означает проверенный вход
в ещё не развёрнутый backend.

Bootstrap и административный port-forward Argo CD описаны
в [../bootstrap/README.md](../bootstrap/README.md).
