#!/usr/bin/env python3
"""Read REG.RU credentials interactively and create their Kubernetes Secret.

Credentials go directly to kubectl on stdin, never to files or command arguments.
An existing Secret is preserved; this command does not rotate credentials.
"""

import argparse
import getpass
import json
import subprocess
import sys
import warnings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kubectl")
    parser.add_argument("--kubeconfig", required=True)
    arguments = parser.parse_args()
    kubectl = [arguments.kubectl, "--kubeconfig", arguments.kubeconfig]
    secret_scope = ["-n", "cert-manager"]

    existing = subprocess.run(
        kubectl + secret_scope + ["get", "secret", "regru-api", "--ignore-not-found", "-o", "name"],
        capture_output=True, text=True,
    )
    if existing.returncode:
        print("Не удалось подключиться к Kubernetes. Данные не запрашивались.", file=sys.stderr)
        return 1
    if existing.stdout.strip():
        print("Secret cert-manager/regru-api уже существует и оставлен без изменений.")
        return 0
    if not sys.stdin.isatty():
        print("Запустите команду в своём интерактивном терминале.", file=sys.stderr)
        return 1

    username = input("Логин аккаунта REG.RU: ").strip()
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        password = getpass.getpass("Альтернативный пароль API REG.RU (ввод скрыт): ")
    if not username or not password:
        print("Логин и пароль обязательны. Secret не создан.", file=sys.stderr)
        return 1

    secret = {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {"name": "regru-api", "namespace": "cert-manager"},
        "type": "Opaque",
        "stringData": {"username": username, "password": password},
    }
    created = subprocess.run(
        kubectl + secret_scope + ["create", "-f", "-"],
        input=json.dumps(secret), capture_output=True, text=True,
    )
    if created.returncode:
        print("Не удалось создать Secret. Проверьте права доступа к Kubernetes.", file=sys.stderr)
        return 1
    print("Secret cert-manager/regru-api создан. Пароль не записывался в локальные файлы.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (EOFError, KeyboardInterrupt, getpass.GetPassWarning):
        print("\nВвод отменён. Secret не создан.", file=sys.stderr)
        raise SystemExit(1)
