# Доставка приложений через Helm OCI

## Контракт

Инфраструктурный Git описывает кластер, общие компоненты и постоянное подключение
приложения к Argo CD. Новый выпуск сервиса не изменяет этот Git.

Сервис хранит `helm/values.app.yaml` и `helm/<dev|prod>/values.yaml`. После проверки
и публикации образа CI использует общий action `.github/actions/publish-helm`
этого репозитория, закреплённый caller по Git SHA. Action:

1. Получает values из того же source commit, из которого собран образ.
2. Включает общий chart `charts/application` в самостоятельный Helm-пакет.
3. Закрепляет проверенный image digest; применяет общие values и values среды.
4. Выполняет Helm lint и render, публикует пакет в GHCR.

Пакеты имеют отдельные OCI repositories для приложения и среды:
`ghcr.io/<owner>/helm/<repository-with-dashes>-<dev|prod>`.
Версия `0.<GitHub run ID>.<attempt>` неизменяема и упорядочена по запускам.
Позднее завершение старой dev-сборки не откатывает более новую опубликованную версию.
При откате публикуется новый пакет с ранее проверенным image digest.

Argo CD следит за semver-диапазоном пакетов своей среды и автоматически применяет
новую версию. ConfigMap и образ поступают из одного пакета. Непрошедшая CI-сборка
не публикует пакет и не меняет работающую конфигурацию.

Служебное имя дочернего chart остаётся `application`: selectors и имена существующих
Deployment/Service сохраняются при переходе с прежней multi-source Application.
Digest и ревизии отдельных выпусков больше не задаются в Application инфраструктуры.

## Dev и prod

Dev-пакет публикуется автоматически только после успешного push CI ветки
`development`. Ветка `release/*` создаёт проверенный кандидат; отдельная stage-среда
пока не развёрнута. Prod-пакет публикует только ручной workflow из `master`, после
проверки соответствия master выбранному кандидату. Используется тот же image digest,
повторной сборки приложения нет. Prod-кластер пока не развёрнут.

Успешная публикация пакета не означает успешный rollout: итог доставки проверяется
в Argo CD по Sync/Health и в Kubernetes по readiness/rollout.

## Доступ

CI выполняется на GitHub-hosted runner и использует `GITHUB_TOKEN` с `packages: write`
только для публикации артефактов своего сервиса. Kubeconfig и сетевой доступ к VM ему
не нужны. Все ссылки на credentials остаются ссылками на Kubernetes Secrets.
Значения Secrets не входят в Helm-пакет. Браузерный config.js содержит только публичные
параметры и, как и раньше, задаётся ConfigMap из values приложения.

Для приватных пакетов repo-server Argo CD необходим Helm OCI repository Secret
с `type: helm`, `enableOCI: 'true'`, `url: ghcr.io/<owner>/helm` и доступом на чтение.
Secret не хранится в Git. Одного `imagePullSecret` пода для скачивания chart недостаточно.

## Проверки

```bash
PATH=/path/to/helm:$PATH python3 -B -m unittest discover \
  -s .github/actions/publish-helm -p 'test_*.py'
```

Тест сравнивает полученные Kubernetes-ресурсы со старым способом render, включая
selectors, рекурсивное наложение values, замену списков и закрепление digest.

Штатные механизмы описаны в документации Argo CD:
[Helm OCI](https://argo-cd.readthedocs.io/en/stable/user-guide/helm/),
[отслеживание версий](https://argo-cd.readthedocs.io/en/stable/user-guide/tracking_strategies/).

## Подключённые приложения

Admin UI, витрина, Admin/Client/Socket gateways, Identity, Shop, Product, Store, Cart, File и Media используют общий action и отдельный Helm OCI-пакет среды. Dev Application каждого приложения отслеживает semver-диапазон; старые multi-source источники с image digest и source SHA удалены.
