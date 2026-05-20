"""System & network built-in tools — spec section 4.4.

A pure-stdlib toolset covering local system inspection (disk, env, OS info)
and lightweight network probes (DNS, TCP port, HTTP status). No third-party
dependencies are used — see the taxonomy in spec section 4.4.
"""

from __future__ import annotations

import os
import platform
import shutil
import socket
import sys
import urllib.error
import urllib.request

from argo_brain.tools.base import Tool, ToolResult

# --- helpers ----------------------------------------------------------------

# Substrings that mark an environment variable as sensitive; their values are
# redacted before being returned (spec section 4.4 — no secret leakage).
_SECRET_MARKERS = ("KEY", "TOKEN", "SECRET", "PASSWORD")


def _is_secret_name(name: str) -> bool:
    """Returns True if the variable name looks like it holds a secret."""
    upper = name.upper()
    return any(marker in upper for marker in _SECRET_MARKERS)


def _human_bytes(n: int) -> str:
    """Formats a byte count into a human-readable string."""
    value = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if value < 1024.0 or unit == "PB":
            return f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{value:.1f} PB"


# --- tools ------------------------------------------------------------------


class DiskUsageTool(Tool):
    """Reports free/total disk space for a filesystem path."""

    name = "disk_usage"
    description = "Reports total, used and free disk space for a path."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Filesystem path, default '/'"}
        },
    }

    async def run(self, user_id: str, path: str = "/", **kwargs) -> ToolResult:
        try:
            usage = shutil.disk_usage(path)
        except OSError as exc:
            return ToolResult(content=f"Could not read disk usage: {exc}", success=False)
        content = (
            f"Path: {path}\n"
            f"Total: {_human_bytes(usage.total)}\n"
            f"Used: {_human_bytes(usage.used)}\n"
            f"Free: {_human_bytes(usage.free)}"
        )
        return ToolResult(
            content=content,
            metadata={
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
            },
        )


class EnvGetTool(Tool):
    """Gets the value of an environment variable.

    Values of variables whose name contains KEY/TOKEN/SECRET/PASSWORD are
    redacted so that secrets are never exposed (spec section 4.4).
    """

    name = "env_get"
    description = "Gets an environment variable's value (secret values are redacted)."
    parameters = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Environment variable name"}
        },
        "required": ["name"],
    }

    async def run(self, user_id: str, name: str = "", **kwargs) -> ToolResult:
        if not name:
            return ToolResult(content="No variable name provided.", success=False)
        if name not in os.environ:
            return ToolResult(content=f"Environment variable not set: {name}", success=False)
        if _is_secret_name(name):
            return ToolResult(
                content=f"{name}=<redacted>",
                metadata={"redacted": True},
            )
        return ToolResult(
            content=f"{name}={os.environ[name]}",
            metadata={"redacted": False},
        )


class DNSLookupTool(Tool):
    """Resolves a hostname to its IP addresses."""

    name = "dns_lookup"
    description = "Resolves a hostname to one or more IP addresses."
    parameters = {
        "type": "object",
        "properties": {
            "hostname": {"type": "string", "description": "Hostname to resolve"}
        },
        "required": ["hostname"],
    }

    async def run(self, user_id: str, hostname: str = "", **kwargs) -> ToolResult:
        if not hostname:
            return ToolResult(content="No hostname provided.", success=False)
        try:
            infos = socket.getaddrinfo(hostname, None)
        except socket.gaierror as exc:
            return ToolResult(content=f"Could not resolve {hostname}: {exc}", success=False)
        # De-duplicate addresses while preserving order.
        addresses: list[str] = []
        for info in infos:
            addr = info[4][0]
            if addr not in addresses:
                addresses.append(addr)
        return ToolResult(
            content=f"{hostname} -> {', '.join(addresses)}",
            metadata={"addresses": addresses},
        )


class PortCheckTool(Tool):
    """Checks whether a TCP host:port accepts connections."""

    name = "port_check"
    description = "Checks whether a TCP port on a host is open."
    parameters = {
        "type": "object",
        "properties": {
            "host": {"type": "string", "description": "Hostname or IP address"},
            "port": {"type": "integer", "description": "TCP port number"},
            "timeout": {"type": "number", "description": "Timeout in seconds, default 2.0"},
        },
        "required": ["host", "port"],
    }

    async def run(
        self,
        user_id: str,
        host: str = "",
        port: int = 0,
        timeout: float = 2.0,
        **kwargs,
    ) -> ToolResult:
        if not host:
            return ToolResult(content="No host provided.", success=False)
        try:
            port = int(port)
        except (TypeError, ValueError):
            return ToolResult(content=f"Invalid port: {port}", success=False)
        if not 0 < port < 65536:
            return ToolResult(content=f"Port out of range: {port}", success=False)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(float(timeout))
        try:
            sock.connect((host, port))
        except OSError as exc:
            return ToolResult(
                content=f"{host}:{port} is closed ({exc})",
                metadata={"open": False},
            )
        finally:
            sock.close()
        return ToolResult(
            content=f"{host}:{port} is open",
            metadata={"open": True},
        )


class SystemInfoTool(Tool):
    """Returns basic OS, platform and Python information."""

    name = "system_info"
    description = "Returns OS, platform, Python version and CPU count."
    parameters = {"type": "object", "properties": {}}

    async def run(self, user_id: str, **kwargs) -> ToolResult:
        cpu_count = os.cpu_count() or 1
        content = (
            f"OS: {platform.system()} {platform.release()}\n"
            f"Platform: {platform.platform()}\n"
            f"Machine: {platform.machine()}\n"
            f"Python: {platform.python_version()} ({sys.implementation.name})\n"
            f"CPU count: {cpu_count}"
        )
        return ToolResult(
            content=content,
            metadata={
                "os": platform.system(),
                "python_version": platform.python_version(),
                "cpu_count": cpu_count,
            },
        )


class HTTPStatusTool(Tool):
    """Performs an HTTP HEAD request and returns the status code."""

    name = "http_status"
    description = "Performs a HEAD request to a URL and returns the HTTP status code."
    parameters = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to check (http/https)"},
            "timeout": {"type": "number", "description": "Timeout in seconds, default 5.0"},
        },
        "required": ["url"],
    }

    async def run(
        self, user_id: str, url: str = "", timeout: float = 5.0, **kwargs
    ) -> ToolResult:
        if not url:
            return ToolResult(content="No URL provided.", success=False)
        if not url.startswith(("http://", "https://")):
            return ToolResult(content=f"Unsupported URL scheme: {url}", success=False)
        request = urllib.request.Request(url, method="HEAD")
        try:
            with urllib.request.urlopen(request, timeout=float(timeout)) as response:
                status = response.status
        except urllib.error.HTTPError as exc:
            # An HTTP error still carries a meaningful status code.
            return ToolResult(
                content=f"{url} -> HTTP {exc.code}",
                metadata={"status": exc.code},
            )
        except (urllib.error.URLError, OSError, ValueError) as exc:
            return ToolResult(content=f"Could not reach {url}: {exc}", success=False)
        return ToolResult(
            content=f"{url} -> HTTP {status}",
            metadata={"status": status},
        )


def system_tools() -> list[Tool]:
    """List of the system & network built-in tools (spec section 4.4)."""
    return [
        DiskUsageTool(),
        EnvGetTool(),
        DNSLookupTool(),
        PortCheckTool(),
        SystemInfoTool(),
        HTTPStatusTool(),
    ]
