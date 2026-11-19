import argparse
import base64
import json
import subprocess


def main():
    parser = argparse.ArgumentParser(description="Reuse existing GHCR read credentials for Argo CD Helm OCI")
    parser.add_argument("kubectl")
    parser.add_argument("--kubeconfig", required=True)
    arguments = parser.parse_args()
    kubectl = [arguments.kubectl, "--kubeconfig", arguments.kubeconfig]

    source = json.loads(subprocess.check_output(
        kubectl + ["-n", "sellgar-dev", "get", "secret", "ghcr-pull", "-o", "json"]
    ))
    config = json.loads(base64.b64decode(source["data"][".dockerconfigjson"]))
    credential = config["auths"].get("ghcr.io") or config["auths"].get("https://ghcr.io")
    if credential is None:
        raise ValueError("The existing pull secret has no GHCR credentials")
    if "auth" in credential:
        username, password = base64.b64decode(credential["auth"]).decode().split(":", 1)
    else:
        username, password = credential["username"], credential["password"]

    secret = {
        "apiVersion": "v1", "kind": "Secret",
        "metadata": {
            "name": "sellgar-helm-ghcr", "namespace": "argocd",
            "labels": {"argocd.argoproj.io/secret-type": "repository"},
        },
        "type": "Opaque",
        "stringData": {
            "name": "sellgar-helm", "type": "helm", "enableOCI": "true",
            "url": "ghcr.io/pyatakovvg/helm", "username": username, "password": password,
        },
    }
    subprocess.run(
        kubectl + ["apply", "--server-side", "--field-manager=sellgar-helm-bootstrap", "-f", "-"],
        input=json.dumps(secret), text=True, check=True, stdout=subprocess.DEVNULL,
    )
    print("Argo CD Helm OCI repository configured using existing GHCR read credentials.")


if __name__ == "__main__":
    main()
