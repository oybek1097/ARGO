"""Minimal stdlib WebSocket client — spec section 4.5.

Python's standard library ships no WebSocket client, yet the Discord Gateway
(needed to *receive* messages) speaks WebSocket over TLS. This module is a
focused, dependency-free RFC 6455 implementation: just enough to do the
HTTP Upgrade handshake and exchange text frames (plus ping/pong control
frames).

It deliberately covers only what the Discord adapter needs:

* client role (so every outbound frame is masked, as RFC 6455 mandates);
* text frames (opcode 0x1) and control frames close/ping/pong;
* synchronous blocking I/O over `socket` / `ssl` (the Discord adapter runs
  it in a worker thread, exactly like the other polling adapters).

The frame codec helpers `encode_frame` / `decode_frame` are pure functions
with no I/O, so they can be unit-tested fully offline.
"""

from __future__ import annotations

import base64
import hashlib
import os
import socket
import ssl
import struct
import urllib.parse

# RFC 6455 opcodes.
OPCODE_CONTINUATION = 0x0
OPCODE_TEXT = 0x1
OPCODE_BINARY = 0x2
OPCODE_CLOSE = 0x8
OPCODE_PING = 0x9
OPCODE_PONG = 0xA

# Magic GUID from RFC 6455 section 4.2.2, used to derive Sec-WebSocket-Accept.
_WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


def make_ws_key() -> str:
    """Generates a fresh, random base64 `Sec-WebSocket-Key` header value.

    RFC 6455 requires a 16-byte random nonce, base64-encoded. The server
    echoes back a derived value in `Sec-WebSocket-Accept` which the client
    can verify with `expected_accept`.
    """
    return base64.b64encode(os.urandom(16)).decode("ascii")


def expected_accept(ws_key: str) -> str:
    """Derives the `Sec-WebSocket-Accept` value the server must return.

    Per RFC 6455: SHA-1 of the client key concatenated with the magic GUID,
    then base64-encoded. Used to validate the handshake response.
    """
    digest = hashlib.sha1((ws_key + _WS_GUID).encode("ascii")).digest()
    return base64.b64encode(digest).decode("ascii")


def encode_frame(payload: str, opcode: int = OPCODE_TEXT) -> bytes:
    """Encodes a single, complete (FIN=1) client WebSocket frame.

    Pure function — no I/O. A client frame is always masked (RFC 6455
    section 5.3): a random 4-byte masking key is generated and XOR-applied
    to the payload. The payload-length field uses the 7-bit / 16-bit / 64-bit
    extended forms depending on size.
    """
    data = payload.encode("utf-8")
    length = len(data)

    # First byte: FIN bit set (0x80) plus the 4-bit opcode.
    header = bytearray()
    header.append(0x80 | (opcode & 0x0F))

    # Second byte: mask bit (0x80, always set for clients) plus length code.
    if length < 126:
        header.append(0x80 | length)
    elif length < 65536:
        header.append(0x80 | 126)
        header.extend(struct.pack("!H", length))
    else:
        header.append(0x80 | 127)
        header.extend(struct.pack("!Q", length))

    # 4-byte masking key followed by the masked payload.
    mask = os.urandom(4)
    masked = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
    return bytes(header) + mask + masked


def decode_frame(data: bytes) -> tuple[int, str]:
    """Decodes a single complete WebSocket frame from `data`.

    Pure function — no I/O. Returns `(opcode, payload_text)`. Handles the
    7/16/64-bit length forms and unmasks the payload if the mask bit is set
    (server frames are normally unmasked, but this stays correct either way).

    `data` must contain at least one whole frame; trailing bytes are ignored.
    """
    if len(data) < 2:
        raise ValueError("frame too short")

    opcode = data[0] & 0x0F
    masked = bool(data[1] & 0x80)
    length = data[1] & 0x7F
    offset = 2

    # Resolve the extended payload length.
    if length == 126:
        length = struct.unpack("!H", data[offset:offset + 2])[0]
        offset += 2
    elif length == 127:
        length = struct.unpack("!Q", data[offset:offset + 8])[0]
        offset += 8

    # If masked, the next 4 bytes are the masking key.
    mask = b""
    if masked:
        mask = data[offset:offset + 4]
        offset += 4

    payload = data[offset:offset + length]
    if masked:
        payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))

    return opcode, payload.decode("utf-8", errors="replace")


