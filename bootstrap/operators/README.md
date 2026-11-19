# Cluster operators

Install in order; wait for each deployment before proceeding:

1. `kubectl apply --server-side -k bootstrap/operators/cert-manager`
2. `kubectl -n cert-manager rollout status deployment/cert-manager-webhook`
3. `kubectl apply --server-side -k bootstrap/operators/postgresql`
4. `kubectl apply --server-side -k bootstrap/operators/rabbitmq`
5. Wait for `cnpg-system/cnpg-controller-manager` and
   `rabbitmq-system/rabbitmq-cluster-operator` to become Available.

Upstream release URLs and checksums are recorded in `releases.yaml`.
RabbitMQ operator requires cert-manager certificates for its admission webhook.
Platform application data is managed by the `dev-platform` Argo application;
operators are cluster bootstrap, not dependencies of an individual service.
