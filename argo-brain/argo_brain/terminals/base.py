"""Multi-backend terminal subsystem — base abstractions (spec section 4.15).

This module defines the contract every terminal backend must satisfy:

* ``CommandResult`` — a uniform result object returned by every backend.
* ``TerminalBackend`` — an abstract base class with an ``async run`` method.
* ``get_backend`` — a factory that maps a backend name to a concrete class.

Concrete backends (``LocalBackend``, ``DockerBackend``, ``SSHBackend``) live
in sibling modules and are wired into the factory below.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass


@dataclass
class CommandResult:
    """Uniform result of running a command on any backend (spec section 4.15).

    Attributes:
        stdout: Captured standard output (decoded, possibly truncated).
        stderr: Captured standard error (decoded, possibly truncated).
        exit_code: Process exit code. A negative or non-zero value, or a
            sentinel such as ``-1``, indicates the command did not complete
            successfully.
        success: ``True`` only when the command ran and exited with code 0.
        backend: Name of the backend that produced this result
            (e.g. ``"local"``, ``"docker"``, ``"ssh"``).
    """

    stdout: str
    stderr: str
    exit_code: int
    success: bool
    backend: str


class TerminalBackend(abc.ABC):
    """Abstract base class for a terminal execution backend (spec section 4.15).

    Every backend executes a shell command somewhere — locally, inside a
    Docker container, on a remote host over SSH, and so on — and returns a
    :class:`CommandResult`. Backends must *never* raise for an environmental
    failure (missing CLI, unreachable host, timeout); instead they return a
    ``CommandResult`` with ``success=False`` and a useful ``stderr`` message.
    """

    #: Short identifier for this backend, overridden by subclasses.
    name: str = "base"

    @abc.abstractmethod
    async def run(self, command: str, timeout: int = 30) -> CommandResult:
        """Run ``command`` and return a :class:`CommandResult`.

        Args:
            command: The shell command to execute.
            timeout: Maximum number of seconds to wait before giving up.

        Returns:
            A :class:`CommandResult` describing the outcome. Implementations
            must catch environmental errors and report them via the result
            rather than raising.
        """
        raise NotImplementedError


def get_backend(name: str, **kwargs) -> TerminalBackend:
    """Factory: return a terminal backend instance for ``name`` (spec 4.15).

    Args:
        name: One of ``"local"``, ``"docker"`` or ``"ssh"`` (case-insensitive).
        **kwargs: Backend-specific constructor arguments. For example
            ``image=`` for docker, or ``host=`` / ``user=`` for ssh.

    Returns:
        A concrete :class:`TerminalBackend` instance.

    Raises:
        ValueError: If ``name`` is not a recognised backend.
    """
    # Imported lazily to avoid a circular import (the concrete backends
    # import ``TerminalBackend`` / ``CommandResult`` from this module).
    from argo_brain.terminals.docker import DockerBackend
    from argo_brain.terminals.local import LocalBackend
    from argo_brain.terminals.ssh import SSHBackend

    registry: dict[str, type[TerminalBackend]] = {
        "local": LocalBackend,
        "docker": DockerBackend,
        "ssh": SSHBackend,
    }

    key = (name or "").strip().lower()
    backend_cls = registry.get(key)
    if backend_cls is None:
        known = ", ".join(sorted(registry))
        raise ValueError(f"Unknown terminal backend {name!r}; known backends: {known}")
    return backend_cls(**kwargs)
