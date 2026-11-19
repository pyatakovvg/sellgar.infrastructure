# Первоначальная настройка GitOps

## Сеть локальной VM

На текущем хосте исходящий трафик проходит через VPN с MTU 1420. MTU 1500
в VM приводил к зависанию TLS при обращении к GitHub; снижение до 1380
восстановило HTTPS и git access из repo-server. Для этой VM используется
`local-vm/99-sellgar-mtu.yaml`, устанавливаемый в `/etc/netplan/` с режимом 0600.
После `netplan apply` и перезапуска K3s Flannel вычисляет MTU 1330.
Это настройка локальной VM, а не универсальное значение для production VPS.

## Argo CD

`argocd/` устанавливает официальный Argo CD 3.6.2 по зафиксированному commit;
образы также закреплены digest. Установка предназначена для текущего одного
узла K3s. Argo CD API/UI остаётся ClusterIP, внешний Ingress не создаётся.
Repo-server читает Helm values без submodules (`ARGOCD_GIT_MODULES_ENABLED=false`):
исходники вложенных библиотек собирает CI, для deployment они не нужны.

Сначала, с kubeconfig нужного кластера:

```bash
kubectl apply --server-side --field-manager=sellgar-bootstrap -k bootstrap/argocd
kubectl -n argocd rollout status statefulset/argocd-application-controller --timeout=180s
kubectl -n argocd rollout status deployment/argocd-repo-server --timeout=180s
kubectl -n argocd rollout status deployment/argocd-server --timeout=180s
```

После публикации `environments/dev/kustomization.yaml` и его ресурсов:

```bash
kubectl apply -k bootstrap/dev
kubectl -n argocd get applications
kubectl -n sellgar-dev get deployments,pods,services,ingresses
```

Корневой Application `sellgar-dev` читает desired state ветки `development`.
Дочерние приложения следят за версионными Helm OCI-пакетами своей среды. Digest образа и соответствующие values входят в пакет.
Для dev включена синхронизация после изменения desired state; bootstrap
не подключает prod. Chart приложения хранится в `charts/application`,
values и ConfigMaps админки — в её `helm/`.

Для доступа администратора к Argo CD используется отдельный localhost port-forward:

```bash
kubectl -n argocd port-forward service/argocd-server 8443:443
```

Первичный пароль администратора находится в Secret
`argocd-initial-admin-secret` namespace `argocd`; его содержимое не публикуется
и не сохраняется в этом репозитории. Изменение пароля и внешняя публикация UI
в bootstrap не выполняются.

Для Helm OCI включены штатные интервалы Argo CD: обычная сверка раз в 60 секунд (jitter до 15 секунд), hard reconciliation раз в 3 минуты и cache repo-server 60 секунд. Это позволяет обнаруживать новые версии без ручного refresh и коммитов инфраструктуры. После изменения этих startup-параметров перезапустить repo-server и application-controller; работающие приложения это не перезапускает.
