"""Terminal and web tool tests."""

import unittest

from argo_brain.tools.builtin.terminal import ShellExecTool
from argo_brain.tools.builtin.web import _html_to_text


class TestShellExecTool(unittest.IsolatedAsyncioTestCase):
    async def test_runs_command(self):
        r = await ShellExecTool()("u1", command="echo ARGO")
        self.assertTrue(r.success)
        self.assertIn("ARGO", r.content)

    async def test_nonzero_exit_marks_failure(self):
        r = await ShellExecTool()("u1", command="exit 3")
        self.assertFalse(r.success)
        self.assertEqual(r.metadata["exit_code"], 3)

    async def test_blocks_destructive_command(self):
        r = await ShellExecTool()("u1", command="rm   -rf   /")
        self.assertFalse(r.success)
        self.assertIn("Bloklangan", r.content)

    async def test_timeout(self):
        r = await ShellExecTool()("u1", command="sleep 5", timeout=1)
        self.assertFalse(r.success)


class TestHtmlToText(unittest.TestCase):
    def test_strips_tags(self):
        html = "<html><body><p>Hello <b>world</b></p></body></html>"
        self.assertEqual(_html_to_text(html), "Hello world")

    def test_drops_script(self):
        html = "<p>keep</p><script>alert(1)</script>"
        self.assertNotIn("alert", _html_to_text(html))


if __name__ == "__main__":
    unittest.main()
