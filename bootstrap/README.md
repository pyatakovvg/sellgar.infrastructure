# Первоначальная настройка GitOps

`argocd/` устанавливает официальный Argo CD 3.6.2 по зафиксированному commit;
образы также закреплены digest. Установка предназначена для текущего одного
узла K3s. Argo CD API/UI остаётся ClusterIP, внешний Ingress не создаётся.

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
Дочерние приложения задают конкретные SHA chart/values и digest образа.
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
