"""HTTP API gateway — spec section 4.1 (subset).

In the target architecture the public HTTP/WS surface is `argo-core`, written
in Rust. Until that binary exists this stdlib `http.server` gateway provides
the same core endpoints in Python, so the brain is reachable over HTTP today.

Endpoints:
  GET  /api/health          -> liveness probe + version
  GET  /api/version         -> version info
  POST /api/chat            -> {"user_id", "message"} -> AgentResponse
  GET  /api/history?user_id -> message history
"""

from __future__ import annotations

import asyncio
import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from argo_brain import __version__
from argo_brain.config import Settings
from argo_brain.core import AgentCore, AgentRequest

log = logging.getLogger("argo_brain.api")


class HTTPGateway:
    """Threaded HTTP gateway wrapping a shared `AgentCore`."""

    def __init__(self, settings: Settings, host: str = "127.0.0.1",
                 port: int = 8000, agent: AgentCore | None = None) -> None:
        self.settings = settings
        self.host = host
        self.port = port
        self.agent = agent or AgentCore(settings)
        self._httpd: ThreadingHTTPServer | None = None

    def _make_handler(self) -> type[BaseHTTPRequestHandler]:
        agent = self.agent

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, fmt: str, *args) -> None:  # noqa: A003
                log.info("%s - %s", self.address_string(), fmt % args)

            def _send(self, code: int, payload: dict) -> None:
                body = json.dumps(payload, ensure_ascii=False).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self) -> None:  # noqa: N802
                parsed = urlparse(self.path)
                if parsed.path == "/api/health":
                    self._send(200, {"status": "ok", "version": __version__})
                elif parsed.path == "/api/version":
                    self._send(200, {"version": __version__, "component": "argo-brain"})
                elif parsed.path == "/api/history":
                    qs = parse_qs(parsed.query)
                    user_id = qs.get("user_id", ["anon"])[0]
                    history = asyncio.run(agent.memory.history(user_id))
                    self._send(200, {"history": history})
                else:
                    self._send(404, {"error": "not found"})

            def do_POST(self) -> None:  # noqa: N802
                if urlparse(self.path).path != "/api/chat":
                    self._send(404, {"error": "not found"})
                    return
                length = int(self.headers.get("Content-Length", 0))
                try:
                    req = json.loads(self.rfile.read(length) or b"{}")
                except json.JSONDecodeError:
                    self._send(400, {"error": "invalid JSON"})
                    return
                resp = asyncio.run(
                    agent.process(
                        AgentRequest(
                            user_id=req.get("user_id", "anon"),
                            message=req.get("message", ""),
                            language=req.get("language", ""),
                            channel=req.get("channel", "http"),
                        )
                    )
                )
                self._send(200, resp.to_dict())

        return Handler

    def serve_forever(self) -> None:
        """Starts the gateway and blocks until interrupted."""
        self._httpd = ThreadingHTTPServer((self.host, self.port), self._make_handler())
        log.info("HTTP gateway listening on %s:%s", self.host, self.port)
        try:
            self._httpd.serve_forever()
        finally:
            self.agent.close()

    def stop(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
