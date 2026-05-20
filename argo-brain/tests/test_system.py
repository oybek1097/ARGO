"""Tests for the system & network built-in tools — spec section 4.4.

These tests rely only on the stdlib and avoid external network access:
DNS and port checks are performed against localhost.
"""

from __future__ import annotations

import os
import socket
import unittest

from argo_brain.tools.builtin.system import (
    DiskUsageTool,
    DNSLookupTool,
    EnvGetTool,
    HTTPStatusTool,
    PortCheckTool,
    SystemInfoTool,
    system_tools,
)

USER = "test-user"


def _free_port() -> int:
    """Finds a TCP port that is currently closed (bind then release)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


class DiskUsageToolTests(unittest.IsolatedAsyncioTestCase):
    async def test_disk_usage_root(self) -> None:
        result = await DiskUsageTool().run(USER, path="/")
        self.assertTrue(result.success)
        self.assertIn("Total:", result.content)
        self.assertGreater(result.metadata["total"], 0)

    async def test_disk_usage_invalid_path(self) -> None:
        result = await DiskUsageTool().run(USER, path="/no/such/path/xyz123")
        self.assertFalse(result.success)


class EnvGetToolTests(unittest.IsolatedAsyncioTestCase):
    async def test_env_get_value(self) -> None:
        os.environ["ARGO_TEST_VAR"] = "hello-world"
        try:
            result = await EnvGetTool().run(USER, name="ARGO_TEST_VAR")
        finally:
            del os.environ["ARGO_TEST_VAR"]
        self.assertTrue(result.success)
        self.assertIn("hello-world", result.content)
        self.assertFalse(result.metadata["redacted"])

    async def test_env_get_secret_redacted(self) -> None:
        os.environ["ARGO_TEST_API_KEY"] = "super-secret-value"
        try:
            result = await EnvGetTool().run(USER, name="ARGO_TEST_API_KEY")
        finally:
            del os.environ["ARGO_TEST_API_KEY"]
        self.assertTrue(result.success)
        self.assertNotIn("super-secret-value", result.content)
        self.assertIn("<redacted>", result.content)
        self.assertTrue(result.metadata["redacted"])

    async def test_env_get_token_redacted(self) -> None:
        os.environ["ARGO_TEST_TOKEN"] = "tok-12345"
        try:
            result = await EnvGetTool().run(USER, name="ARGO_TEST_TOKEN")
        finally:
            del os.environ["ARGO_TEST_TOKEN"]
        self.assertNotIn("tok-12345", result.content)

    async def test_env_get_missing(self) -> None:
        result = await EnvGetTool().run(USER, name="ARGO_DEFINITELY_NOT_SET_XYZ")
        self.assertFalse(result.success)


class DNSLookupToolTests(unittest.IsolatedAsyncioTestCase):
    async def test_dns_lookup_localhost(self) -> None:
        result = await DNSLookupTool().run(USER, hostname="localhost")
        self.assertTrue(result.success)
        self.assertTrue(result.metadata["addresses"])

    async def test_dns_lookup_invalid(self) -> None:
        result = await DNSLookupTool().run(
            USER, hostname="no-such-host.invalid.argo-test"
        )
        self.assertFalse(result.success)

    async def test_dns_lookup_empty(self) -> None:
        result = await DNSLookupTool().run(USER, hostname="")
        self.assertFalse(result.success)


class PortCheckToolTests(unittest.IsolatedAsyncioTestCase):
    async def test_port_check_closed(self) -> None:
        result = await PortCheckTool().run(
            USER, host="127.0.0.1", port=_free_port(), timeout=1.0
        )
        self.assertTrue(result.success)
        self.assertFalse(result.metadata["open"])

    async def test_port_check_open(self) -> None:
        # Open a listening socket and verify the tool detects it.
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        port = server.getsockname()[1]
        try:
            result = await PortCheckTool().run(
                USER, host="127.0.0.1", port=port, timeout=1.0
            )
        finally:
            server.close()
        self.assertTrue(result.success)
        self.assertTrue(result.metadata["open"])

    async def test_port_check_invalid_port(self) -> None:
        result = await PortCheckTool().run(USER, host="127.0.0.1", port=99999)
        self.assertFalse(result.success)


class SystemInfoToolTests(unittest.IsolatedAsyncioTestCase):
    async def test_system_info_contains_python(self) -> None:
        result = await SystemInfoTool().run(USER)
        self.assertTrue(result.success)
        self.assertIn("Python", result.content)

    async def test_system_info_cpu_count(self) -> None:
        result = await SystemInfoTool().run(USER)
        self.assertGreaterEqual(result.metadata["cpu_count"], 1)


class HTTPStatusToolTests(unittest.IsolatedAsyncioTestCase):
    async def test_http_status_invalid_scheme(self) -> None:
        result = await HTTPStatusTool().run(USER, url="ftp://example.com")
        self.assertFalse(result.success)

    async def test_http_status_empty(self) -> None:
        result = await HTTPStatusTool().run(USER, url="")
        self.assertFalse(result.success)

    async def test_http_status_unreachable(self) -> None:
        # An unroutable address should fail gracefully (no crash).
        result = await HTTPStatusTool().run(
            USER, url="http://127.0.0.1:1/", timeout=1.0
        )
        self.assertFalse(result.success)


class SystemToolsRegistrationTests(unittest.TestCase):
    def test_system_tools_count(self) -> None:
        self.assertEqual(len(system_tools()), 6)

    def test_system_tools_names(self) -> None:
        names = {t.name for t in system_tools()}
        self.assertEqual(
            names,
            {
                "disk_usage",
                "env_get",
                "dns_lookup",
                "port_check",
                "system_info",
                "http_status",
            },
        )


if __name__ == "__main__":
    unittest.main()
