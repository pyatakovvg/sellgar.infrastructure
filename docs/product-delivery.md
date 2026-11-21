# Product: CI-driven delivery

This replaces delivery for Product only. Other applications keep their pinned
Argo CD/Helm OCI mechanism and `.github/actions/publish-helm` remains for them.

## Dev pilot, 21 November 2026

The official repository runner `sellgar-product-dev` is installed on the dev VM
as the unprivileged `product-runner` systemd service. Its Kubernetes identity is
`product-delivery-dev`, scoped to `sellgar-dev`; access to production Deployments
was denied in the permission check. Setup, maintenance and certificate expiry
are recorded in [the runner guide](../bootstrap/runner/README.md).

The live `argocd/dev-product-service` Application was removed with workloads
preserved. Helm adopted Product using its previously running image and unchanged
environment; `/health` stayed successful. The one-time Helm 4 handover used
`--take-ownership --force-conflicts`. Equal values still shared Argo ownership,
which blocked the first normal image update. Retired `argocd-controller`
managedFields entries were then removed from the adopted Deployment/Service;
their specs were verified unchanged. Routine delivery uses no ownership flags.
Other Argo Applications remain in place.

Failure checks: a temporary migration-shaped Job exited with code 7 and failed
the completion wait; it used no DB/broker credentials and was removed. In the
first actual Actions attempt, setup-helm failed before Job creation and deploy
was skipped. This verifies the workflow dependency gate, not a failed schema
migration against the dev database. No database reversal was performed.

