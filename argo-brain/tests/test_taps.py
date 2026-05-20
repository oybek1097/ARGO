"""Tests for the skill-tap system — spec section 4.7."""

import tempfile
import unittest
from pathlib import Path

from argo_brain.skills.loader import Skill
from argo_brain.skills.taps import (
    BundledTap,
    GitTap,
    LocalTap,
    SkillTap,
    TapRegistry,
)


def _skill_md(slug: str, name: str | None = None, body: str = "Do the thing.") -> str:
    """Build a minimal skill markdown document with frontmatter."""
    return (
        "---\n"
        f"name: {name or slug}\n"
        f"slug: {slug}\n"
        "trigger: do, thing\n"
        "category: general\n"
        "---\n"
        f"# {name or slug}\n\n{body}\n"
    )


def _write(directory: Path, filename: str, content: str) -> None:
    """Write a file inside `directory`, creating parents as needed."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / filename).write_text(content, encoding="utf-8")


class TestLocalTap(unittest.IsolatedAsyncioTestCase):
    """LocalTap loads skills from a local directory of .md files."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    async def test_loads_skills_from_directory(self):
        _write(self.dir, "a.md", _skill_md("alpha"))
        _write(self.dir, "b.md", _skill_md("beta"))
        tap = LocalTap(self.dir)
        skills = await tap.list_skills()
        self.assertEqual({s.slug for s in skills}, {"alpha", "beta"})

    async def test_is_a_skill_tap(self):
        tap = LocalTap(self.dir)
        self.assertIsInstance(tap, SkillTap)

    async def test_default_priority_is_high(self):
        # Local edits should win over bundled/community skills.
        tap = LocalTap(self.dir)
        self.assertGreater(tap.priority, BundledTap(self.dir).priority)

    async def test_empty_directory_yields_no_skills(self):
        tap = LocalTap(self.dir)
        self.assertEqual(await tap.list_skills(), [])

    async def test_missing_directory_handled(self):
        tap = LocalTap(self.dir / "does-not-exist")
        self.assertEqual(await tap.list_skills(), [])

    async def test_reflects_changes_on_relist(self):
        tap = LocalTap(self.dir)
        self.assertEqual(await tap.list_skills(), [])
        _write(self.dir, "a.md", _skill_md("alpha"))
        skills = await tap.list_skills()
        self.assertEqual([s.slug for s in skills], ["alpha"])


class TestBundledTap(unittest.IsolatedAsyncioTestCase):
    """BundledTap loads the skills bundled with ARGO."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    async def test_loads_bundled_skills(self):
        _write(self.dir, "core.md", _skill_md("core-skill"))
        tap = BundledTap(self.dir)
        skills = await tap.list_skills()
        self.assertEqual([s.slug for s in skills], ["core-skill"])

    async def test_lowest_priority_by_default(self):
        tap = BundledTap(self.dir)
        self.assertEqual(tap.priority, 0)

    async def test_missing_directory_handled(self):
        tap = BundledTap(self.dir / "nope")
        self.assertEqual(await tap.list_skills(), [])


class TestGitTap(unittest.IsolatedAsyncioTestCase):
    """GitTap loads skills from its local cache directory."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.cache = Path(self._tmp.name) / "cache"

    def tearDown(self):
        self._tmp.cleanup()

    async def test_loads_from_cache_dir(self):
        _write(self.cache, "shared.md", _skill_md("shared-skill"))
        tap = GitTap("https://github.com/argo/skills.git", self.cache)
        skills = await tap.list_skills()
        self.assertEqual([s.slug for s in skills], ["shared-skill"])

    async def test_missing_cache_dir_yields_no_skills(self):
        # The repo has not been cloned yet — no cache dir on disk.
        tap = GitTap("https://github.com/argo/skills.git", self.cache)
        self.assertEqual(await tap.list_skills(), [])

    async def test_name_derived_from_repo_url(self):
        tap = GitTap("https://github.com/argo/awesome-skills.git", self.cache)
        self.assertEqual(tap.name, "git:awesome-skills")

    async def test_explicit_name_overrides_derived(self):
        tap = GitTap("https://x/y.git", self.cache, name="community")
        self.assertEqual(tap.name, "community")

    async def test_priority_between_bundled_and_local(self):
        tap = GitTap("https://x/y.git", self.cache)
        self.assertLess(BundledTap(self.cache).priority, tap.priority)
        self.assertLess(tap.priority, LocalTap(self.cache).priority)


