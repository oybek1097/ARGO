"""Multi-backend terminal subsystem (spec section 4.15).

Provides a uniform :class:`TerminalBackend` interface with concrete backends
for running commands locally, inside a Docker container, or on a remote host
over SSH. Use :func:`get_backend` to obtain a backend by name.
"""

from argo_brain.terminals.base import (
    CommandResult,
    TerminalBackend,
    get_backend,
)
from argo_brain.terminals.docker import DockerBackend
from argo_brain.terminals.local import LocalBackend
from argo_brain.terminals.ssh import SSHBackend

__all__ = [
    "CommandResult",
    "TerminalBackend",
    "LocalBackend",
    "DockerBackend",
    "SSHBackend",
    "get_backend",
]
