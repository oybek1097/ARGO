"""Unit tests for the skill curator (spec section 4.7)."""

import unittest

from argo_brain.skills.curator import SkillCurator
from argo_brain.skills.loader import Skill


def _skill(slug: str, content: str = "do something useful") -> Skill:
    """Build a Skill with sensible defaults for testing."""
    return Skill(
        name=slug.replace("-", " ").title(),
        slug=slug,
        content=content,
        trigger=[slug],
        category="general",
    )


class GradeTests(unittest.TestCase):
    """Tests for SkillCurator.grade()."""

    def setUp(self):
        self.curator = SkillCurator()

    def test_grade_in_unit_range(self):
        s = _skill("a")
        g = self.curator.grade(s, use_count=5, success_count=3,
                               failure_count=2, age_days=10)
        self.assertGreaterEqual(g, 0.0)
        self.assertLessEqual(g, 1.0)

    def test_frequent_successful_beats_rare_failing(self):
        s = _skill("a")
        good = self.curator.grade(s, use_count=50, success_count=48,
                                  failure_count=2, age_days=1)
        bad = self.curator.grade(s, use_count=1, success_count=0,
                                 failure_count=1, age_days=200)
        self.assertGreater(good, bad)

    def test_higher_success_rate_scores_higher(self):
        s = _skill("a")
        high = self.curator.grade(s, use_count=10, success_count=10,
                                  failure_count=0, age_days=5)
        low = self.curator.grade(s, use_count=10, success_count=2,
                                 failure_count=8, age_days=5)
        self.assertGreater(high, low)

    def test_recency_decays_grade(self):
        s = _skill("a")
        fresh = self.curator.grade(s, use_count=10, success_count=8,
                                   failure_count=2, age_days=0)
        stale = self.curator.grade(s, use_count=10, success_count=8,
                                   failure_count=2, age_days=300)
        self.assertGreater(fresh, stale)

    def test_no_outcomes_uses_neutral_success_rate(self):
        # A skill with zero recorded outcomes should still grade reasonably,
        # not collapse to zero.
        s = _skill("a")
        g = self.curator.grade(s, use_count=0, success_count=0,
                               failure_count=0, age_days=0)
        self.assertGreater(g, 0.0)

    def test_negative_inputs_are_tolerated(self):
        s = _skill("a")
        g = self.curator.grade(s, use_count=-5, success_count=-1,
                               failure_count=-1, age_days=-10)
        self.assertGreaterEqual(g, 0.0)
        self.assertLessEqual(g, 1.0)


class FindDuplicatesTests(unittest.TestCase):
    """Tests for SkillCurator.find_duplicates()."""

    def setUp(self):
        self.curator = SkillCurator()

    def test_detects_near_identical_content(self):
        body = "Deploy the service to the cluster using kubectl apply." * 3
        a = _skill("deploy-one", body)
        b = _skill("deploy-two", body + " Also verify rollout.")
        dups = self.curator.find_duplicates([a, b])
        self.assertIn(("deploy-one", "deploy-two"), dups)

    def test_ignores_distinct_content(self):
        a = _skill("send-email", "Compose and send an email via SMTP.")
        b = _skill("parse-logs", "Tail and grep production log files.")
        dups = self.curator.find_duplicates([a, b])
        self.assertEqual(dups, [])

    def test_identical_content_is_duplicate(self):
        body = "The exact same instructions for both skills here."
        a = _skill("alpha", body)
        b = _skill("beta", body)
        dups = self.curator.find_duplicates([a, b])
        self.assertEqual(dups, [("alpha", "beta")])

    def test_threshold_argument_controls_sensitivity(self):
        a = _skill("x", "shared opening text. unique tail aaa.")
        b = _skill("y", "shared opening text. unique tail bbbbbbbbb.")
        loose = self.curator.find_duplicates([a, b], threshold=0.3)
        strict = self.curator.find_duplicates([a, b], threshold=0.99)
        self.assertIn(("x", "y"), loose)
        self.assertEqual(strict, [])

    def test_empty_list_returns_no_duplicates(self):
        self.assertEqual(self.curator.find_duplicates([]), [])


class RecommendTests(unittest.TestCase):
    """Tests for SkillCurator.recommend()."""

    def setUp(self):
        self.curator = SkillCurator()

    def test_archives_low_grade_unused_skill(self):
        skill = _skill("dead-skill")
        stats = {"dead-skill": {"use_count": 0, "success_count": 0,
                                "failure_count": 0, "age_days": 365}}
        report = self.curator.recommend([skill], stats)
        self.assertIn("dead-skill", report["archive"])

    def test_keeps_high_grade_skill(self):
        skill = _skill("star-skill")
        stats = {"star-skill": {"use_count": 80, "success_count": 78,
                                "failure_count": 2, "age_days": 1}}
        report = self.curator.recommend([skill], stats)
        self.assertIn("star-skill", report["keep"])

    def test_missing_stats_treated_as_unused(self):
        skill = _skill("orphan", "tiny body")
        report = self.curator.recommend([skill], stats={})
        # No stats -> age 0, neutral success -> not archived, lands in review.
        self.assertIn("orphan", report["review"])
        self.assertNotIn("orphan", report["archive"])

    def test_report_buckets_partition_all_skills(self):
        skills = [_skill("a"), _skill("b", "different"), _skill("c", "more")]
        stats = {
            "a": {"use_count": 80, "success_count": 80,
                  "failure_count": 0, "age_days": 1},
            "b": {"use_count": 0, "success_count": 0,
                  "failure_count": 0, "age_days": 400},
            "c": {"use_count": 3, "success_count": 1,
                  "failure_count": 2, "age_days": 50},
        }
        report = self.curator.recommend(skills, stats)
        all_slugs = (report["keep"] + report["archive"] + report["review"])
        self.assertCountEqual(all_slugs, ["a", "b", "c"])


class RunTests(unittest.TestCase):
    """Tests for SkillCurator.run()."""

    def setUp(self):
        self.curator = SkillCurator()

    def test_run_returns_full_report(self):
        skills = [_skill("a"), _skill("b", "completely separate content")]
        stats = {
            "a": {"use_count": 40, "success_count": 38,
                  "failure_count": 2, "age_days": 2},
            "b": {"use_count": 0, "success_count": 0,
                  "failure_count": 0, "age_days": 500},
        }
        report = self.curator.run(skills, stats)
        self.assertEqual(report["total"], 2)
        self.assertEqual(set(report["grades"]), {"a", "b"})
        self.assertIn("recommendations", report)
        self.assertEqual(report["duplicates"], [])

    def test_run_includes_duplicate_pairs(self):
        body = "Identical instructions repeated for the duplicate test case."
        skills = [_skill("dup-a", body), _skill("dup-b", body)]
        report = self.curator.run(skills, {})
        self.assertIn(("dup-a", "dup-b"), report["duplicates"])

    def test_run_grades_match_recommendations(self):
        skill = _skill("solo")
        stats = {"solo": {"use_count": 90, "success_count": 90,
                          "failure_count": 0, "age_days": 0}}
        report = self.curator.run([skill], stats)
        self.assertGreaterEqual(report["grades"]["solo"],
                                self.curator.keep_grade)
        self.assertIn("solo", report["recommendations"]["keep"])


if __name__ == "__main__":
    unittest.main()
