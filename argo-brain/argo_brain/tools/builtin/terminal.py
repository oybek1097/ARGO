"""Terminal tools — spec section 4.4 (`terminal` toolset).

The skeleton ships the `local` backend (subprocess with a timeout). Other
backends from spec section 4.15 (docker, ssh, k8s_pod, firecracker, ...)
arrive in Sprint 4-5.
"""

from __future__ import annotations

import asyncio

from argo_brain.tools.base import Tool, ToolResult

_DEFAULT_TIMEOUT = 30
_MAX_OUTPUT = 32 * 1024

# Obvious destructive patterns blocked even before sandboxing exists.
_BLOCKED = (
    "rm -rf /", "mkfs", ":(){:|:&};:", "dd if=", "> /dev/sda",
)


class ShellExecTool(Tool):
    name = "shell_exec"
    description = (
        "Runs a shell command on the local backend and returns stdout/stderr. "
        "Has a timeout; obviously destructive commands are blocked."
    )
    parameters = {
        "type": "object",
        "properties": {
            "command": {"type": "string"},
            "timeout": {"type": "integer", "description": "seconds, default 30"},
            "cwd": {"type": "string", "description": "working directory"},
        },
        "required": ["command"],
    }
    dangerous = True

    async def run(self, user_id: str, command: str = "", timeout: int | None = None,
                  cwd: str | None = None, **kwargs) -> ToolResult:
        normalized = " ".join(command.split())
        if any(bad in normalized for bad in _BLOCKED):
            return ToolResult(
                content="Bloklangan buyruq: xavfli amaliyot.", success=False
            )

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )
        except OSError as exc:
            return ToolResult(content=f"Bajarib boʻlmadi: {exc}", success=False)

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout or _DEFAULT_TIMEOUT
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return ToolResult(content="Buyruq vaqti tugadi (timeout).", success=False)

        out = stdout.decode("utf-8", errors="replace")[:_MAX_OUTPUT]
        err = stderr.decode("utf-8", errors="replace")[:_MAX_OUTPUT]
        body = out
        if err:
            body += f"\n[stderr]\n{err}"
        return ToolResult(
            content=body.strip() or "(boʻsh chiqish)",
            success=proc.returncode == 0,
            metadata={"exit_code": proc.returncode},
        )


def terminal_tools() -> list[Tool]:
    return [ShellExecTool()]
