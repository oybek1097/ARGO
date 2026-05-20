"""Local terminal backend — runs commands on the host (spec section 4.15).

``LocalBackend`` executes a shell command in a subprocess on the machine the
agent itself runs on. It is the only backend guaranteed to work everywhere
and is therefore the default.
"""

from __future__ import annotations

import asyncio

from argo_brain.terminals.base import CommandResult, TerminalBackend

# Cap captured output so a noisy command cannot exhaust memory.
_MAX_OUTPUT = 32 * 1024


class LocalBackend(TerminalBackend):
    """Run commands locally via an asyncio subprocess (spec section 4.15)."""

    name = "local"

    def __init__(self, cwd: str | None = None) -> None:
        """Create a local backend.

        Args:
            cwd: Optional working directory for executed commands.
        """
        self.cwd = cwd

    async def run(self, command: str, timeout: int = 30) -> CommandResult:
        """Run ``command`` locally and capture its output (spec section 4.15).

        Args:
            command: The shell command to execute.
            timeout: Maximum number of seconds to wait for completion.

        Returns:
            A :class:`CommandResult`. Spawn failures and timeouts are reported
            via ``success=False`` rather than raised.
        """
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.cwd,
            )
        except OSError as exc:
            return CommandResult(
                stdout="",
                stderr=f"Could not execute command: {exc}",
                exit_code=-1,
                success=False,
                backend=self.name,
            )

        try:
            raw_out, raw_err = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            # Kill the runaway process and reap it so no zombie remains.
            proc.kill()
            await proc.wait()
            return CommandResult(
                stdout="",
                stderr=f"Command timed out after {timeout}s.",
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
