"""DevOps tool tests.

Git tools are tested against a real temporary repository (git is assumed
present). Docker/kubectl tools are tested for graceful handling when the
CLI is absent.
"""

import subprocess
import tempfile
import unittest
from pathlib import Path

from argo_brain.tools.builtin.devops import (
    DockerPsTool,
    GitBranchTool,
    GitCommitTool,
    GitDiffTool,
    GitLogTool,
    GitStatusTool,
    KubectlGetTool,
    devops_tools,
)


class TestGitTools(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = self._tmp.name
        self._git("init")
        self._git("config", "user.email", "test@argo.dev")
        self._git("config", "user.name", "ARGO Test")
        (Path(self.repo) / "file.txt").write_text("hello\n", encoding="utf-8")
        self._git("add", ".")
        self._git("commit", "-m", "initial commit")

    def tearDown(self):
        self._tmp.cleanup()

    def _git(self, *args):
        subprocess.run(
            ["git", *args], cwd=self.repo, check=True, capture_output=True
        )

    async def test_status_clean(self):
        r = await GitStatusTool()("u1", repo=self.repo)
        self.assertTrue(r.success)
        self.assertIn("##", r.content)  # branch header line

    async def test_log_shows_commit(self):
        r = await GitLogTool()("u1", repo=self.repo)
        self.assertTrue(r.success)
        self.assertIn("initial commit", r.content)

    async def test_branch_lists(self):
        r = await GitBranchTool()("u1", repo=self.repo)
        self.assertTrue(r.success)
        self.assertTrue(r.content)

    async def test_diff_shows_changes(self):
        (Path(self.repo) / "file.txt").write_text("changed\n", encoding="utf-8")
        r = await GitDiffTool()("u1", repo=self.repo)
        self.assertTrue(r.success)
        self.assertIn("changed", r.content)

    async def test_commit_requires_message(self):
        r = await GitCommitTool()("u1", repo=self.repo, message="")
        self.assertFalse(r.success)

    async def test_commit_succeeds(self):
        (Path(self.repo) / "file.txt").write_text("v2\n", encoding="utf-8")
        r = await GitCommitTool()("u1", repo=self.repo, message="update file")
        self.assertTrue(r.success)
        log = await GitLogTool()("u1", repo=self.repo)
        self.assertIn("update file", log.content)


class TestContainerTools(unittest.IsolatedAsyncioTestCase):
    async def test_docker_ps_graceful_when_absent(self):
        # docker is not installed in this environment — must fail cleanly.
        r = await DockerPsTool()("u1")
        if not r.success:
            self.assertIn("not installed", r.content)

    async def test_kubectl_get_graceful_when_absent(self):
        r = await KubectlGetTool()("u1", resource="pods")
        if not r.success:
            self.assertIn("not installed", r.content)


class TestDevopsToolset(unittest.TestCase):
    def test_toolset_complete(self):
        names = {t.name for t in devops_tools()}
        self.assertEqual(
            names,
            {"git_status", "git_log", "git_diff", "git_branch", "git_commit",
             "docker_ps", "docker_images", "kubectl_get"},
        )

    def test_commit_marked_dangerous(self):
        self.assertTrue(GitCommitTool().dangerous)


if __name__ == "__main__":
    unittest.main()
