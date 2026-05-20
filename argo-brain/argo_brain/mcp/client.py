"""MCP client — spec section 4.10.

Connects to an external MCP server launched as a subprocess and speaks
JSON-RPC 2.0 over stdio. Per the spec, the stdio transport is
**newline-delimited JSON** (one message per line), not Content-Length framed.

Dependency-free: uses `asyncio` subprocess management from the stdlib.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os

from argo_brain import __version__

log = logging.getLogger("argo_brain.mcp")

_PROTOCOL_VERSION = "2024-11-05"
_REQUEST_TIMEOUT = 30


class MCPClient:
    """A client connection to one external MCP server (stdio transport)."""

    def __init__(self, name: str, command: str, args: list[str] | None = None,
                 cwd: str | None = None, env: dict | None = None) -> None:
        self.name = name
        self._command = command
        self._args = args or []
        self._cwd = cwd
        self._env = env
        self._proc: asyncio.subprocess.Process | None = None
        self._reader_task: asyncio.Task | None = None
        self._pending: dict[int, asyncio.Future] = {}
        self._next_id = 0
        self._tools: list[dict] = []

    @property
    def tools(self) -> list[dict]:
        """Tool definitions advertised by the server (after `start()`)."""
        return self._tools

    # --- lifecycle ----------------------------------------------------------

    async def start(self) -> None:
        """Launches the server, performs the handshake and loads its tools."""
        self._proc = await asyncio.create_subprocess_exec(
            self._command, *self._args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self._cwd,
            env={**os.environ, **(self._env or {})},
        )
        self._reader_task = asyncio.create_task(self._read_loop())

        await self._request("initialize", {
            "protocolVersion": _PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "argo-brain", "version": __version__},
        })
        await self._notify("notifications/initialized", {})

        result = await self._request("tools/list", {})
        self._tools = result.get("tools", [])
        log.info("MCP server '%s' connected: %d tool(s)", self.name, len(self._tools))

    async def stop(self) -> None:
        """Terminates the server subprocess and stops the reader."""
        if self._reader_task is not None:
            self._reader_task.cancel()
        if self._proc is not None and self._proc.returncode is None:
            self._proc.terminate()
            try:
                await asyncio.wait_for(self._proc.wait(), timeout=5)
            except asyncio.TimeoutError:
                self._proc.kill()

    # --- JSON-RPC plumbing --------------------------------------------------

    async def _read_loop(self) -> None:
        """Reads newline-delimited JSON messages and resolves pending calls."""
        assert self._proc is not None and self._proc.stdout is not None
        while True:
            line = await self._proc.stdout.readline()
            if not line:
                break  # server closed stdout
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            msg_id = msg.get("id")
            if msg_id is None:
                continue  # a notification from the server — ignored here
            future = self._pending.pop(msg_id, None)
            if future is None or future.done():
                continue
            if "error" in msg:
                err = msg["error"]
                future.set_exception(
                    RuntimeError(err.get("message", "MCP error"))
                )
            else:
                future.set_result(msg.get("result", {}))

    async def _send(self, payload: dict) -> None:
        assert self._proc is not None and self._proc.stdin is not None
        self._proc.stdin.write((json.dumps(payload) + "\n").encode())
        await self._proc.stdin.drain()

    async def _request(self, method: str, params: dict) -> dict:
        """Sends a JSON-RPC request and awaits its matching response."""
        self._next_id += 1
        msg_id = self._next_id
        future: asyncio.Future = asyncio.get_running_loop().create_future()
        self._pending[msg_id] = future
        await self._send(
            {"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params}
        )
        try:
            return await asyncio.wait_for(future, timeout=_REQUEST_TIMEOUT)
        finally:
            self._pending.pop(msg_id, None)

    async def _notify(self, method: str, params: dict) -> None:
        """Sends a JSON-RPC notification (no id, no response expected)."""
        await self._send({"jsonrpc": "2.0", "method": method, "params": params})

    # --- tool invocation ----------------------------------------------------

    async def call_tool(self, tool_name: str, arguments: dict) -> str:
        """Invokes a tool on the server and returns its text content."""
        result = await self._request(
            "tools/call", {"name": tool_name, "arguments": arguments}
        )
        parts = [
            block.get("text", "")
            for block in result.get("content", [])
            if block.get("type") == "text"
        ]
        return "\n".join(parts)
