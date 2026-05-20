"""OpenAI-compatible proxy server — spec section 4.9.

In the target architecture third-party tools talk to the ARGO brain through
familiar OpenAI client libraries. This module provides a stdlib `http.server`
based proxy that accepts OpenAI-shaped requests, runs the last user message
through an `AgentCore`, and returns OpenAI-shaped responses.

Endpoints:
  POST /v1/chat/completions  -> run last user message, return chat.completion
  GET  /v1/models            -> list available models
  GET  /health               -> liveness probe

The request/response converters (`openai_request_to_message` and
`agent_response_to_openai`) are kept as pure, side-effect-free module-level
functions so they can be unit-tested without binding a socket.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from argo_brain.core import AgentCore, AgentRequest

log = logging.getLogger("argo_brain.proxy")


# --------------------------------------------------------------------------
# Pure converter functions (spec section 4.9) — no I/O, fully testable.
# --------------------------------------------------------------------------


def openai_request_to_message(body: dict) -> str:
    """Extracts the last user message from an OpenAI chat request body.

    An OpenAI chat request carries a `messages` list of role/content objects.
    The agent loop only needs the most recent user turn, since prior history
    is reconstructed from persistent memory by the `AgentCore` itself.

    The `content` field may be a plain string or, in the newer OpenAI schema,
    a list of typed content parts (e.g. `{"type": "text", "text": "..."}`).
    Both forms are flattened to plain text here.

    Returns an empty string when the body is missing, malformed, or contains
    no user message.
    """
    if not isinstance(body, dict):
        return ""
    messages = body.get("messages")
    if not isinstance(messages, list):
        return ""

    # Walk the list in reverse to find the most recent user turn.
    for msg in reversed(messages):
        if not isinstance(msg, dict):
            continue
        if msg.get("role") != "user":
            continue
        return _flatten_content(msg.get("content", ""))
    return ""


def _flatten_content(content: object) -> str:
    """Flattens an OpenAI message `content` value into plain text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        # Multi-part content: collect every text fragment.
        parts: list[str] = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                parts.append(str(part.get("text", "")))
            elif isinstance(part, str):
                parts.append(part)
        return "".join(parts)
    return ""


def agent_response_to_openai(content: str, model: str) -> dict:
    """Builds an OpenAI `chat.completion` envelope from agent output text.

    Token usage counts are not tracked by the agent loop, so the `usage`
    block is reported as zeroes — this keeps the response schema valid for
    OpenAI client libraries that expect the field to be present.
    """
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content,
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
    }


# --------------------------------------------------------------------------
# Proxy server
# --------------------------------------------------------------------------


class OpenAIProxy:
    """Threaded OpenAI-compatible HTTP proxy wrapping a shared `AgentCore`."""

    def __init__(
        self,
        agent: AgentCore,
        host: str = "127.0.0.1",
        port: int = 8001,
    ) -> None:
        self.agent = agent
        self.host = host
        self.port = port
        self._httpd: ThreadingHTTPServer | None = None

    def _make_handler(self) -> type[BaseHTTPRequestHandler]:
        agent = self.agent

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, fmt: str, *args) -> None:  # noqa: A003
                log.info("%s - %s", self.address_string(), fmt % args)

            # -- helpers ----------------------------------------------------

            def _send(self, code: int, payload: dict) -> None:
                body = json.dumps(payload, ensure_ascii=False).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _send_error(self, code: int, message: str) -> None:
                # OpenAI-style error envelope.
                self._send(code, {"error": {"message": message, "type": "invalid_request_error"}})

            def _read_json(self) -> dict | None:
                length = int(self.headers.get("Content-Length", 0))
                try:
                    return json.loads(self.rfile.read(length) or b"{}")
                except json.JSONDecodeError:
                    return None

            # -- routing ----------------------------------------------------

            def do_GET(self) -> None:  # noqa: N802
                path = urlparse(self.path).path
                if path == "/health":
                    self._send(200, {"status": "ok"})
                elif path == "/v1/models":
                    self._handle_models()
                else:
                    self._send_error(404, "not found")

            def do_POST(self) -> None:  # noqa: N802
                path = urlparse(self.path).path
                if path == "/v1/chat/completions":
                    self._handle_chat_completions()
                else:
                    self._send_error(404, "not found")

            # -- endpoint handlers -----------------------------------------

            def _handle_models(self) -> None:
                """GET /v1/models — list the model served by this proxy."""
                model = agent.provider.model
                self._send(
                    200,
                    {
                        "object": "list",
                        "data": [
                            {
                                "id": model,
                                "object": "model",
                                "created": int(time.time()),
                                "owned_by": "argo-brain",
                            }
                        ],
                    },
                )

            def _handle_chat_completions(self) -> None:
                """POST /v1/chat/completions — run the request through the agent."""
                body = self._read_json()
                if body is None:
                    self._send_error(400, "invalid JSON")
                    return

                message = openai_request_to_message(body)
                if not message:
                    self._send_error(400, "no user message found")
                    return

                # The requested model is echoed back; the actual provider is
                # whatever the AgentCore was configured with.
                requested_model = body.get("model") or agent.provider.model

                resp = asyncio.run(
                    agent.process(
                        AgentRequest(
                            user_id=str(body.get("user", "openai-proxy")),
                            message=message,
                            channel="openai-proxy",
                        )
                    )
                )
                self._send(200, agent_response_to_openai(resp.content, requested_model))

        return Handler

    def serve_forever(self) -> None:
        """Starts the proxy and blocks until interrupted."""
        self._httpd = ThreadingHTTPServer((self.host, self.port), self._make_handler())
        log.info("OpenAI proxy listening on %s:%s", self.host, self.port)
        try:
            self._httpd.serve_forever()
        finally:
            self.agent.close()

    def stop(self) -> None:
        """Shuts down the proxy server if it is running."""
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