class TestTapRegistry(unittest.IsolatedAsyncioTestCase):
    """TapRegistry merges skills from multiple taps with priority dedup."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    async def test_merges_multiple_taps(self):
        bundled = self.root / "bundled"
        local = self.root / "local"
        _write(bundled, "b.md", _skill_md("bundled-only"))
        _write(local, "l.md", _skill_md("local-only"))
        reg = TapRegistry()
        reg.register(BundledTap(bundled))
        reg.register(LocalTap(local))
        slugs = [s.slug for s in await reg.all_skills()]
        self.assertEqual(slugs, ["bundled-only", "local-only"])

    async def test_higher_priority_tap_overrides_same_slug(self):
        bundled = self.root / "bundled"
        local = self.root / "local"
        _write(bundled, "x.md", _skill_md("shared", name="Bundled Version"))
        _write(local, "x.md", _skill_md("shared", name="Local Version"))
        reg = TapRegistry()
        reg.register(BundledTap(bundled))
        reg.register(LocalTap(local))
        skills = await reg.all_skills()
        self.assertEqual(len(skills), 1)
        # The high-priority LocalTap wins for the shared slug.
        self.assertEqual(skills[0].name, "Local Version")

    async def test_lower_priority_does_not_override(self):
        # Registration order must not matter — priority decides the winner.
        bundled = self.root / "bundled"
        local = self.root / "local"
        _write(bundled, "x.md", _skill_md("shared", name="Bundled Version"))
        _write(local, "x.md", _skill_md("shared", name="Local Version"))
        reg = TapRegistry()
        reg.register(LocalTap(local))      # registered first
        reg.register(BundledTap(bundled))  # registered last, lower priority
        skills = await reg.all_skills()
        self.assertEqual(skills[0].name, "Local Version")

    async def test_git_tap_overrides_bundled(self):
        bundled = self.root / "bundled"
        cache = self.root / "cache"
        _write(bundled, "x.md", _skill_md("shared", name="Bundled Version"))
        _write(cache, "x.md", _skill_md("shared", name="Git Version"))
        reg = TapRegistry()
        reg.register(BundledTap(bundled))
        reg.register(GitTap("https://x/y.git", cache))
        skills = await reg.all_skills()
        self.assertEqual(skills[0].name, "Git Version")

    async def test_taps_listed_by_priority(self):
        reg = TapRegistry()
        bundled = BundledTap(self.root / "b")
        git = GitTap("https://x/y.git", self.root / "c")
        local = LocalTap(self.root / "l")
        reg.register(git)
        reg.register(bundled)
        reg.register(local)
        # taps() returns highest priority first.
        self.assertEqual(reg.taps(), [local, git, bundled])

    async def test_empty_registry_yields_no_skills(self):
        reg = TapRegistry()
        self.assertEqual(await reg.all_skills(), [])
        self.assertEqual(reg.taps(), [])

    async def test_result_sorted_by_slug(self):
        d = self.root / "local"
        _write(d, "z.md", _skill_md("zeta"))
        _write(d, "a.md", _skill_md("alpha"))
        _write(d, "m.md", _skill_md("mu"))
        reg = TapRegistry()
        reg.register(LocalTap(d))
        slugs = [s.slug for s in await reg.all_skills()]
        self.assertEqual(slugs, ["alpha", "mu", "zeta"])

    async def test_three_tap_merge_with_overlaps(self):
        bundled = self.root / "bundled"
        cache = self.root / "cache"
        local = self.root / "local"
        # "common" exists in all three; each unique skill exists in one.
        _write(bundled, "c.md", _skill_md("common", name="from-bundled"))
        _write(bundled, "b.md", _skill_md("bundled-uniq"))
        _write(cache, "c.md", _skill_md("common", name="from-git"))
        _write(cache, "g.md", _skill_md("git-uniq"))
        _write(local, "c.md", _skill_md("common", name="from-local"))
        _write(local, "l.md", _skill_md("local-uniq"))
        reg = TapRegistry()
        reg.register(GitTap("https://x/y.git", cache))
        reg.register(BundledTap(bundled))
        reg.register(LocalTap(local))
        skills = {s.slug: s for s in await reg.all_skills()}
        self.assertEqual(
            set(skills),
            {"common", "bundled-uniq", "git-uniq", "local-uniq"},
        )
        # LocalTap has the highest priority and wins "common".
        self.assertEqual(skills["common"].name, "from-local")

    async def test_returns_skill_instances(self):
        d = self.root / "local"
        _write(d, "a.md", _skill_md("alpha"))
        reg = TapRegistry()
        reg.register(LocalTap(d))
        skills = await reg.all_skills()
        self.assertTrue(all(isinstance(s, Skill) for s in skills))


if __name__ == "__main__":
    unittest.main()
