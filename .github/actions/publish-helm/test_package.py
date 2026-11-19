import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

from package import package_release


CHART = Path(__file__).resolve().parents[3] / "charts/application"
DIGEST = "sha256:" + "1" * 64


class HelmReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.service = self.directory / "service"
        (self.service / "helm/dev").mkdir(parents=True)
        self.common = {
            "image": {"repository": "ghcr.io/example/unverified", "digest": "latest"},
            "ingress": {"enabled": True, "className": "traefik", "path": "/admin"},
            "env": {"PORT": "8080"},
            "configmaps": [{"nameOverride": "obsolete-config", "enabled": True, "filename": "config.js", "data": "old"}],
        }
        self.environment = {
            "replicas": 1,
            "ingress": {"host": "dev.sellgar.io"},
            "env": {"FEATURE": "dev"},
            "configmaps": [{"nameOverride": "admin-ui-config", "enabled": True, "filename": "config.js", "data": "window.env = {};"}],
        }
        (self.service / "helm/values.app.yaml").write_text(yaml.safe_dump(self.common))
        (self.service / "helm/dev/values.yaml").write_text(yaml.safe_dump(self.environment))
        self.arguments = {
            "chart": CHART,
            "service": self.service,
            "destination": self.directory / "release",
            "repository": "example/admin-ui",
            "commit": "a" * 40,
            "digest": DIGEST,
            "environment": "dev",
            "version": "0.123.1",
            "release_name": "admin-ui",
        }

    def test_package_preserves_existing_resources_and_binds_values_to_verified_image(self):
        release = package_release(**self.arguments)
        rendered = subprocess.check_output([
            "helm", "template", "admin-ui", release["chart_package"], "--namespace", "sellgar-dev"
        ], text=True)
        baseline = subprocess.check_output([
            "helm", "template", "admin-ui", str(CHART), "--namespace", "sellgar-dev",
            "-f", str(self.service / "helm/values.app.yaml"),
            "-f", str(self.service / "helm/dev/values.yaml"),
            "--set-string", "image.repository=ghcr.io/example/admin-ui",
            "--set-string", f"image.digest={DIGEST}",
        ], text=True)
        resources = list(yaml.safe_load_all(rendered))
        self.assertEqual(resources, list(yaml.safe_load_all(baseline)))
        deployment = next(resource for resource in resources if resource["kind"] == "Deployment")
        self.assertEqual(deployment["spec"]["selector"]["matchLabels"], {
            "app.kubernetes.io/name": "application", "app.kubernetes.io/instance": "admin-ui"
        })
        configmaps = [resource["metadata"]["name"] for resource in resources if resource["kind"] == "ConfigMap"]
        self.assertEqual(configmaps, ["admin-ui-config"])
        metadata = yaml.safe_load(subprocess.check_output(["helm", "show", "chart", release["chart_package"]], text=True))
        self.assertEqual(metadata["appVersion"], self.arguments["commit"])
        self.assertEqual(metadata["annotations"]["sellgar.io/image-digest"], DIGEST)

    def test_rejects_mutable_or_unrelated_release_identifiers(self):
        for field, value in [
            ("digest", "latest"), ("commit", "development"), ("environment", "other"),
            ("repository", "../other"), ("version", "0.123.0"), ("release_name", "../../other"),
        ]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                package_release(**dict(self.arguments, **{field: value}))
        self.assertFalse(self.arguments["destination"].exists())

    def test_missing_environment_values_cannot_fall_back_to_another_environment(self):
        with self.assertRaises(FileNotFoundError):
            package_release(**dict(self.arguments, environment="prod"))
        self.assertFalse(self.arguments["destination"].exists())


if __name__ == "__main__":
    unittest.main()
