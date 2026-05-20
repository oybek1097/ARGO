"""Hub & Marketplace tests — spec section 4.7 / Sprint 11.

Stdlib ``unittest`` coverage for ``argo_brain.hub``: the ``.argopkg`` package
format, HMAC package signing, the file-backed registry catalogue, and the
publish/install flow through ``HubClient``.
"""

import gzip
import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path

from argo_brain.hub import (
    ArgoPackage,
    HubClient,
    HubError,
    HubRegistry,
    Manifest,
    PackageError,
    RegistryError,
    Signature,
    SignatureError,
    TrustStore,
    build_skill_package,
    sign,
    verify,
)
from argo_brain.hub.package import KIND_PLUGIN, KIND_SKILL


SKILL_MD = "---\nname: deploy-k8s\n---\n# Deploy\nApply manifests.\n"


def _skill_pkg(name="deploy-k8s", version="1.0.0", author="argo-team",
               markdown=SKILL_MD):
    return build_skill_package(
        name=name,
        version=version,
        author=author,
        description="Deploy a service to Kubernetes",
        category="devops",
        triggers=["deploy", "k8s"],
        markdown=markdown,
    )


def _plugin_pkg(name="my-plugin", version="1.0.0", author="argo-team"):
    return ArgoPackage(
        manifest=Manifest(name=name, version=version, kind=KIND_PLUGIN,
                          author=author),
        files={"plugin.py": b"# plugin code\n"},
    )


