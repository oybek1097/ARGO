"""Tests for the multi-backend terminal subsystem (spec section 4.15)."""

from __future__ import annotations

import shutil
import sys
import unittest

from argo_brain.terminals import (
    CommandResult,
    DockerBackend,
    LocalBackend,
    SSHBackend,
    TerminalBackend,
    get_backend,
)


class LocalBackendTests(unittest.IsolatedAsyncioTestCase):
    """The local backend must actually run commands here."""

    async def test_echo_captures_stdout(self):
        backend = LocalBackend()
        result = await backend.run("echo hello-argo")
        self.assertIsInstance(result, CommandResult)
        self.assertIn("hello-argo", result.stdout)
        self.assertTrue(result.success)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.backend, "local")

    async def test_nonzero_exit_sets_success_false(self):
        backend = LocalBackend()
        # `exit 3` returns a non-zero code.
        result = await backend.run("exit 3")
        self.assertFalse(result.success)
        self.assertEqual(result.exit_code, 3)

    async def test_stderr_is_captured(self):
        backend = LocalBackend()
        result = await backend.run("echo oops 1>&2")
        self.assertIn("oops", result.stderr)

    async def test_timeout_handled_gracefully(self):
        backend = LocalBackend()
        # A sleep longer than the timeout must not raise.
        result = await backend.run("sleep 5", timeout=1)
        self.assertFalse(result.success)
        self.assertIn("timed out", result.stderr.lower())

    async def test_cwd_is_respected(self):
        backend = LocalBackend(cwd="/")
        result = await backend.run("pwd")
        self.assertTrue(result.success)
        self.assertEqual(result.stdout.strip(), "/")


class DockerBackendTests(unittest.IsolatedAsyncioTestCase):
    """The docker backend must degrade gracefully without raising."""

    async def test_run_never_raises_and_returns_result(self):
        backend = DockerBackend(image="alpine:latest")
        result = await backend.run("echo from-docker", timeout=10)
        self.assertIsInstance(result, CommandResult)
        self.assertEqual(result.backend, "docker")

    async def test_missing_cli_fails_cleanly(self):
        # Point at a binary that certainly does not exist.
        backend = DockerBackend(docker_path="docker-does-not-exist-xyz")
        result = await backend.run("echo hi")
        self.assertFalse(result.success)
        self.assertEqual(result.exit_code, -1)
        self.assertIn("not found", result.stderr.lower())

    async def test_real_docker_when_available(self):
        if shutil.which("docker") is None:
            self.skipTest("docker CLI not installed")
        backend = DockerBackend(image="alpine:latest")
        result = await backend.run("echo containerised", timeout=60)
        # Either it ran (success) or the daemon/image was unavailable; both
        # are acceptable as long as no exception escaped.
        self.assertIsInstance(result, CommandResult)


class SSHBackendTests(unittest.IsolatedAsyncioTestCase):
    """The ssh backend must degrade gracefully without raising."""

    async def test_run_never_raises_and_returns_result(self):
        backend = SSHBackend(host="invalid.host.invalid", user="nobody")
        result = await backend.run("echo hi", timeout=5)
        self.assertIsInstance(result, CommandResult)
        self.assertEqual(result.backend, "ssh")

    async def test_missing_cli_fails_cleanly(self):
        backend = SSHBackend(host="example.com", ssh_path="ssh-does-not-exist-xyz")
        result = await backend.run("echo hi")
        self.assertFalse(result.success)
        self.assertEqual(result.exit_code, -1)
        self.assertIn("not found", result.stderr.lower())

    async def test_invalid_host_fails_cleanly(self):
        if shutil.which("ssh") is None:
            self.skipTest("ssh CLI not installed")
        backend = SSHBackend(host="host.invalid", user="nobody")
        result = await backend.run("echo hi", timeout=10)
        # An unreachable host must produce a failed result, not an exception.
        self.assertFalse(result.success)


class GetBackendFactoryTests(unittest.TestCase):
    """The get_backend factory must map names to the right classes."""

    def test_local(self):
        self.assertIsInstance(get_backend("local"), LocalBackend)

    def test_docker(self):
        backend = get_backend("docker", image="ubuntu:22.04")
        self.assertIsInstance(backend, DockerBackend)
        self.assertEqual(backend.image, "ubuntu:22.04")

    def test_ssh(self):
        backend = get_backend("ssh", host="srv1", user="ops")
        self.assertIsInstance(backend, SSHBackend)
        self.assertEqual(backend.host, "srv1")
        self.assertEqual(backend.user, "ops")

    def test_name_is_case_insensitive(self):
        self.assertIsInstance(get_backend("LOCAL"), LocalBackend)

    def test_unknown_name_raises_value_error(self):
        with self.assertRaises(ValueError):
            get_backend("firecracker")

    def test_all_backends_are_terminal_backends(self):
        for name, kwargs in (
            ("local", {}),
            ("docker", {}),
            ("ssh", {"host": "h"}),
        ):
            self.assertIsInstance(get_backend(name, **kwargs), TerminalBackend)


if __name__ == "__main__":  # pragma: no cover
    unittest.main(verbosity=2)
