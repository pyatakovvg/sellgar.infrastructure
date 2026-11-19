# Shop service: dev deployment

The Shop repository owns `code/`, root Dockerfile, `.github/` CI and `helm/`
values. This repository owns Argo CD Application and PostgreSQL role/database.
Working branch is development. One replica, internal HTTP 8080, no public Ingress;
HTTP administration stays in the existing Admin gateway `/v2/shops` branch.

## Database and credentials

CloudNativePG manages the non-superuser login `shop_srv` from the basic-auth
Secret `shop-database` and its separate database `shop_srv` through the Database
resource. Reclaim policy is retain. Bootstrap creates only missing Secrets;
existing Identity, Socket and platform credentials are preserved.

This is a fresh Shop database. No local shops or other application data are
imported. The app's migration Sync Job runs all nine migrations before a new
Deployment starts; TypeORM synchronize remains disabled. ConfigMap `.env` is
mounted at `/app/.env`. Database and RabbitMQ credentials are Secret env refs;
secret values are absent from Git, ConfigMaps and images.

## Image and readiness

GitHub recursively checks out the existing @sellgar/outbox submodule, builds it
with Shop, runs unit tests and an isolated production-image smoke before GHCR
publication. The runtime image contains the library's package.json/dist alongside
Shop and production node_modules. Outbox is a library in the Shop process.

Smoke uses empty temporary PostgreSQL/RabbitMQ, applies migrations twice,
checks RMQ create/read/update/search, stale version 409, validation 400 and actual
shop.created/shop.updated publication in aggregate version order. Runtime is
non-root with read-only filesystem and mounted .env. A broker disconnect makes
`/health` return 503; the endpoint checks both command-consumer state and DB.

The shared chart uses RollingUpdate maxSurge 1/maxUnavailable 0, readiness and
startup probes, and shutdown grace. This deployment alone does not claim verified
loss-free draining of every in-flight RMQ command during rollout.

## Acceptance

Check `dev-platform` and `dev-shop-service` Synced/Healthy, all nine rows in the
`migrations` history, Deployment 1/1 and Service port 8080. Open Shops in the
already authenticated dev admin browser, create a clearly labelled development
shop and verify it appears in the list and opens again from the backend.
Personal PostgreSQL account grants were left unchanged at the user's request;
application credentials remain separate. Prod is not deployed.
