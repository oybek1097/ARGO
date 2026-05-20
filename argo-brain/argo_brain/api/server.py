"""HTTP API gateway — spec section 4.1 (subset).

In the target architecture the public HTTP/WS surface is `argo-core`, written
in Rust. Until that binary exists this stdlib `http.server` gateway provides
the same core endpoints in Python, so the brain is reachable over HTTP today.

Endpoints:
  GET  /api/health          -> liveness probe + version
  GET  /api/version         -> version info
  POST /api/chat            -> {"user_id", "message"} -> AgentResponse
  GET  /api/history?user_id -> message history
  POST /webhook/<platform>  -> inbound webhook for a registered channel
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
                 port: int = 8000, agent: AgentCore | None = None,
                 webhooks: dict | None = None) -> None:
        self.settings = settings
        self.host = host
        self.port = port
        self.agent = agent or AgentCore(settings)
        # platform name -> WebhookChannel
        self.webhooks = webhooks or {}
        self._httpd: ThreadingHTTPServer | None = None

    def _make_handler(self) -> type[BaseHTTPRequestHandler]:
        agent = self.agent
        webhooks = self.webhooks

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

            def _read_json(self) -> dict | None:
                length = int(self.headers.get("Content-Length", 0))
                try:
                    return json.loads(self.rfile.read(length) or b"{}")
                except json.JSONDecodeError:
                    return None

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
                elif parsed.path in ("/", "/dashboard"):
                    from argo_brain.api.dashboard import dashboard_page

                    body = dashboard_page().encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                else:
                    self._send(404, {"error": "not found"})

            def do_POST(self) -> None:  # noqa: N802
                path = urlparse(self.path).path
                if path == "/api/chat":
                    self._handle_chat()
                elif path.startswith("/webhook/"):
                    self._handle_webhook(path[len("/webhook/"):])
                else:
                    self._send(404, {"error": "not found"})

            def _handle_chat(self) -> None:
                req = self._read_json()
                if req is None:
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

            def _handle_webhook(self, platform: str) -> None:
                channel = webhooks.get(platform)
                if channel is None:
                    self._send(404, {"error": f"unknown webhook: {platform}"})
                    return
                payload = self._read_json()
                if payload is None:
                    self._send(400, {"error": "invalid JSON"})
                    return
                # Platform handshake (e.g. Slack url_verification).
                challenge = channel.verify(payload)
                if challenge is not None:
                    self._send(200, challenge)
                    return
                msg = channel.parse_webhook(payload)
                if msg is None:
                    self._send(200, {"ok": True, "skipped": True})
                    return
                resp = asyncio.run(
                    agent.process(
                        AgentRequest(
                            user_id=msg.user_id,
                            message=msg.text,
                            channel=channel.name,
                        )
                    )
                )
                asyncio.run(channel.send(msg.target, resp.content))
                self._send(200, {"ok": True})

        return Handler

    def serve_forever(self) -> None:
        """Starts the gateway and blocks until interrupted."""
        self._httpd = ThreadingHTTPServer((self.host, self.port), self._make_handler())
        log.info("HTTP gateway listening on %s:%s", self.host, self.port)
        if self.webhooks:
            log.info("webhook platforms: %s", ", ".join(self.webhooks))
        try:
            self._httpd.serve_forever()
        finally:
            self.agent.close()

    def stop(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
