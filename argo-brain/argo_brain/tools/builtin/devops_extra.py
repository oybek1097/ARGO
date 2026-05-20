"""Additional DevOps tools — spec section 4.4 (`devops` toolset extension).

This module extends the core DevOps toolset (`devops.py`) with thin, audited
CLI wrappers for secret management (Vault), remote execution (SSH),
configuration management (Ansible) and infrastructure-as-code (Terraform).

Following the established pattern in `devops.py`, every tool runs the
underlying CLI via an asyncio subprocess and fails CLEANLY with a clear
message when the CLI is not installed (the `FileNotFoundError` raised by
`asyncio.create_subprocess_exec` is caught inside `_run_cli`).

Mutating tools carry `dangerous = True` so the agent loop can request
confirmation before they run.
"""

from __future__ import annotations

from argo_brain.tools.base import Tool, ToolResult

# Reuse the audited CLI helper from devops.py — importing is read-only and
# keeps the timeout / output-truncation / not-installed handling consistent.
from argo_brain.tools.builtin.devops import _run_cli


# --- Vault tools ------------------------------------------------------------

class VaultGetTool(Tool):
    """Reads a secret from HashiCorp Vault via `vault kv get`."""

    name = "vault_get"
    description = "Reads a secret from HashiCorp Vault at the given KV path."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "KV secret path"},
        },
        "required": ["path"],
    }

    async def run(self, user_id: str, path: str = "", **kwargs) -> ToolResult:
        if not path.strip():
            return ToolResult(content="A Vault path is required.", success=False)
        ok, out = await _run_cli(["vault", "kv", "get", path])
        return ToolResult(content=out or "(empty)", success=ok)


class VaultPutTool(Tool):
    """Writes a secret to HashiCorp Vault via `vault kv put`."""

    name = "vault_put"
    description = "Writes one or more key=value pairs to a Vault KV path."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "KV secret path"},
            "data": {
                "type": "object",
                "description": "key/value pairs to store",
            },
        },
        "required": ["path", "data"],
    }
    dangerous = True  # mutates Vault state

    async def run(self, user_id: str, path: str = "", data: dict | None = None,
                  **kwargs) -> ToolResult:
        if not path.strip():
            return ToolResult(content="A Vault path is required.", success=False)
        data = data or {}
        if not data:
            return ToolResult(
                content="At least one key=value pair is required.", success=False
            )
        argv = ["vault", "kv", "put", path]
        argv += [f"{k}={v}" for k, v in data.items()]
        ok, out = await _run_cli(argv)
        return ToolResult(content=out or "(written)", success=ok)


# --- SSH tool ---------------------------------------------------------------

class SSHExecTool(Tool):
    """Runs a command on a remote host via `ssh <host> <command>`."""

    name = "ssh_exec"
    description = "Executes a shell command on a remote host over SSH."
    parameters = {
        "type": "object",
        "properties": {
            "host": {"type": "string", "description": "SSH target (user@host)"},
            "command": {"type": "string", "description": "command to run"},
        },
        "required": ["host", "command"],
    }
    dangerous = True  # arbitrary remote execution

    async def run(self, user_id: str, host: str = "", command: str = "",
                  **kwargs) -> ToolResult:
        if not host.strip():
            return ToolResult(content="An SSH host is required.", success=False)
        if not command.strip():
            return ToolResult(content="A command is required.", success=False)
        # BatchMode avoids interactive password prompts hanging the subprocess.
        ok, out = await _run_cli(
            ["ssh", "-o", "BatchMode=yes", host, command]
        )
        return ToolResult(content=out or "(no output)", success=ok)


# --- Ansible tool -----------------------------------------------------------

class AnsiblePlaybookTool(Tool):
    """Runs an Ansible playbook via `ansible-playbook`."""

    name = "ansible_playbook"
    description = "Runs an Ansible playbook against an inventory."
    parameters = {
        "type": "object",
        "properties": {
            "playbook": {"type": "string", "description": "path to the playbook"},
            "inventory": {"type": "string", "description": "optional inventory path"},
        },
        "required": ["playbook"],
    }
    dangerous = True  # may change managed-host state

    async def run(self, user_id: str, playbook: str = "", inventory: str = "",
                  **kwargs) -> ToolResult:
        if not playbook.strip():
            return ToolResult(content="A playbook path is required.", success=False)
        argv = ["ansible-playbook", playbook]
        if inventory:
            argv += ["-i", inventory]
        ok, out = await _run_cli(argv)
        return ToolResult(content=out or "(no output)", success=ok)


# --- Terraform tools --------------------------------------------------------

class TerraformPlanTool(Tool):
    """Produces an execution plan via `terraform plan` (read-only)."""

    name = "terraform_plan"
    description = "Shows the Terraform execution plan for a working directory."
    parameters = {
        "type": "object",
        "properties": {
            "directory": {"type": "string", "description": "Terraform working dir"},
        },
    }

    async def run(self, user_id: str, directory: str = ".", **kwargs) -> ToolResult:
        ok, out = await _run_cli(["terraform", "plan", "-no-color"], cwd=directory)
        return ToolResult(content=out or "(no changes)", success=ok)


class TerraformApplyTool(Tool):
    """Applies infrastructure changes via `terraform apply -auto-approve`."""

    name = "terraform_apply"
    description = "Applies the Terraform plan, provisioning infrastructure changes."
    parameters = {
        "type": "object",
        "properties": {
            "directory": {"type": "string", "description": "Terraform working dir"},
        },
    }
    dangerous = True  # mutates real infrastructure

    async def run(self, user_id: str, directory: str = ".", **kwargs) -> ToolResult:
        ok, out = await _run_cli(
            ["terraform", "apply", "-auto-approve", "-no-color"], cwd=directory
        )
        return ToolResult(content=out or "(applied)", success=ok)


def devops_extra_tools() -> list[Tool]:
    """The extended DevOps toolset: Vault, SSH, Ansible and Terraform."""
    return [
        VaultGetTool(),
        VaultPutTool(),
        SSHExecTool(),
        AnsiblePlaybookTool(),
        TerraformPlanTool(),
        TerraformApplyTool(),
    ]
