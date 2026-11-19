# Dev-развёртывание витрины

Адрес — `http://dev.sellgar.io/`, namespace — `sellgar-dev`, release — `storefront`.
Админка использует отдельный ingress `/admin`; более длинный prefix сохраняет
приоритет над `/` витрины. TLS этим этапом не подключается.

## Источники

`environments/dev/services/storefront/application.yaml` фиксирует SHA общего
chart `charts/application`, SHA Helm values репозитория `sellgar.ui.desktop`
и digest образа из успешного GitHub CI. Commit образа и запуск CI указаны
в annotations. Продвижение версии повторяет [админку](admin-ui.md).

`helm/values.app.yaml` и `helm/dev/values.yaml` находятся в репозитории витрины.
ConfigMap монтирует `.env` в `/app/clients/desktop/.env`; Node.js читает его
перед запуском standalone Next.js. Образ одинаков для всех сред.
При изменении ConfigMap checksum общего chart запускает rolling update.

## Backend — отдельный этап

По решению пользователя сейчас развёртывается только фронтенд. В dev `.env`
`CLIENT_GATEWAY_URL` пуст, публичный origin — `http://dev.sellgar.io`.
Корневой URL и `/offers/*` возвращают HTTP 503 с сообщением о временной
недоступности. Существующие cookies сохраняются, новая сессия не создаётся.
Это ожидаемое состояние до подключения backend, а не проверка commerce flow.

`GET /healthz` отвечает JSON `{ "status": "ok" }` и используется probes.
Он подтверждает готовность Next.js сервера, без проверки сессии, каталога и корзины.

Следующим этапом нужно развернуть клиентский gateway с его зависимостями,
заполнить серверный `CLIENT_GATEWAY_URL` в Helm values витрины и опубликовать
существующие пути gateway `/v1`, socket gateway `/socket.io`. Включение TLS
потребуется для браузерных session-механизмов, которым нужен secure context.
Эти сервисы и маршруты текущим deployment не создаются.

## Проверки

```bash
kubectl -n argocd get application dev-storefront
kubectl -n sellgar-dev rollout status deployment/storefront --timeout=180s
curl http://dev.sellgar.io/healthz
curl -i http://dev.sellgar.io/
curl -I http://dev.sellgar.io/admin/
```

CI проверяет один образ с несколькими `.env`: рабочий SSR на изолированном
fixture backend, отсутствие private env в HTML и корректный 503 без backend.
Это проверка образа; реальные покупки до deployment backend не проверяются.
