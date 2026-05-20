"""Hub HTTP server — spec section 4.7 / Sprint 11 (Hub & Marketplace).

Exposes a `HubRegistry` over HTTP so a hub can be reached at a URL such as
``skills.argo-agent.io`` rather than only as a local directory. The wire
format is small and JSON-based; package bytes are transferred raw.

API (all under ``/hub/v1``):
  GET  /hub/v1/health                  -> {"status": "ok"}
  GET  /hub/v1/index                   -> {"packages": [entry, ...]}
  GET  /hub/v1/search?q=&kind=         -> {"packages": [entry, ...]}
  GET  /hub/v1/package/<name>?version= -> a single entry, or 404
  GET  /hub/v1/versions/<name>         -> {"versions": [entry, ...]}
  GET  /hub/v1/download/<name>?version=-> the .argopkg bytes
  POST /hub/v1/publish                 -> publish a pre-signed package

A publish request carries the package bytes as the body and the detached
signature in headers (``X-Argo-Publisher``, ``X-Argo-Signature``,
``X-Argo-Algorithm``); the hub stores what the publisher signed and never
needs a signing key itself.

Standard library only — `http.server`, mirroring `argo_brain.api.server`.
"""

from __future__ import annotations

import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from argo_brain.hub.package import ArgoPackage, PackageError
from argo_brain.hub.registry import HubRegistry, RegistryError
from argo_brain.hub.signing import ALGO_HMAC_SHA256, Signature

log = logging.getLogger("argo_brain.hub")

_API = "/hub/v1"


class HubServer:
    """A threaded HTTP server serving one `HubRegistry`."""

    def __init__(
        self,
        registry: HubRegistry,
        host: str = "127.0.0.1",
        port: int = 8730,
    ) -> None:
        self.registry = registry
        self.host = host
        self.port = port
        self._httpd: ThreadingHTTPServer | None = None
        registry.init()

    def _handler(self) -> type[BaseHTTPRequestHandler]:
        registry = self.registry

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, fmt: str, *args) -> None:  # noqa: A003
                log.info("%s - %s", self.address_string(), fmt % args)

            # -- response helpers ----------------------------------------
            def _json(self, code: int, payload: dict) -> None:
                body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _bytes(self, code: int, blob: bytes, filename: str) -> None:
                self.send_response(code)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header(
                    "Content-Disposition", f'attachment; filename="{filename}"'
                )
                self.send_header("Content-Length", str(len(blob)))
                self.end_headers()
                self.wfile.write(blob)

            def _error(self, code: int, message: str) -> None:
                self._json(code, {"error": message})

            # -- routing -------------------------------------------------
            def do_GET(self) -> None:  # noqa: N802
                parsed = urlparse(self.path)
                path = parsed.path.rstrip("/")
                qs = parse_qs(parsed.query)
                try:
                    self._route_get(path, qs)
                except RegistryError as exc:
                    self._error(404, str(exc))
                except Exception as exc:  # noqa: BLE001
                    log.exception("hub GET failed")
                    self._error(500, f"internal error: {exc}")

            def _route_get(self, path: str, qs: dict) -> None:
                if path == f"{_API}/health":
                    self._json(200, {"status": "ok", "component": "argo-hub"})
                elif path == f"{_API}/index":
                    self._json(200, {
                        "packages": [e.to_dict() for e in registry.all()],
                    })
                elif path == f"{_API}/search":
                    query = qs.get("q", [""])[0]
                    kind = qs.get("kind", [None])[0]
                    hits = registry.search(query, kind=kind)
                    self._json(200, {"packages": [e.to_dict() for e in hits]})
                elif path.startswith(f"{_API}/package/"):
                    name = unquote(path[len(f"{_API}/package/"):])
                    version = qs.get("version", [None])[0]
                    self._json(200, registry.get(name, version).to_dict())
                elif path.startswith(f"{_API}/versions/"):
                    name = unquote(path[len(f"{_API}/versions/"):])
                    rows = registry.versions(name)
                    self._json(200, {"versions": [e.to_dict() for e in rows]})
                elif path.startswith(f"{_API}/download/"):
                    name = unquote(path[len(f"{_API}/download/"):])
                    version = qs.get("version", [None])[0]
                    entry, package = registry.fetch(name, version)
                    self._bytes(200, package.to_bytes(), entry.filename)
                else:
                    self._error(404, f"no such route: {path}")

            def do_POST(self) -> None:  # noqa: N802
                parsed = urlparse(self.path)
                if parsed.path.rstrip("/") != f"{_API}/publish":
                    self._error(404, f"no such route: {parsed.path}")
                    return
                try:
                    self._publish()
                except (PackageError, RegistryError, ValueError) as exc:
                    self._error(400, str(exc))
                except Exception as exc:  # noqa: BLE001
                    log.exception("hub publish failed")
                    self._error(500, f"internal error: {exc}")

            def _publish(self) -> None:
                length = int(self.headers.get("Content-Length", 0))
                if length <= 0:
                    raise ValueError("empty request body")
                body = self.rfile.read(length)
                publisher = self.headers.get("X-Argo-Publisher", "")
                sig_value = self.headers.get("X-Argo-Signature", "")
                algorithm = self.headers.get("X-Argo-Algorithm", ALGO_HMAC_SHA256)
                if not publisher or not sig_value:
                    raise ValueError(
                        "X-Argo-Publisher and X-Argo-Signature headers required"
                    )
                package = ArgoPackage.from_bytes(body)
                signature = Signature(
                    publisher=publisher, algorithm=algorithm, value=sig_value
                )
                entry = registry.publish(package, signature)
                self._json(201, entry.to_dict())

        return Handler

    # -- lifecycle ---------------------------------------------------------
    def _bind(self) -> None:
        """Create the HTTP server and reflect back the actually-bound port."""
        self._httpd = ThreadingHTTPServer((self.host, self.port), self._handler())
        # With port=0 the OS picks a free port — surface the real one.
        self.port = self._httpd.server_address[1]

    def start(self) -> None:
        """Bind the socket and serve in the current thread (blocks until `stop`)."""
        if self._httpd is None:
            self._bind()
        log.info("argo-hub serving on http://%s:%s", self.host, self.port)
        self._httpd.serve_forever()

    def serve_in_thread(self) -> "threading.Thread":
        """Bind now and serve on a background daemon thread; returns the thread."""
        import threading

        self._bind()
        thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        thread.start()
        return thread

    def stop(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"
