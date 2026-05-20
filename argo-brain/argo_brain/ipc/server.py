"""IPC server — the Unix socket interface that argo-core connects to.

Spec section 3.4: line-delimited JSON over a Unix socket. Each message is
a single line terminated by `\\n`.

Supported `action`s (skeleton):
  * ``ping``         -> ``{"pong": true}``
  * ``chat``         -> the agent response (``AgentResponse.to_dict()``)
  * ``get_history``  -> a list of the user's messages
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from argo_brain.config import Settings
from argo_brain.core import AgentCore, AgentRequest

log = logging.getLogger("argo_brain.ipc")


class IPCServer:
    """Line-delimited JSON IPC server over a Unix socket."""

    def __init__(self, settings: Settings, agent: AgentCore | None = None) -> None:
        self.settings = settings
        self.agent = agent or AgentCore(settings)
        self._socket_path = settings.resolved_ipc_socket
        self._server: asyncio.AbstractServer | None = None

    async def _dispatch(self, req: dict) -> dict:
        """Routes a single IPC request to the appropriate action."""
        action = req.get("action")
        req_id = req.get("id")

        if action == "ping":
            return {"id": req_id, "pong": True}

        if action == "chat":
            resp = await self.agent.process(
                AgentRequest(
                    user_id=req.get("user_id", "anon"),
                    message=req.get("message", ""),
                    language=req.get("language", ""),
                    channel=req.get("channel", "ipc"),
                    session_id=req.get("session_id"),
                )
            )
            return {"id": req_id, **resp.to_dict()}

        if action == "get_history":
            history = await self.agent.memory.history(
                req.get("user_id", "anon"), limit=int(req.get("limit", 20))
            )
            return {"id": req_id, "history": history}

        return {"id": req_id, "error": f"noma'lum action: {action}"}

    async def _handle(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        peer = "core"
        log.info("IPC ulanish: %s", peer)
        try:
            while line := await reader.readline():
                try:
                    req = json.loads(line)
                except json.JSONDecodeError:
                    resp = {"error": "buzilgan JSON"}
                else:
                    resp = await self._dispatch(req)
                writer.write((json.dumps(resp, ensure_ascii=False) + "\n").encode())
                await writer.drain()
        except (ConnectionResetError, asyncio.IncompleteReadError):
            pass
        finally:
            writer.close()
            log.info("IPC uzildi: %s", peer)

    async def serve_forever(self) -> None:
        """Opens the socket and serves requests until stopped."""
        path = Path(self._socket_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            path.unlink()  # clean up the stale socket

        self._server = await asyncio.start_unix_server(self._handle, path=str(path))
        log.info("IPC server tinglamoqda: %s", path)
        async with self._server:
            await self._server.serve_forever()

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
        self.agent.close()
        Path(self._socket_path).unlink(missing_ok=True)
