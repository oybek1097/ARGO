"""Docker terminal backend — runs commands in a container (spec section 4.15).

``DockerBackend`` shells out to the ``docker`` CLI and runs each command in a
fresh, throwaway container via ``docker run --rm``. If the ``docker`` binary
is not installed (or the daemon is unreachable) the backend fails *cleanly*:
it returns a :class:`CommandResult` with ``success=False`` instead of raising.
"""

from __future__ import annotations

import asyncio
import shutil

from argo_brain.terminals.base import CommandResult, TerminalBackend

_MAX_OUTPUT = 32 * 1024


class DockerBackend(TerminalBackend):
    """Run commands inside a Docker container (spec section 4.15)."""

    name = "docker"

    def __init__(
        self,
        image: str = "alpine:latest",
        shell: str = "/bin/sh",
        docker_path: str = "docker",
    ) -> None:
        """Create a docker backend.

        Args:
            image: The container image to run commands in.
            shell: The in-container shell used to interpret the command.
            docker_path: Name or path of the ``docker`` executable.
        """
        self.image = image
        self.shell = shell
        self.docker_path = docker_path

    async def run(self, command: str, timeout: int = 30) -> CommandResult:
        """Run ``command`` inside a container (spec section 4.15).

        Args:
            command: The shell command to execute in the container.
            timeout: Maximum number of seconds to wait for completion.

        Returns:
            A :class:`CommandResult`. A missing ``docker`` CLI, an unreachable
            daemon, or a timeout are all reported via ``success=False``.
        """
        # Fail cleanly when docker is not installed at all.
        if shutil.which(self.docker_path) is None:
            return CommandResult(
                stdout="",
                stderr=(
                    f"Docker CLI {self.docker_path!r} not found; "
                    "cannot run containerised command."
                ),
                exit_code=-1,
                success=False,
                backend=self.name,
            )

        argv = [
            self.docker_path,
            "run",
            "--rm",
            self.image,
            self.shell,
            "-c",
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
                stderr=f"Could not start docker: {exc}",
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
                stderr=f"Docker command timed out after {timeout}s.",
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
