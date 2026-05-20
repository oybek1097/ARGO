"""Skill loader tests."""

import tempfile
import unittest
from pathlib import Path

from argo_brain.skills import SkillLoader

_SKILL_MD = """\
---
name: Deploy to Kubernetes
slug: deploy-k8s
trigger: deploy, kubernetes, k8s
category: devops
---
# Deploy to Kubernetes

Verify the cluster context, then apply the manifests.
"""

_NO_FRONTMATTER = "# Plain note\n\nJust some text, no frontmatter.\n"


class TestSkillLoader(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        d = Path(self._tmp.name)
        (d / "deploy.md").write_text(_SKILL_MD, encoding="utf-8")
        (d / "note.md").write_text(_NO_FRONTMATTER, encoding="utf-8")
        self.loader = SkillLoader(d)
        self.loader.load()

    def tearDown(self):
        self._tmp.cleanup()

    def test_loads_all_files(self):
        self.assertEqual(len(self.loader.all()), 2)

    def test_frontmatter_parsed(self):
        skill = self.loader.get("deploy-k8s")
        self.assertIsNotNone(skill)
        self.assertEqual(skill.name, "Deploy to Kubernetes")
        self.assertEqual(skill.category, "devops")
        self.assertIn("kubernetes", skill.trigger)
        self.assertIn("apply the manifests", skill.content)

    def test_missing_frontmatter_defaults(self):
        skill = self.loader.get("note")
        self.assertIsNotNone(skill)
        self.assertEqual(skill.category, "general")
        self.assertEqual(skill.trigger, [])

    def test_get_relevant_matches_trigger(self):
        hits = self.loader.get_relevant("please deploy the app to k8s")
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].slug, "deploy-k8s")

    def test_get_relevant_no_match(self):
        self.assertEqual(self.loader.get_relevant("write me a poem"), [])


if __name__ == "__main__":
    unittest.main()
