import argparse
import copy
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import yaml


def merge_values(base, override):
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge_values(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def package_release(chart, service, destination, repository, commit, digest, environment, version, release_name,
                    migration_digest=None):
    if environment not in {"dev", "prod"}:
        raise ValueError("Only dev and prod release packages are supported")
    if not re.fullmatch(r"[a-z0-9-]+/[a-z0-9_.-]+", repository):
        raise ValueError("Invalid source repository")
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Source commit must be an immutable Git SHA")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise ValueError("Image digest must come from the verified image publication")
    if not re.fullmatch(r"0\.[1-9][0-9]*\.[1-9][0-9]*", version):
        raise ValueError("Package version must be 0.<workflow run ID>.<attempt>")
    if not re.fullmatch(r"[a-z][a-z0-9-]*", release_name):
        raise ValueError("Invalid Helm release name")

    values = {}
    for file in [service / "helm/values.app.yaml", service / f"helm/{environment}/values.yaml"]:
        loaded = yaml.safe_load(file.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError(f"Expected a values mapping: {file}")
        values = merge_values(values, loaded)
    values["image"] = {"repository": f"ghcr.io/{repository}", "digest": digest}
    migration = values.get("migration", {})
    if migration_digest:
        if not migration.get("enabled"):
            raise ValueError("A migration image requires migration.enabled")
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", migration_digest):
            raise ValueError("Migration digest must come from the verified image publication")
        migration["image"] = {"repository": f"ghcr.io/{repository}", "digest": migration_digest}
    elif migration.get("image", {}).get("repository"):
        raise ValueError("A separate migration image requires a verified migration digest")

    name = f"{repository.split('/')[1].replace('.', '-')}-{environment}"
    wrapper = destination / name
    wrapper.mkdir(parents=True)
    (wrapper / "templates").mkdir()
    (wrapper / "templates/NOTES.txt").write_text(
        "Managed by Argo CD.\nImage: {{ .Values.application.image.repository }}@{{ .Values.application.image.digest }}\n",
        encoding="utf-8",
    )
    shutil.copytree(chart, wrapper / "charts/application")
    common_chart = yaml.safe_load((chart / "Chart.yaml").read_text(encoding="utf-8"))
    metadata = {
        "apiVersion": "v2",
        "name": name,
        "type": "application",
        "version": version,
        "appVersion": commit,
        "annotations": {
            "org.opencontainers.image.source": f"https://github.com/{repository}",
            "org.opencontainers.image.revision": commit,
            "sellgar.io/image-digest": digest,
            "sellgar.io/environment": environment,
        },
        "dependencies": [{"name": "application", "version": common_chart["version"]}],
    }
    if migration_digest:
        metadata["annotations"]["sellgar.io/migration-image-digest"] = migration_digest
    (wrapper / "Chart.yaml").write_text(yaml.safe_dump(metadata, sort_keys=False), encoding="utf-8")
    (wrapper / "values.yaml").write_text(
        yaml.safe_dump({"application": values}, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    subprocess.run(["helm", "lint", "--strict", str(wrapper)], check=True)
    subprocess.run(
        ["helm", "template", release_name, str(wrapper), "--namespace", f"sellgar-{environment}"],
        check=True, stdout=subprocess.DEVNULL,
    )
    subprocess.run(["helm", "package", str(wrapper), "--destination", str(destination)], check=True)
    package = destination / f"{name}-{version}.tgz"
    return {"chart_package": str(package), "chart_name": name, "chart_version": version}


def main():
    parser = argparse.ArgumentParser(description="Package a verified image and its matching Helm configuration")
    for name in ["chart", "service", "destination"]:
        parser.add_argument(f"--{name}", type=Path, required=True)
    for name in ["repository", "commit", "digest", "environment", "version", "release-name"]:
        parser.add_argument(f"--{name}", required=True)
    parser.add_argument("--migration-digest")
    arguments = parser.parse_args()
    result = package_release(**vars(arguments))
    print(json.dumps(result))
    if output := os.environ.get("GITHUB_OUTPUT"):
        with open(output, "a", encoding="utf-8") as file:
            for key, value in result.items():
                file.write(f"{key}={value}\n")


if __name__ == "__main__":
    main()
