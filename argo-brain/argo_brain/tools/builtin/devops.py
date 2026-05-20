"""DevOps tools — spec section 4.4 (`git` / `devops` toolsets).

DevOps-native tooling is one of ARGO's exclusive strengths (spec section 0).
The skeleton ships Git, Docker and kubectl tools as thin, audited wrappers
around the respective CLIs. Vault, Proxmox, Ansible, Terraform and ArgoCD
follow in the same pattern.

If a required CLI is not installed the tool fails cleanly with a clear
message instead of raising.
"""

from __future__ import annotations

import asyncio

from argo_brain.tools.base import Tool, ToolResult

_DEFAULT_TIMEOUT = 30
_MAX_OUTPUT = 32 * 1024


async def _run_cli(argv: list[str], cwd: str | None = None,
                   timeout: int = _DEFAULT_TIMEOUT) -> tuple[bool, str]:
    """Runs an external CLI; returns (success, combined_output)."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
    except FileNotFoundError:
        return False, f"'{argv[0]}' is not installed or not on PATH"
    except OSError as exc:
        return False, f"could not run {argv[0]}: {exc}"

    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return False, f"'{argv[0]}' timed out after {timeout}s"

    text = stdout.decode("utf-8", errors="replace")
    err = stderr.decode("utf-8", errors="replace").strip()
    if err:
        text += f"\n[stderr]\n{err}"
    return proc.returncode == 0, text.strip()[:_MAX_OUTPUT]


# --- Git tools --------------------------------------------------------------

_REPO_PARAM = {
    "type": "object",
    "properties": {"repo": {"type": "string", "description": "repository path"}},
}


class GitStatusTool(Tool):
    name = "git_status"
    description = "Shows the working-tree status of a Git repository."
    parameters = _REPO_PARAM

    async def run(self, user_id: str, repo: str = ".", **kwargs) -> ToolResult:
        ok, out = await _run_cli(["git", "status", "--short", "--branch"], cwd=repo)
        return ToolResult(content=out or "(clean)", success=ok)


class GitLogTool(Tool):
    name = "git_log"
    description = "Shows the recent commit history of a Git repository."
    parameters = {
        "type": "object",
        "properties": {
            "repo": {"type": "string", "description": "repository path"},
            "limit": {"type": "integer", "description": "number of commits"},
        },
    }

    async def run(self, user_id: str, repo: str = ".", limit: int = 10,
                  **kwargs) -> ToolResult:
        ok, out = await _run_cli(
            ["git", "log", "--oneline", "-n", str(limit)], cwd=repo
        )
        return ToolResult(content=out or "(no commits)", success=ok)


class GitDiffTool(Tool):
    name = "git_diff"
    description = "Shows uncommitted changes in a Git repository."
    parameters = {
        "type": "object",
        "properties": {
            "repo": {"type": "string", "description": "repository path"},
            "path": {"type": "string", "description": "optional file/dir to diff"},
        },
    }

    async def run(self, user_id: str, repo: str = ".", path: str = "",
                  **kwargs) -> ToolResult:
        argv = ["git", "diff"]
        if path:
            argv += ["--", path]
        ok, out = await _run_cli(argv, cwd=repo)
        return ToolResult(content=out or "(no changes)", success=ok)


class GitBranchTool(Tool):
    name = "git_branch"
    description = "Lists the branches of a Git repository."
    parameters = _REPO_PARAM

    async def run(self, user_id: str, repo: str = ".", **kwargs) -> ToolResult:
        ok, out = await _run_cli(["git", "branch", "--all"], cwd=repo)
        return ToolResult(content=out or "(no branches)", success=ok)


class GitCommitTool(Tool):
    name = "git_commit"
    description = "Commits all tracked changes with a message."
    parameters = {
        "type": "object",
        "properties": {
            "repo": {"type": "string", "description": "repository path"},
            "message": {"type": "string"},
        },
        "required": ["message"],
    }
    dangerous = True

    async def run(self, user_id: str, message: str = "", repo: str = ".",
                  **kwargs) -> ToolResult:
        if not message.strip():
            return ToolResult(content="A commit message is required.", success=False)
        ok, out = await _run_cli(
            ["git", "commit", "-am", message], cwd=repo
        )
        return ToolResult(content=out, success=ok)


# --- Docker tools -----------------------------------------------------------

class DockerPsTool(Tool):
    name = "docker_ps"
    description = "Lists running Docker containers."
    parameters = {"type": "object", "properties": {}}

    async def run(self, user_id: str, **kwargs) -> ToolResult:
        ok, out = await _run_cli(
            ["docker", "ps", "--format",
             "table {{.Names}}\t{{.Image}}\t{{.Status}}"]
        )
        return ToolResult(content=out or "(no containers)", success=ok)


class DockerImagesTool(Tool):
    name = "docker_images"
    description = "Lists locally available Docker images."
    parameters = {"type": "object", "properties": {}}

    async def run(self, user_id: str, **kwargs) -> ToolResult:
        ok, out = await _run_cli(["docker", "images"])
        return ToolResult(content=out or "(no images)", success=ok)


# --- Kubernetes tools -------------------------------------------------------

class KubectlGetTool(Tool):
    name = "kubectl_get"
    description = "Lists Kubernetes resources of a given kind (pods, services, ...)."
    parameters = {
        "type": "object",
        "properties": {
            "resource": {"type": "string", "description": "e.g. pods, services"},
            "namespace": {"type": "string"},
        },
        "required": ["resource"],
    }

    async def run(self, user_id: str, resource: str = "pods",
                  namespace: str = "", **kwargs) -> ToolResult:
        argv = ["kubectl", "get", resource]
        if namespace:
            argv += ["-n", namespace]
        ok, out = await _run_cli(argv)
        return ToolResult(content=out, success=ok)


def devops_tools() -> list[Tool]:
    """The DevOps toolset: Git, Docker and Kubernetes."""
    return [
        GitStatusTool(),
        GitLogTool(),
        GitDiffTool(),
        GitBranchTool(),
        GitCommitTool(),
        DockerPsTool(),
        DockerImagesTool(),
        KubectlGetTool(),
    ]