[Run 44917345949](https://github.com/pyatakovvg/sellgar.product.service/actions/runs/44917345949)
completed successfully after runner setup and handover. Its migration Job
completed and reported no pending migrations; deploy used the verified application
digest `sha256:1829e303ab058e16e5afbb9565993ff0bea2479d36aa0ffbd141793abe2c367f`
for source `717a6c6eb1869a144234831288b72e07a00348b7`. Helm revision 4 was deployed,
the new pod became ready, and the workflow's digest/HTTP health checks passed.

[Fresh push run 44930076889](https://github.com/pyatakovvg/sellgar.product.service/actions/runs/44930076889)
then completed all five jobs without manual retries in 4m 10s. Source
`5c334601f9fd9c0a22acbcf752ff0f601aabfa2d` was deployed through Helm revision 5.

JavaScript actions in this Product pipeline declare Node 24. Delivery v0.5.2
updates setup-kubectl to official v5.2.0, pinned at
`bda439f5f36b99b262ebdcd3613869bddb064c8e`, replacing the v4 action whose manifest
still declared Node 20. Checkout, Helm, artifact upload/download and registry
login manifests were checked at their pinned commits and already declare Node 24.

## Ownership and files

- Product owns Dockerfile, application/migration images, Jest tests and `helm/`
  values. No environment or secret values are built into the images.
- Infrastructure owns `charts/application` and the reusable workflows
  `.github/workflows/build-service.yml` and `.github/workflows/deliver-service.yml`.
- Helm owns Product Deployment, Service and application ConfigMaps after handover.
  Argo continues managing the platform and other applications.
- Kubernetes Secrets own DB, broker and image-pull credentials. The runner is a
  trusted deployment principal for the target namespace.

There is no per-release infrastructure commit, generated wrapper chart, Python
release/packaging script, custom composite delivery action, ARC controller or
GitHub App in this Product path.

## Sequence

```text
development: build → publish → delivery/[test | migrate] → delivery/deploy
release/*:   build → publish candidate → tests
master:      manual candidate tag → validate → delivery/[test | migrate] → delivery/deploy → back-merge PR
PR:          build → tests
```

Product `ci.yml` handles development pushes only. `checks.yml` handles PRs and
release pushes; its jobs are not part of the development graph. Both reuse the
same build/publication workflow rather than maintaining two build definitions.
The development graph has exactly five executable jobs: build, publish, test,
migrate, deploy. No PR/release-only test job is conditionally skipped in it.

Build validates Helm for dev and prod and builds both images. Publication loads
the exact image IDs exported by build. In delivery, component tests and migration
run as independent parallel jobs. Tests run on GitHub-hosted runners with an
isolated PostgreSQL, while migration runs against the target environment database.
Deploy requires both jobs to succeed. Migration runs after publication so
Kubernetes can pull the migration image from the registry. PR tests follow build
without publication or access to the environment. Release candidates are eligible
for promotion only once the entire original CI run, including tests, succeeds.
Candidate GitHub Releases attach `release.json` containing application/migration
digests, source revision, chart revision and successful build run. Production
requires a published immutable release, verifies source ancestry and identical
master tree, checks the original CI result and both OCI image labels. It does
not rebuild the images. Stage is optional and not provisioned here.

The shared chart is checked out by its recorded commit; values by the exact
application source commit. The workflow calls and chart checkout select the
infrastructure release `delivery-v0.5.2`. Publish that immutable GitHub Release/tag
before Product. Never move it; changes to the shared pipeline/chart get a new version.

## Migration and configuration

`workload: migration` renders only a Job and its environment ConfigMap. It does
not render a Deployment, Service, Ingress or application ConfigMap. The Job has
backoff 0, a 600-second deadline and 24-hour TTL in Product values. It receives
the existing DB Secret refs and executes the migration image's CMD. The workflow
waits for completion and prints logs even on failure. A failed Job or test cannot reach
deploy; the bounded wait can report failure after its timeout rather than
immediately. No additional background watchers or polling scripts are used.

The Job's `.env` is `product-service-migration-env`. Application `.env` is an
immutable `product-service-env-<run>-<attempt>` ConfigMap. A failed/cancelled
migration therefore cannot change the environment of an existing application.
The old app ConfigMaps have `helm.sh/resource-policy: keep`, so still-running
pods can restart with their original config after a failed rollout. Cleanup of
old ConfigMaps is deliberate operator maintenance after confirming that no
remaining pod/release uses them; there is no automatic cleanup script.

Application deployment is a normal `helm upgrade --install --wait`, followed by
image digest and HTTP `/health` verification through its ClusterIP. Product health
checks PostgreSQL and both RabbitMQ consumers. The process uses port 8080 and
RollingUpdate with maxUnavailable 0/maxSurge 1. HTTP readiness does not gate
RabbitMQ delivery and is not a zero-message-loss guarantee.

## Cancellation, retry and failure

The reusable workflow serializes the whole delivery per repository/environment,
without cancelling an active run. Newer queued GitHub runs may replace older
pending runs; this is not a FIFO promise. The workflow rejects a superseded
branch revision before migration and again before deployment.

Cancel does not delete an executing DB Job. Its Kubernetes deadline remains
active. The next run refuses to replace a Job that has no terminal condition.
After completion, retry uses the migration journal and the same verified image.
A pending Helm operation also blocks the next run; inspect the cluster and
release status before intervention. Do not delete release metadata blindly.

If tests fail, deployment is blocked; a successful parallel migration remains
applied. No database reversal is attempted.
If migration fails, inspect its logs and schema/journal, fix the cause, and run
the corrected forward release. Application deployment is not started.
If deployment fails, inspect `helm status`, Deployment/Pod events and the running
revision; the previous available pod is retained while the new pod is unready.
A later corrected forward upgrade can resume delivery. No migration reverse,
automatic database downgrade or migration rollback workflow is implemented.

## Enabling the pilot

1. Publish the infrastructure workflow/chart as immutable release/tag
   `delivery-v0.5.2`, then publish Product. Its workflow calls and chart checkout
   already select that version. No other application's delivery reference changes.
2. Configure the official runner and scoped Kubernetes credential as described
   in `bootstrap/runner/README.md`.
3. Protect branches and configure environment gates/immutable releases. Product
   release branches merge into master with merge commits. Back-merge remains
   an explicitly reviewed PR after a successful deployment.
4. Perform the documented Argo-to-Helm handover without deleting workloads/data.
   Root GitOps inventory no longer contains Product. Inventory removal alone
   does not remove the live Argo Application; the root has no automated prune.
5. Run a real development CI and verify both private-runner jobs and their logs.

`prod` values describe a separate namespace, not a deployed production cluster.
Provision its runner, platform, Secrets and approvals before pressing the prod
button. PostgreSQL backups/recovery and fresh-VPS provisioning are prerequisites
to production operation and are not claimed complete by this pipeline rewrite.