class WSClient:
    """A minimal blocking WebSocket client (text frames + ping/pong)."""

    def __init__(self) -> None:
        self._sock: ssl.SSLSocket | socket.socket | None = None
        # Buffer of bytes already read from the socket but not yet consumed
        # as a full frame.
        self._buf = bytearray()
        self._connected = False

    @property
    def connected(self) -> bool:
        """Whether the handshake completed and the socket is open."""
        return self._connected

    def connect(self, url: str, timeout: float = 30.0) -> None:
        """Opens a TCP/TLS connection and performs the RFC 6455 handshake.

        `url` is a `ws://` or `wss://` URL. The handshake is an HTTP/1.1
        `Upgrade` request carrying a random `Sec-WebSocket-Key`; the server
        must answer `101 Switching Protocols` with a matching
        `Sec-WebSocket-Accept`.
        """
        parsed = urllib.parse.urlparse(url)
        secure = parsed.scheme == "wss"
        host = parsed.hostname or ""
        port = parsed.port or (443 if secure else 80)
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"

        raw = socket.create_connection((host, port), timeout=timeout)
        if secure:
            ctx = ssl.create_default_context()
            sock = ctx.wrap_socket(raw, server_hostname=host)
        else:
            sock = raw
        self._sock = sock

        ws_key = make_ws_key()
        request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {ws_key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "\r\n"
        )
        sock.sendall(request.encode("ascii"))

        # Read the HTTP response headers (everything up to the blank line).
        response = bytearray()
        while b"\r\n\r\n" not in response:
            chunk = sock.recv(4096)
            if not chunk:
                raise ConnectionError("connection closed during handshake")
            response.extend(chunk)

        head, _, rest = bytes(response).partition(b"\r\n\r\n")
        # Any bytes past the header block are the start of frame data.
        self._buf.extend(rest)

        status_line = head.split(b"\r\n", 1)[0].decode("latin-1")
        if "101" not in status_line:
            raise ConnectionError(f"handshake failed: {status_line}")

        # Validate Sec-WebSocket-Accept so we know we reached a real WS peer.
        headers = self._parse_headers(head)
        accept = headers.get("sec-websocket-accept", "")
        if accept and accept != expected_accept(ws_key):
            raise ConnectionError("invalid Sec-WebSocket-Accept")

        self._connected = True

    @staticmethod
    def _parse_headers(head: bytes) -> dict[str, str]:
        """Parses HTTP response headers into a lower-cased name->value map."""
        headers: dict[str, str] = {}
        for line in head.split(b"\r\n")[1:]:
            if b":" in line:
                name, _, value = line.partition(b":")
                headers[name.strip().lower().decode("latin-1")] = (
                    value.strip().decode("latin-1")
                )
        return headers

    def send(self, text: str) -> None:
        """Sends `text` as a single masked text frame."""
        if not self._connected or self._sock is None:
            raise ConnectionError("WebSocket is not connected")
        self._sock.sendall(encode_frame(text, OPCODE_TEXT))

    def _send_control(self, opcode: int, payload: str = "") -> None:
        """Sends a control frame (close/ping/pong)."""
        if self._sock is not None:
            self._sock.sendall(encode_frame(payload, opcode))

    def _read_exactly(self, n: int) -> bytes:
        """Reads exactly `n` bytes, draining the internal buffer first."""
        while len(self._buf) < n:
            if self._sock is None:
                raise ConnectionError("socket closed")
            chunk = self._sock.recv(4096)
            if not chunk:
                raise ConnectionError("connection closed")
            self._buf.extend(chunk)
        out = bytes(self._buf[:n])
        del self._buf[:n]
        return out

    def recv(self) -> str:
        """Receives and returns the next text frame's payload.

        Control frames are handled transparently: a ping is answered with a
        pong, a close triggers `close()` and raises `ConnectionError`. The
        method keeps reading until an application text frame arrives.
        """
        if not self._connected:
            raise ConnectionError("WebSocket is not connected")

        while True:
            # Read the 2-byte minimal header to learn opcode + length code.
            first_two = self._read_exactly(2)
            opcode = first_two[0] & 0x0F
            masked = bool(first_two[1] & 0x80)
            length = first_two[1] & 0x7F

            if length == 126:
                length = struct.unpack("!H", self._read_exactly(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", self._read_exactly(8))[0]

            mask = self._read_exactly(4) if masked else b""
            payload = self._read_exactly(length)
            if masked:
                payload = bytes(
                    b ^ mask[i % 4] for i, b in enumerate(payload)
                )

            if opcode == OPCODE_TEXT:
                return payload.decode("utf-8", errors="replace")
            if opcode == OPCODE_PING:
                # Echo the ping payload straight back as a pong.
                self._send_control(
                    OPCODE_PONG, payload.decode("utf-8", errors="replace")
                )
                continue
            if opcode == OPCODE_PONG:
                # Unsolicited pong — nothing to do, keep waiting.
                continue
            if opcode == OPCODE_CLOSE:
                self.close()
                raise ConnectionError("WebSocket closed by peer")
            # Binary / continuation frames are not expected from the Gateway.
            continue

    def close(self) -> None:
        """Sends a close frame (best-effort) and shuts the socket down."""
        if self._sock is not None:
            try:
                self._send_control(OPCODE_CLOSE)
            except OSError:
                pass
            try:
                self._sock.close()
            except OSError:
                pass
        self._sock = None
        self._connected = False
