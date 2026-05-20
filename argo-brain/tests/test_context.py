"""Tests for the context-file subsystem (spec section 4.2).

Covers :class:`ContextLoader` discovery/assembly and :func:`expand_refs`
@-reference expansion. Uses stdlib :mod:`unittest` with temporary directories.
"""

import os
import tempfile
import unittest

from argo_brain.context import ContextLoader, expand_refs


class ContextLoaderTests(unittest.TestCase):
    """Exercise ContextLoader.load and ContextLoader.assemble."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.loader = ContextLoader()

    def tearDown(self):
        # Best-effort cleanup of the temporary directory.
        for root, dirs, files in os.walk(self.tmp, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(self.tmp)

    def _write(self, name, content):
        with open(os.path.join(self.tmp, name), "w", encoding="utf-8") as fh:
            fh.write(content)

    def test_load_finds_present_files(self):
        """load returns content for MEMORY.md and AGENTS.md when present."""
        self._write("MEMORY.md", "remember this")
        self._write("AGENTS.md", "agent guidance")
        found = self.loader.load(self.tmp)
        self.assertEqual(found["MEMORY.md"], "remember this")
        self.assertEqual(found["AGENTS.md"], "agent guidance")

    def test_load_ignores_absent_files(self):
        """load omits context files that do not exist."""
        self._write("MEMORY.md", "only memory")
        found = self.loader.load(self.tmp)
        self.assertIn("MEMORY.md", found)
        self.assertNotIn("USER.md", found)
        self.assertNotIn("AGENTS.md", found)
        self.assertNotIn(".argo.md", found)

    def test_load_empty_directory_returns_empty_dict(self):
        """A directory with no context files yields an empty mapping."""
        self.assertEqual(self.loader.load(self.tmp), {})

    def test_load_finds_dotfile(self):
        """The hidden .argo.md context file is discovered."""
        self._write(".argo.md", "project config")
        found = self.loader.load(self.tmp)
        self.assertEqual(found[".argo.md"], "project config")

    def test_load_finds_all_four(self):
        """All four well-known context files are discovered together."""
        self._write("MEMORY.md", "m")
        self._write("USER.md", "u")
        self._write("AGENTS.md", "a")
        self._write(".argo.md", "c")
        found = self.loader.load(self.tmp)
        self.assertEqual(set(found), {"MEMORY.md", "USER.md", "AGENTS.md", ".argo.md"})

    def test_assemble_produces_labelled_block(self):
        """assemble emits a '# Context: <name>' header per file."""
        self._write("MEMORY.md", "remember this")
        self._write("AGENTS.md", "agent guidance")
        block = self.loader.assemble(self.tmp)
        self.assertIn("# Context: MEMORY.md", block)
        self.assertIn("# Context: AGENTS.md", block)
        self.assertIn("remember this", block)
        self.assertIn("agent guidance", block)

    def test_assemble_empty_when_nothing_present(self):
        """assemble returns an empty string for an empty directory."""
        self.assertEqual(self.loader.assemble(self.tmp), "")

    def test_assemble_preserves_configured_order(self):
        """assemble emits files in the spec-defined order."""
        self._write("AGENTS.md", "a")
        self._write("MEMORY.md", "m")
        block = self.loader.assemble(self.tmp)
        self.assertLess(block.index("MEMORY.md"), block.index("AGENTS.md"))


class ExpandRefsTests(unittest.TestCase):
    """Exercise the expand_refs @-reference expander."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        for root, dirs, files in os.walk(self.tmp, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(self.tmp)

    def _write(self, relpath, content):
        path = os.path.join(self.tmp, relpath)
        os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(relpath) else None
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        return path

    def test_inlines_existing_file_ref(self):
        """An @file reference is replaced with the file's contents."""
        self._write("notes.txt", "hello from file")
        out = expand_refs("see @notes.txt please", base_dir=self.tmp)
        self.assertIn("hello from file", out)
        self.assertIn("[@notes.txt]", out)

    def test_lists_folder_ref(self):
        """An @folder/ reference is replaced with a directory listing."""
        os.makedirs(os.path.join(self.tmp, "docs"))
        self._write(os.path.join("docs", "a.txt"), "a")
        self._write(os.path.join("docs", "b.txt"), "b")
        out = expand_refs("check @docs/ now", base_dir=self.tmp)
        self.assertIn("- a.txt", out)
        self.assertIn("- b.txt", out)

    def test_missing_file_ref_left_unchanged(self):
        """A reference to a non-existent file is left as written."""
        text = "look at @does_not_exist.md here"
        out = expand_refs(text, base_dir=self.tmp)
        self.assertEqual(out, text)

    def test_email_address_not_treated_as_ref(self):
        """Email addresses must not be mangled as @-references."""
        text = "contact user@example.com for help"
        out = expand_refs(text, base_dir=self.tmp)
        self.assertEqual(out, text)

    def test_ref_at_start_of_text(self):
        """A reference at the very start of the string is expanded."""
        self._write("start.txt", "begins here")
        out = expand_refs("@start.txt", base_dir=self.tmp)
        self.assertIn("begins here", out)

    def test_large_file_is_truncated(self):
        """Files larger than the inline cap are truncated with a marker."""
        big = "x" * (9 * 1024)
        self._write("big.txt", big)
        out = expand_refs("@big.txt", base_dir=self.tmp)
        self.assertIn("truncated", out)
        self.assertLess(len(out), 9 * 1024 + 200)

    def test_empty_text_returns_unchanged(self):
        """Empty input is returned unchanged."""
        self.assertEqual(expand_refs("", base_dir=self.tmp), "")

    def test_directory_without_trailing_slash_is_listed(self):
        """A bare directory reference is also expanded to a listing."""
        os.makedirs(os.path.join(self.tmp, "sub"))
        self._write(os.path.join("sub", "f.txt"), "f")
        out = expand_refs("@sub", base_dir=self.tmp)
        self.assertIn("- f.txt", out)

    def test_multiple_refs_expanded(self):
        """Multiple references in one string are all expanded."""
        self._write("one.txt", "ONE")
        self._write("two.txt", "TWO")
        out = expand_refs("@one.txt and @two.txt", base_dir=self.tmp)
        self.assertIn("ONE", out)
        self.assertIn("TWO", out)


if __name__ == "__main__":
    unittest.main()
