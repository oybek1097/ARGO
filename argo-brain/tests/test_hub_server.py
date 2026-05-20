"""Hub HTTP server, remote client and CLI tests — spec section 4.7 / Sprint 11."""

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from argo_brain.hub import (
    HubClient,
    HubRegistry,
    HubServer,
    RemoteRegistry,
    TrustStore,
    build_skill_package,
    sign,
)
from argo_brain.hub.cli import run as hub_cli
from argo_brain.hub.registry import RegistryError


def _skill(name="deploy-k8s", version="1.0.0"):
    return build_skill_package(
        name=name, version=version, author="argo-team",
        description="Deploy a service to Kubernetes",
        category="devops", triggers=["deploy", "k8s"],
        markdown="---\nname: deploy-k8s\n---\n# Deploy\nApply manifests.\n",
    )


class _ServerFixture(unittest.TestCase):
    """Spins up a HubServer on a background thread against a temp registry."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.registry = HubRegistry(self.root / "hub")
        self.registry.init()
        self.server = HubServer(self.registry, host="127.0.0.1", port=0)
        self.server.serve_in_thread()
        self.remote = RemoteRegistry(self.server.url)

    def tearDown(self):
        self.server.stop()
        self._tmp.cleanup()

    def _publish_local(self, pkg, publisher="argo-team", key="secret"):
        return self.registry.publish(pkg, sign(pkg.to_bytes(), publisher=publisher, key=key))


class TestHubServer(_ServerFixture):
    def test_health(self):
        self.assertTrue(self.remote.health())

    def test_index_and_search_over_http(self):
        self._publish_local(_skill())
        self.assertEqual(len(self.remote.all()), 1)
        hits = self.remote.search("kubernetes")
        self.assertEqual([e.name for e in hits], ["deploy-k8s"])

    def test_get_and_versions_over_http(self):
        self._publish_local(_skill(version="1.0.0"))
        self._publish_local(_skill(version="2.0.0"))
        self.assertEqual(self.remote.get("deploy-k8s").version, "2.0.0")
        self.assertEqual(self.remote.get("deploy-k8s", "1.0.0").version, "1.0.0")
        self.assertEqual(len(self.remote.versions("deploy-k8s")), 2)

    def test_get_missing_raises(self):
        with self.assertRaises(RegistryError):
            self.remote.get("nope")

    def test_fetch_downloads_package(self):
        self._publish_local(_skill())
        entry, package = self.remote.fetch("deploy-k8s")
        self.assertEqual(package.manifest.name, "deploy-k8s")
        self.assertEqual(package.digest, entry.digest)

    def test_publish_over_http(self):
        pkg = _skill()
        signature = sign(pkg.to_bytes(), publisher="argo-team", key="secret")
        entry = self.remote.publish(pkg, signature)
        self.assertEqual(entry.ref, "deploy-k8s@1.0.0")
        # The package really landed in the underlying registry.
        self.assertEqual(len(self.registry.all()), 1)

    def test_publish_rejects_immutable_version(self):
        pkg = _skill()
        sig = sign(pkg.to_bytes(), publisher="argo-team", key="secret")
        self.remote.publish(pkg, sig)
        with self.assertRaises(RegistryError):
            self.remote.publish(pkg, sig)


class TestRemoteWithClient(_ServerFixture):
    def test_client_installs_from_remote_hub(self):
        # Publish through the HTTP server, then install through it.
        client = HubClient(
            self.remote,
            trust=TrustStore({"argo-team": "secret"}),
            skills_dir=self.root / "skills",
            plugins_dir=self.root / "plugins",
        )
        client.publish(_skill(), publisher="argo-team", key="secret")
        result = client.install("deploy-k8s")
        self.assertTrue(result.signature_verified)
        self.assertTrue((self.root / "skills" / "deploy-k8s.md").is_file())

    def test_remote_install_rejects_bad_signature(self):
        client = HubClient(
            self.remote,
            trust=TrustStore({"argo-team": "secret"}),
            skills_dir=self.root / "skills",
            plugins_dir=self.root / "plugins",
        )
        client.publish(_skill(), publisher="argo-team", key="wrong-key")
        from argo_brain.hub import HubError
        with self.assertRaises(HubError):
            client.install("deploy-k8s")


class TestHubCLI(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.registry = self.root / "hub"
        self.trust = self.root / "trust.json"
        # A skill markdown file to publish.
        self.skill_md = self.root / "my-skill.md"
        self.skill_md.write_text(
            "---\nname: my-skill\ntrigger: foo, bar\ncategory: general\n"
            "description: A test skill\n---\n# My Skill\nDo the thing.\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self._tmp.cleanup()

    def _run(self, *args):
        """Run the hub CLI with the temp registry/trust; capture stdout."""
        argv = ["--registry", str(self.registry), "--trust", str(self.trust), *args]
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = hub_cli(argv)
        return code, buf.getvalue()

    def test_publish_search_install_round_trip(self):
        code, out = self._run(
            "publish", str(self.skill_md),
            "--name", "my-skill", "--publisher", "argo-team", "--key", "secret",
        )
        self.assertEqual(code, 0, out)
        self.assertIn("Published my-skill@1.0.0", out)

        code, out = self._run("search", "foo")
        self.assertEqual(code, 0)
        self.assertIn("my-skill", out)

        # Trust the publisher, then install.
        code, _ = self._run("trust", "add", "argo-team", "secret")
        self.assertEqual(code, 0)
        code, out = self._run("install", "my-skill")
        self.assertEqual(code, 0, out)
        self.assertIn("verified", out)

    def test_info_and_versions(self):
        self._run("publish", str(self.skill_md), "--name", "my-skill",
                  "--publisher", "argo-team", "--key", "secret")
        code, out = self._run("info", "my-skill")
        self.assertEqual(code, 0)
        self.assertIn("my-skill", out)
        code, out = self._run("versions", "my-skill")
        self.assertEqual(code, 0)
        self.assertIn("1.0.0", out)

    def test_search_empty_registry(self):
        code, out = self._run("search")
        self.assertEqual(code, 0)
        self.assertIn("No packages", out)

    def test_install_missing_package_errors(self):
        code, out = self._run("install", "ghost")
        self.assertEqual(code, 1)
        self.assertIn("error:", out)

    def test_trust_add_and_list(self):
        code, _ = self._run("trust", "add", "argo-team", "k1")
        self.assertEqual(code, 0)
        code, out = self._run("trust", "list")
        self.assertEqual(code, 0)
        self.assertIn("argo-team", out)

    def test_publish_md_requires_name(self):
        code, out = self._run("publish", str(self.skill_md),
                               "--publisher", "p", "--key", "k")
        self.assertEqual(code, 1)
        self.assertIn("--name is required", out)


if __name__ == "__main__":
    unittest.main()
