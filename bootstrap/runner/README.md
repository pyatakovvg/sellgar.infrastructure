# Shared delivery runner

One organization runner `sellgar-dev` serves the 12 approved application repositories
in `sellgar`. GitHub-hosted runners build images, publish them, and run unit/component
tests. Only migrate/deploy use the shared runner inside the dev VM.

Provision the official runner with [Ansible runners.yml](../../ansible/runners.yml).
The inventory has one account, `delivery-dev-runner`, and the playbook rejects pools
with more than two runners or duplicate environments. Register through the official
short-lived organization token, supplied through an ignored Vault file.
Do not create repository-scoped registrations for additional services.

The systemd service starts with the VM:

```bash
sudo systemctl status actions.runner.sellgar.sellgar-dev.service
sudo journalctl -u actions.runner.sellgar.sellgar-dev.service -n 30
```

The runner has no sudo or Docker access. Its namespace kubeconfig is copied by
Ansible from root-owned `/etc/sellgar/delivery/dev.kubeconfig` (0600) into the
runner home. The runner environment preserves upstream entries and sets the
dedicated KUBECONFIG and Node network-family selection timeout. TLS verification
remains enabled. Ansible preloads official kubectl v1.37.2 with SHA-256 into
the standard setup-kubectl tool cache. CI setup actions reuse it.

Product passed the complete shared-runner pipeline in
[run 44941272922, attempt 2](https://github.com/sellgar/sellgar.product.service/actions/runs/44941272922).
The legacy `sellgar-product-dev` registration, systemd service, Linux account and
installation directory have been removed. There is one runner in the VM.

GitHub Free access is limited to the 12 selected public application repositories.
All external contributor workflows require approval. Selected workflows restriction
requires Enterprise and is not used; a trusted repository administrator can change
workflow scheduling. The agreed policy and transition checks are in
[organization-transition.md](../../docs/organization-transition.md).

## Kubernetes access

`product-dev-rbac.yaml` binds the Kubernetes user `product-delivery-dev` to the
`sellgar-dev` namespace. Provision a client certificate for that user through
the standard Kubernetes CertificateSigningRequest API, with a defined expiry
and renewal date. Install the dedicated kubeconfig as
`~/.kube/config` of the runner user, mode 0600, using the VM endpoint and CA.
No runner credential belongs in the repository.

The installed dev certificate was issued through CSR
`product-delivery-dev-20261121` and expires on **19 February 2027, 16:49:53 UTC**.
Renew it before 12 February through the CSR API, replace the certificate in
the dedicated kubeconfig, and repeat the permission checks below. Renewal is
manual; no automatic certificate rotation is installed.

Apply the namespace Role/RoleBinding using an administrator, then verify with
the runner's kubeconfig:

```bash
kubectl auth can-i create jobs -n sellgar-dev
kubectl auth can-i create secrets -n sellgar-dev
kubectl auth can-i get deployments -n sellgar-prod
```

The first two must return yes, the last no. Helm stores release history in
namespace Secrets; this deployment principal is trusted for the whole namespace,
not isolated to Product by its name. Runtime containers have no API token.
The pipeline passes DB credentials to the migration container through existing
Secret references and does not download DB passwords to GitHub-hosted runners.

The namespace must already exist. Delivery does not provision databases, broker
users, registry pull credentials or production infrastructure. All runner API
operations are namespace-scoped; no cluster-wide permissions are needed.

## GitHub settings

Before enabling production, configure protected `master`/`development`, required
CI checks, and the `prod` environment (allowed branch master and reviewers).
Enable immutable releases before publishing candidates. Keep release/master
merges as merge commits: promotion verifies source ancestry and identical trees.
Back-merge creates a PR; review/merge remains explicit. Workflows created by
GITHUB_TOKEN can require approval to run checks.

A repository runner serves one repository. A shared pool across repositories
requires a GitHub organization. Use a separate production registration, label
`sellgar-prod`, user and kubeconfig when production is provisioned.

## First handover from Argo CD

Do this only after publishing the new shared chart/workflow and Product CI,
registering the runner, and removing Product from the root GitOps inventory.
Apply the same procedure separately to each remaining Argo-managed application.

1. Disable auto-sync of `argocd/dev-product-service` and wait for any active
   sync to finish. Record the running image, environment and readiness.
2. Remove any resources finalizer from this Application, then delete only the
   Application. Preserve the Deployment, Service, ConfigMap, database and Secrets.
   Removing a Git manifest is not proof that reconciliation stopped.
3. Bootstrap a Helm release with the CURRENT verified image, the new chart and
   Product values, `--set migration.enabled=false`, a unique `releaseId`,
   `--take-ownership --force-conflicts --wait` with Helm 4. The first flag adopts
   Helm ownership; the second resolves changed fields owned by the stopped Argo
   controller. Review the rendered diff before this one-time step.
   It introduces the versioned environment ConfigMap without replacing resources.
   Do not put either ownership flag in routine CI; do not use `--force-replace`.
4. Inspect `kubectl get ... -o json --show-managed-fields` for the adopted
   Deployment and Service. Equal values can retain shared ownership even with
   `--force-conflicts`. In the dev pilot, Argo still owned the unchanged image,
   so the first normal upgrade failed. After confirming the Application was gone,
   only the retired `argocd-controller` entries were removed with JSON Patch,
   guarded by a resourceVersion test. Server dry-run and before/after comparisons
   confirmed identical `spec`; Helm and Kubernetes controller entries remained.
   Do not clear all managedFields or add permanent force flags to delivery.
5. Check `helm status product-service -n sellgar-dev`, the running image and
   `/health`. Only then enable ordinary CI delivery.

Routine workflow preflight refuses an existing Deployment that has not been
adopted by the corresponding Helm release. It never silently takes ownership.

References: [official runner setup](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/add-runners),
[systemd service](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/configure-the-application),
[Kubernetes client certificates](https://kubernetes.io/docs/reference/access-authn-authz/certificate-signing-requests/),
[server-side field ownership and conflicts](https://kubernetes.io/docs/reference/using-api/server-side-apply/).
