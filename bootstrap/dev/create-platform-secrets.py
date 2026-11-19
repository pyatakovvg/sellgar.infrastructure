#!/usr/bin/env python3
"""Create missing development credentials in Kubernetes; never overwrite existing ones.

Usage: create-platform-secrets.py /path/to/kubectl --kubeconfig /path/to/kubeconfig
Credentials are generated in memory and sent on stdin, never written to Git or logs.
"""
import json
import secrets
import subprocess
import sys

kubectl = sys.argv[1:]
if not kubectl:
    raise SystemExit(__doc__)

namespace = "sellgar-dev"
credentials = {
    "socket-database": {"username": "socket_srv", "password": secrets.token_hex(32)},
    "socket-auth": {"ticket-secret": secrets.token_hex(48)},
    "admin-auth": {"fingerprint-secret": secrets.token_hex(48)},
    "minio-root": {"username": "sellgar-admin", "password": secrets.token_hex(32)},
}
for name, values in credentials.items():
    existing = subprocess.run(
        [*kubectl, "get", "secret", name, "-n", namespace, "--ignore-not-found", "-o", "name"],
        check=True, capture_output=True, text=True,
    )
    if existing.stdout.strip():
        print(f"Preserved Secret {namespace}/{name}")
        continue
    manifest = {
        "apiVersion": "v1", "kind": "Secret",
        "metadata": {"name": name, "namespace": namespace},
        "type": "kubernetes.io/basic-auth" if name in ("socket-database", "minio-root") else "Opaque",
        "stringData": values,
    }
    subprocess.run([*kubectl, "create", "-f", "-"], input=json.dumps(manifest), text=True, check=True)