# --------------------------------------------------------------------------
# package.py
# --------------------------------------------------------------------------
class TestPackage(unittest.TestCase):
    def test_build_skill_package_shape(self):
        pkg = _skill_pkg()
        self.assertEqual(pkg.manifest.kind, KIND_SKILL)
        self.assertEqual(pkg.manifest.name, "deploy-k8s")
        self.assertIn("deploy-k8s.md", pkg.files)
        self.assertEqual(pkg.files["deploy-k8s.md"], SKILL_MD.encode("utf-8"))

    def test_round_trip_to_and_from_bytes(self):
        pkg = _skill_pkg()
        restored = ArgoPackage.from_bytes(pkg.to_bytes())
        self.assertEqual(restored.manifest.name, "deploy-k8s")
        self.assertEqual(restored.manifest.version, "1.0.0")
        self.assertEqual(restored.manifest.ref, "deploy-k8s@1.0.0")
        self.assertEqual(restored.manifest.author, "argo-team")
        self.assertEqual(restored.manifest.triggers, ["deploy", "k8s"])
        self.assertEqual(restored.files["deploy-k8s.md"],
                         pkg.files["deploy-k8s.md"])

    def test_bytes_are_a_valid_targz_with_manifest(self):
        # The .argopkg is a plain tar.gz; manifest.json must be inside it.
        data = _skill_pkg().to_bytes()
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
            names = sorted(m.name for m in tar.getmembers())
            self.assertEqual(names, ["files/deploy-k8s.md", "manifest.json"])
            blob = tar.extractfile("manifest.json").read()
        manifest = json.loads(blob)
        self.assertEqual(manifest["name"], "deploy-k8s")

    def test_digest_is_sha256_hex(self):
        digest = _skill_pkg().digest
        self.assertEqual(len(digest), 64)
        int(digest, 16)  # raises ValueError if not hex

    def test_digest_is_stable_and_deterministic(self):
        # Identical inputs → identical content address across rebuilds.
        self.assertEqual(_skill_pkg().digest, _skill_pkg().digest)
        self.assertEqual(_skill_pkg().to_bytes(), _skill_pkg().to_bytes())

    def test_digest_changes_with_content(self):
        a = _skill_pkg()
        b = build_skill_package(name="deploy-k8s", version="1.0.0",
                                markdown="something else entirely")
        self.assertNotEqual(a.digest, b.digest)

    def test_manifest_validation(self):
        with self.assertRaises(PackageError):
            Manifest(name="", version="1.0.0")
        with self.assertRaises(PackageError):
            Manifest(name="x", version="")
        with self.assertRaises(PackageError):
            Manifest(name="x", version="1.0.0", kind="bogus")

    def test_manifest_from_dict_rejects_unknown_fields(self):
        with self.assertRaises(PackageError):
            Manifest.from_dict({"name": "x", "version": "1", "evil": True})

    def test_rejects_corrupt_archive(self):
        with self.assertRaises(PackageError):
            ArgoPackage.from_bytes(b"not a tar.gz at all")

    def test_rejects_tampered_archive(self):
        # Flip bytes in the middle of a real archive: gzip/tar decode fails.
        data = bytearray(_skill_pkg().to_bytes())
        for i in range(len(data) // 2, len(data) // 2 + 10):
            data[i] ^= 0xFF
        with self.assertRaises(PackageError):
            ArgoPackage.from_bytes(bytes(data))

    def test_rejects_archive_with_no_manifest(self):
        # A valid tar.gz that simply lacks manifest.json.
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            info = tarfile.TarInfo("files/x.md")
            blob = b"# orphan"
            info.size = len(blob)
            tar.addfile(info, io.BytesIO(blob))
        with self.assertRaises(PackageError):
            ArgoPackage.from_bytes(buf.getvalue())

    def test_rejects_unexpected_member(self):
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            for name, blob in (("manifest.json",
                                Manifest(name="x", version="1").to_json()
                                .encode()),
                               ("evil.sh", b"rm -rf /")):
                info = tarfile.TarInfo(name)
                info.size = len(blob)
                tar.addfile(info, io.BytesIO(blob))
        with self.assertRaises(PackageError):
            ArgoPackage.from_bytes(buf.getvalue())

    def test_rejects_newer_package_format(self):
        pkg = _skill_pkg()
        pkg.manifest.format = 999
        with self.assertRaises(PackageError):
            ArgoPackage.from_bytes(pkg.to_bytes())


# --------------------------------------------------------------------------
# signing.py
# --------------------------------------------------------------------------
class TestSigning(unittest.TestCase):
    def test_sign_then_verify_round_trip(self):
        data = b"package-bytes"
        s = sign(data, publisher="argo-team", key="secret")
        self.assertEqual(s.publisher, "argo-team")
        self.assertEqual(s.algorithm, "hmac-sha256")
        self.assertTrue(s.value)
        self.assertTrue(verify(data, s, key="secret"))

    def test_verify_rejects_tampered_payload(self):
        s = sign(b"original", publisher="argo-team", key="secret")
        self.assertFalse(verify(b"tampered", s, key="secret"))

    def test_verify_rejects_wrong_key(self):
        s = sign(b"data", publisher="argo-team", key="secret")
        self.assertFalse(verify(b"data", s, key="other-key"))

    def test_verify_rejects_unsupported_algorithm(self):
        s = Signature(publisher="p", algorithm="ed25519", value="abc")
        with self.assertRaises(SignatureError):
            verify(b"data", s, key="secret")

    def test_sign_requires_publisher_and_key(self):
        with self.assertRaises(SignatureError):
            sign(b"data", publisher="", key="secret")
        with self.assertRaises(SignatureError):
            sign(b"data", publisher="p", key="")

    def test_signature_serialisation_round_trip(self):
        s = sign(b"data", publisher="argo-team", key="secret")
        self.assertEqual(Signature.from_dict(s.to_dict()), s)

    def test_signature_from_dict_rejects_malformed(self):
        with self.assertRaises(SignatureError):
            Signature.from_dict({"publisher": "p"})

    def test_trust_store_add_and_lookup(self):
        store = TrustStore()
        self.assertFalse(store.trusts("argo-team"))
        store.add("argo-team", "secret")
        self.assertTrue(store.trusts("argo-team"))
        self.assertIn("argo-team", store.publishers())
        s = sign(b"data", publisher="argo-team", key="secret")
        self.assertTrue(store.verify(b"data", s))

    def test_trust_store_remove(self):
        store = TrustStore({"argo-team": "secret"})
        store.remove("argo-team")
        self.assertFalse(store.trusts("argo-team"))

    def test_trust_store_rejects_unknown_publisher(self):
        store = TrustStore()
        s = sign(b"data", publisher="stranger", key="secret")
        with self.assertRaises(SignatureError):
            store.verify(b"data", s)

    def test_trust_store_verify_fails_on_wrong_stored_key(self):
        store = TrustStore({"argo-team": "the-wrong-key"})
        s = sign(b"data", publisher="argo-team", key="real-key")
        self.assertFalse(store.verify(b"data", s))

    def test_trust_store_from_file(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "trust.json"
            path.write_text(json.dumps({"argo-team": "secret"}))
            store = TrustStore.from_file(path)
            self.assertTrue(store.trusts("argo-team"))
            # Missing file → empty store, not an error.
            empty = TrustStore.from_file(Path(td) / "missing.json")
            self.assertEqual(empty.publishers(), [])


# --------------------------------------------------------------------------
# registry.py
# --------------------------------------------------------------------------
class TestRegistry(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.registry = HubRegistry(self.root)
        self.registry.init()

    def tearDown(self):
        self._tmp.cleanup()

    def _publish(self, pkg, publisher="argo-team", key="secret"):
        s = sign(pkg.to_bytes(), publisher=publisher, key=key)
        return self.registry.publish(pkg, s)

    def test_init_creates_layout(self):
        self.assertTrue((self.root / "packages").is_dir())
        self.assertTrue((self.root / "index.json").is_file())

    def test_publish_writes_index_and_package_file(self):
        entry = self._publish(_skill_pkg())
        self.assertEqual(entry.ref, "deploy-k8s@1.0.0")
        # The catalogue file lists the published package.
        index = json.loads((self.root / "index.json").read_text())
        self.assertEqual(len(index["packages"]), 1)
        self.assertEqual(index["packages"][0]["name"], "deploy-k8s")
        self.assertEqual(index["packages"][0]["digest"], entry.digest)
        # The package bytes live beside the index.
        self.assertTrue(
            (self.root / "packages" / "deploy-k8s@1.0.0.argopkg").is_file())

    def test_fetch_returns_bytes_back(self):
        entry = self._publish(_skill_pkg())
        fetched_entry, pkg = self.registry.fetch("deploy-k8s")
        self.assertEqual(fetched_entry.digest, entry.digest)
        self.assertEqual(pkg.manifest.name, "deploy-k8s")
        self.assertEqual(pkg.files["deploy-k8s.md"], SKILL_MD.encode("utf-8"))
        self.assertEqual(pkg.digest, entry.digest)

    def test_versions_are_immutable(self):
        self._publish(_skill_pkg())
        with self.assertRaises(RegistryError):
            self._publish(_skill_pkg())

    def test_get_resolves_latest_and_specific_version(self):
        self._publish(_skill_pkg(version="1.0.0"))
        self._publish(_skill_pkg(version="2.0.0"))
        self.assertEqual(self.registry.get("deploy-k8s").version, "2.0.0")
        self.assertEqual(
            self.registry.get("deploy-k8s", "1.0.0").version, "1.0.0")

    def test_get_missing_package_or_version(self):
        with self.assertRaises(RegistryError):
            self.registry.get("nope")
        self._publish(_skill_pkg())
        with self.assertRaises(RegistryError):
            self.registry.get("deploy-k8s", "9.9.9")

    def test_search_finds_by_name_description_and_trigger(self):
        self._publish(_skill_pkg(name="deploy-k8s"))
        self._publish(build_skill_package(
            name="write-poem", version="1.0.0", markdown="# poem",
            triggers=["poem"]))
        self.assertEqual(len(self.registry.search()), 2)
        # description match
        self.assertEqual(
            [e.name for e in self.registry.search("kubernetes")],
            ["deploy-k8s"])
        # trigger match
        self.assertEqual(self.registry.search("poem")[0].name, "write-poem")

    def test_search_filters_by_kind(self):
        self._publish(_skill_pkg())
        self._publish(_plugin_pkg())
        self.assertEqual(
            [e.name for e in self.registry.search(kind="skill")],
            ["deploy-k8s"])
        self.assertEqual(
            [e.name for e in self.registry.search(kind="plugin")],
            ["my-plugin"])

    def test_fetch_bumps_download_counter(self):
        self._publish(_skill_pkg())
        self.registry.fetch("deploy-k8s")
        self.registry.fetch("deploy-k8s")
        self.assertEqual(self.registry.get("deploy-k8s").downloads, 2)

    def test_publish_requires_a_real_signature(self):
        empty = Signature(publisher="x", algorithm="hmac-sha256", value="")
        with self.assertRaises(RegistryError):
            self.registry.publish(_skill_pkg(), empty)

    def test_persists_across_registry_instances(self):
        self._publish(_skill_pkg())
        reopened = HubRegistry(self.root)
        self.assertEqual(len(reopened.all()), 1)
        self.assertEqual(reopened.all()[0].name, "deploy-k8s")

    def test_fetch_rejects_tampered_stored_package(self):
        # Corrupt the stored bytes after publish: digest no longer matches.
        self._publish(_skill_pkg())
        path = self.root / "packages" / "deploy-k8s@1.0.0.argopkg"
        good = ArgoPackage.from_bytes(path.read_bytes())
        tampered = ArgoPackage(
            manifest=good.manifest,
            files={"deploy-k8s.md": b"# malicious replacement"},
        )
        path.write_bytes(tampered.to_bytes())
        with self.assertRaises(PackageError):
            self.registry.fetch("deploy-k8s")


# --------------------------------------------------------------------------
# client.py
# --------------------------------------------------------------------------
class TestHubClient(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.registry = HubRegistry(root / "hub")
        self.registry.init()
        self.skills_dir = root / "skills"
        self.plugins_dir = root / "plugins"
        self.trust = TrustStore({"argo-team": "secret"})
        self.client = HubClient(
            self.registry,
            trust=self.trust,
            skills_dir=self.skills_dir,
            plugins_dir=self.plugins_dir,
        )

    def tearDown(self):
        self._tmp.cleanup()

    def test_full_publish_then_install_flow(self):
        entry = self.client.publish(_skill_pkg(), publisher="argo-team",
                                    key="secret")
        self.assertEqual(entry.ref, "deploy-k8s@1.0.0")
        result = self.client.install("deploy-k8s")
        self.assertTrue(result.signature_verified)
        self.assertEqual(result.entry.digest, entry.digest)
        installed = self.skills_dir / "deploy-k8s.md"
        self.assertEqual(result.paths, [installed])
        self.assertTrue(installed.is_file())
        self.assertIn("Apply manifests", installed.read_text())

    def test_install_routes_plugin_to_plugins_dir(self):
        self.client.publish(_plugin_pkg(), publisher="argo-team", key="secret")
        result = self.client.install("my-plugin")
        self.assertTrue((self.plugins_dir / "plugin.py").is_file())
        self.assertEqual(len(result.paths), 1)
        self.assertFalse((self.skills_dir / "plugin.py").exists())

    def test_install_refuses_untrusted_publisher(self):
        self.client.publish(_skill_pkg(), publisher="stranger", key="key")
        with self.assertRaises(HubError):
            self.client.install("deploy-k8s")
        # Refused before anything touches disk.
        self.assertFalse((self.skills_dir / "deploy-k8s.md").exists())

    def test_install_refuses_bad_signature(self):
        # Publisher is trusted, but the package was signed with a key the
        # trust store disagrees on — the signature must not verify.
        self.client.publish(_skill_pkg(), publisher="argo-team",
                            key="wrong-key")
        with self.assertRaises(HubError):
            self.client.install("deploy-k8s")
        self.assertFalse((self.skills_dir / "deploy-k8s.md").exists())

    def test_install_refuses_wrong_digest(self):
        # Publish normally, then swap the stored bytes so they no longer
        # hash to the catalogue digest. registry.fetch must reject it.
        self.client.publish(_skill_pkg(), publisher="argo-team", key="secret")
        pkg_path = (self.registry.packages_dir /
                    "deploy-k8s@1.0.0.argopkg")
        forged = build_skill_package(name="deploy-k8s", version="1.0.0",
                                     markdown="# forged payload")
        pkg_path.write_bytes(forged.to_bytes())
        with self.assertRaises(PackageError):
            self.client.install("deploy-k8s")
        self.assertFalse((self.skills_dir / "deploy-k8s.md").exists())

    def test_install_unverified_when_signature_not_required(self):
        self.client.publish(_skill_pkg(), publisher="stranger", key="key")
        result = self.client.install("deploy-k8s", require_signature=False)
        self.assertFalse(result.signature_verified)
        self.assertTrue((self.skills_dir / "deploy-k8s.md").is_file())

    def test_search_and_info(self):
        self.client.publish(_skill_pkg(), publisher="argo-team", key="secret")
        self.assertEqual(self.client.search("k8s")[0].name, "deploy-k8s")
        self.assertEqual(self.client.info("deploy-k8s").version, "1.0.0")

    def test_install_specific_version(self):
        self.client.publish(_skill_pkg(version="1.0.0"),
                            publisher="argo-team", key="secret")
        self.client.publish(_skill_pkg(version="2.0.0"),
                            publisher="argo-team", key="secret")
        result = self.client.install("deploy-k8s", version="1.0.0")
        self.assertEqual(result.entry.version, "1.0.0")

    def test_install_default_picks_latest_version(self):
        self.client.publish(_skill_pkg(version="1.0.0"),
                            publisher="argo-team", key="secret")
        self.client.publish(_skill_pkg(version="2.0.0"),
                            publisher="argo-team", key="secret")
        result = self.client.install("deploy-k8s")
        self.assertEqual(result.entry.version, "2.0.0")


if __name__ == "__main__":
    unittest.main()
