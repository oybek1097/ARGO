"""Email channel adapter — spec section 4.5.

Uses plain IMAP for receiving and SMTP for sending. Dependency-free: all
mail handling is done with the stdlib `imaplib`, `smtplib` and `email`
modules. The blocking IMAP/SMTP calls run inside `asyncio.to_thread` so the
async `Channel` interface holds.

Inbound mail is discovered by polling the IMAP INBOX for UNSEEN messages
every `poll_interval` seconds. Replies are sent straight back to the
sender's address (no threading/References handling — a later-sprint
addition).
"""

from __future__ import annotations

import asyncio
import email
import email.utils
import imaplib
import logging
import smtplib
from collections.abc import AsyncIterator
from email.message import EmailMessage

from argo_brain.channels.base import (
    AuthMode,
    Channel,
    ChannelDirection,
    ChannelHealth,
    ChannelMessage,
)

log = logging.getLogger("argo_brain.channels.email")


class EmailChannel(Channel):
    """IMAP + SMTP email adapter — spec section 4.5."""

    name = "email"
    direction = ChannelDirection.BIDIRECTIONAL
    auth = AuthMode.TOKEN

    def __init__(
        self,
        imap_host: str,
        smtp_host: str,
        username: str,
        password: str,
        imap_port: int = 993,
        smtp_port: int = 587,
        poll_interval: int = 30,
    ) -> None:
        # Constructing the channel only stores config; it never connects.
        # Connections are opened lazily inside start()/send()/receive().
        if not imap_host or not smtp_host:
            raise ValueError("imap_host and smtp_host are required")
        if not username:
            raise ValueError("username is required")
        self._imap_host = imap_host
        self._smtp_host = smtp_host
        self._username = username
        self._password = password
        self._imap_port = imap_port
        self._smtp_port = smtp_port
        self._poll_interval = poll_interval
        self._running = False

    # --- lifecycle ----------------------------------------------------------

    async def start(self) -> None:
        """Marks the channel ready; a probe login verifies credentials."""
        self._running = True
        # A throwaway IMAP login confirms the host and credentials work.
        await asyncio.to_thread(self._probe_imap)
        log.info("Email channel started for %s", self._username)

    async def stop(self) -> None:
        self._running = False

    def _probe_imap(self) -> None:
        """Blocking IMAP login probe (runs in a worker thread)."""
        conn = imaplib.IMAP4_SSL(self._imap_host, self._imap_port)
        try:
            conn.login(self._username, self._password)
        finally:
            try:
                conn.logout()
            except OSError:
                pass

    # --- sending ------------------------------------------------------------

    async def send(self, target: str, text: str) -> None:
        """Sends a plain-text email to the `target` address via SMTP."""
        await asyncio.to_thread(self._send_blocking, target, text)

    def _send_blocking(self, target: str, text: str) -> None:
        """Blocking SMTP send (runs in a worker thread)."""
        msg = EmailMessage()
        msg["From"] = self._username
        msg["To"] = target
        msg["Subject"] = "Re: ARGO Agent"
        msg.set_content(text or "(empty reply)")
        with smtplib.SMTP(self._smtp_host, self._smtp_port) as smtp:
            smtp.starttls()
            smtp.login(self._username, self._password)
            smtp.send_message(msg)

    # --- receiving ----------------------------------------------------------

    @staticmethod
    def parse_email(raw_bytes: bytes) -> ChannelMessage | None:
        """Parses a raw RFC822 email into a `ChannelMessage`.

        The `target` is set to the sender's address so that replies go back
        to whoever wrote in. Returns `None` when the message carries no
        usable plain-text body.
        """
        msg = email.message_from_bytes(raw_bytes)
        # email.utils.parseaddr() strips display names: "A B" <a@b> -> a@b.
        from_address = email.utils.parseaddr(msg.get("From", ""))[1]
        if not from_address:
            return None

        text = EmailChannel._extract_text(msg)
        if not text or not text.strip():
            return None

        return ChannelMessage(
            channel="email",
            user_id=f"email:{from_address}",
            target=from_address,
            text=text,
            raw={
                "from": from_address,
                "subject": msg.get("Subject", ""),
                "message_id": msg.get("Message-ID", ""),
            },
        )

    @staticmethod
    def _extract_text(msg: email.message.Message) -> str | None:
        """Pulls the first plain-text body out of a (possibly multipart) email."""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() != "text/plain":
                    continue
                # Skip attachments; we only want the inline body.
                disposition = part.get_content_disposition()
                if disposition == "attachment":
                    continue
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
            return None

        if msg.get_content_type() != "text/plain":
            return None
        payload = msg.get_payload(decode=True)
        if not payload:
            return None
        charset = msg.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace")

    async def receive(self) -> AsyncIterator[ChannelMessage]:
        """Polls the IMAP INBOX for UNSEEN mail and yields inbound messages."""
        while self._running:
            try:
                raw_messages = await asyncio.to_thread(self._fetch_unseen)
            except (imaplib.IMAP4.error, OSError) as exc:
                log.warning("IMAP poll failed, retrying: %s", exc)
                await asyncio.sleep(self._poll_interval)
                continue

            for raw in raw_messages:
                parsed = self.parse_email(raw)
                if parsed is not None:
                    yield parsed

            await asyncio.sleep(self._poll_interval)

    def _fetch_unseen(self) -> list[bytes]:
        """Blocking IMAP fetch of all UNSEEN messages (runs in a worker thread)."""
        conn = imaplib.IMAP4_SSL(self._imap_host, self._imap_port)
        out: list[bytes] = []
        try:
            conn.login(self._username, self._password)
            conn.select("INBOX")
            status, data = conn.search(None, "UNSEEN")
            if status != "OK":
                return out
            for num in data[0].split():
                fetch_status, fetch_data = conn.fetch(num, "(RFC822)")
                if fetch_status != "OK" or not fetch_data:
                    continue
                # fetch_data is a list of tuples; the body is the second item.
                for item in fetch_data:
                    if isinstance(item, tuple) and item[1]:
                        out.append(item[1])
        finally:
            try:
                conn.logout()
            except OSError:
                pass
        return out

    def health(self) -> ChannelHealth:
        return ChannelHealth(
            ok=self._running,
            detail="polling" if self._running else "stopped",
        )
