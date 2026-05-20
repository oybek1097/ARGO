"""SSH terminal backend — runs commands on a remote host (spec section 4.15).

``SSHBackend`` shells out to the OpenSSH ``ssh`` client and runs the command
on a remote host. If the ``ssh`` binary is missing, the host is unreachable,
or authentication fails, the backend fails *cleanly* by returning a
:class:`CommandResult` with ``success=False`` rather than raising.
"""

from __future__ import annotations

import asyncio
import shutil

from argo_brain.terminals.base import CommandResult, TerminalBackend

_MAX_OUTPUT = 32 * 1024


class SSHBackend(TerminalBackend):
    """Run commands on a remote host over SSH (spec section 4.15)."""

    name = "ssh"

    def __init__(
        self,
        host: str,
        user: str | None = None,
        port: int = 22,
        ssh_path: str = "ssh",
    ) -> None:
        """Create an SSH backend.

        Args:
            host: Remote hostname or IP address.
            user: Optional remote username (defaults to the SSH client default).
            port: Remote SSH port.
            ssh_path: Name or path of the ``ssh`` executable.
        """
        self.host = host
        self.user = user
        self.port = port
        self.ssh_path = ssh_path

    def _target(self) -> str:
        """Return the ``user@host`` (or bare ``host``) connection target."""
        return f"{self.user}@{self.host}" if self.user else self.host

    async def run(self, command: str, timeout: int = 30) -> CommandResult:
        """Run ``command`` on the remote host (spec section 4.15).

        Args:
            command: The shell command to execute remotely.
            timeout: Maximum number of seconds to wait for completion.

        Returns:
            A :class:`CommandResult`. A missing ``ssh`` CLI, an unreachable or
            invalid host, or a timeout are all reported via ``success=False``.
        """
        # Fail cleanly when the ssh client is not installed at all.
        if shutil.which(self.ssh_path) is None:
            return CommandResult(
                stdout="",
                stderr=(
                    f"SSH CLI {self.ssh_path!r} not found; "
                    "cannot run remote command."
                ),
                exit_code=-1,
                success=False,
                backend=self.name,
            )

        # Non-interactive options: never prompt, and bound the TCP connect so
        # an invalid/unreachable host fails fast instead of hanging.
        connect_timeout = max(1, min(timeout, 10))
        argv = [
            self.ssh_path,
            "-p",
            str(self.port),
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            f"ConnectTimeout={connect_timeout}",
            self._target(),
            command,
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *argv,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except OSError as exc:
            return CommandResult(
                stdout="",
                stderr=f"Could not start ssh: {exc}",
                exit_code=-1,
                success=False,
                backend=self.name,
            )

        try:
            raw_out, raw_err = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return CommandResult(
                stdout="",
                stderr=f"SSH command timed out after {timeout}s.",
                exit_code=-1,
                success=False,
                backend=self.name,
            )

        stdout = raw_out.decode("utf-8", errors="replace")[:_MAX_OUTPUT]
        stderr = raw_err.decode("utf-8", errors="replace")[:_MAX_OUTPUT]
        exit_code = proc.returncode if proc.returncode is not None else -1
        return CommandResult(
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            success=exit_code == 0,
            backend=self.name,
        )
