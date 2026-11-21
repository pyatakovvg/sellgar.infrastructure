# Identity service: dev deployment

Identity follows the gateway deployment contract: service repository owns `code/`,
root Dockerfile, `.github/` CI and `helm/` values; this repository owns Argo CD
Application and PostgreSQL role/database. One replica, internal HTTP port 8080,
no public Ingress. All domain operations remain RabbitMQ commands.

## Data and secrets

`platform/postgresql.yaml` manages a non-superuser login `identity_srv` using the
`identity-database` basic-auth Secret. `platform/identity-database.yaml` creates
its separate `identity_srv` database; reclaim policy retains it. The PostgreSQL
operator reconciles role before database creation succeeds. App migration Job
uses this database owner, never the personal operator account or postgres.

Run `ansible-playbook -i inventory/dev.yml secrets.yml` from `ansible/` before synchronization. It creates
missing `identity-database` and `identity-auth`, preserving existing credentials.
The app receives database/broker passwords and three Identity keys from Secrets;
non-secret values are mounted as `/app/.env` from service-owned Helm ConfigMap.
Secret values do not appear in Git, image or ConfigMap.

This is a fresh database. The user explicitly requested importing only the base
administrator and its person profile from the local development database,
retaining UUID/password. Legacy password HMAC key was therefore copied into
`identity-auth` through the authorized Kubernetes client, not Git. Session and
fingerprint keys are newly generated; existing sessions/other data are not imported.
This one-time import is not a general data migration or a seed that CI repeats.

## Rollout

CI builds/tests Node 24 image, applies six migrations to empty isolated PostgreSQL,
repeats them without changes, checks guest session lifecycle through real RabbitMQ,
and verifies readiness drops on broker disconnection. Only then publishes GHCR.
Application pins successful CI source commit, image digest and shared chart revision.
Migration Sync hook finishes before new Deployment starts. TypeORM synchronize is
never used. `/health` checks command-consumer connection and a PostgreSQL query.
Readiness routes away from disconnected instances; TCP liveness checks the process.

Verify `dev-platform` and `dev-identity-service` Synced/Healthy, migration history,
Deployment 1/1, and guest initialize/current/logout through Client gateway. Admin
credential compatibility is confirmed by matching imported hash and HMAC key;
no cleartext password is exported. Product/Store/Cart services are separate stages;
Identity alone does not make storefront catalog/cart available.

Prod values exist in the service, but no prod Identity deployment is configured.
