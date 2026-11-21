# Первоначальная настройка GitOps

Основной способ установки — [Ansible bootstrap](../ansible/README.md).
Ручные команды ниже оставлены для диагностики отдельных компонентов.
Python-обёртки создания Secrets, registry access и media bootstrap удалены.

HTTPS для двух dev-доменов описан в [dev HTTPS](../docs/dev-https.md).
`traefik/` содержит HelmChartConfig HTTP → HTTPS redirect для установленного в K3s
Traefik. Применять его после готовности публичного сертификата и HTTPS Ingress.

## Сеть локальной VM

На текущем хосте исходящий трафик проходит через VPN с MTU 1420. MTU 1500
в VM приводил к зависанию TLS при обращении к GitHub; снижение до 1380
восстановило HTTPS и git access из repo-server. Для этой VM используется
`local-vm/99-sellgar-mtu.yaml`, устанавливаемый в `/etc/netplan/` с режимом 0600.
После `netplan apply` и перезапуска K3s Flannel вычисляет MTU 1330.
Это настройка локальной VM, а не универсальное значение для production VPS.

## Постоянные туннели dev-среды

Все локальные подключения входят в пользовательскую группу systemd
`local-vm/sellgar-dev-tunnels.target`. Они работают независимо от watcher,
терминала и агентской сессии. Каждый туннель — отдельная служба:

| Служба | Адрес на хосте | Service в `sellgar-dev` |
| --- | --- | --- |
| `sellgar-postgresql-tunnel` | `127.0.0.1:15432` | `postgresql-rw:5432` |
| `sellgar-rabbitmq-ui-tunnel` | `http://127.0.0.1:15674` | `rabbitmq:15672` |
| `sellgar-admin-gateway-tunnel` | `http://127.0.0.1:4020` | `admin-gateway:8080` |
| `sellgar-client-gateway-tunnel` | `http://127.0.0.1:4030` | `client-gateway:8080` |

Туннели слушают только loopback. При обрыве соединения, перезапуске pod или
недоступности VM процесс перезапускается через 5 секунд и выбирает актуальный pod.
Пока VM выключена, службы повторяют подключение; саму VM они не запускают.
Уже оборванное JDBC-соединение нужно подключить повторно. Остановка watcher
не должна останавливать эти службы. Временные SSH/port-forward процессы
на перечисленных портах не нужны.

Установка из корня инфраструктурного репозитория:

```bash
mkdir -p "$HOME/.config/systemd/user"
install -m644 bootstrap/local-vm/sellgar-*.service \
  bootstrap/local-vm/sellgar-dev-tunnels.target "$HOME/.config/systemd/user/"
systemctl --user daemon-reload
systemctl --user enable --now sellgar-dev-tunnels.target
loginctl enable-linger "$USER"
```

Linger запускает пользовательский systemd при загрузке Ubuntu и сохраняет
работу служб после выхода из сессии. Службы используют существующий kubeconfig
из `~/.local/share/sellgar/vm/sellgar-k3s/`; credentials в unit не записываются.

Проверка и управление группой; отдельную службу можно проверить и перезапустить
по её имени без остановки остальных:

```bash
systemctl --user status sellgar-dev-tunnels.target 'sellgar-*-tunnel.service'
journalctl --user -u sellgar-client-gateway-tunnel.service -n 30
systemctl --user restart sellgar-client-gateway-tunnel.service
systemctl --user stop sellgar-dev-tunnels.target
systemctl --user start sellgar-dev-tunnels.target
```

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
