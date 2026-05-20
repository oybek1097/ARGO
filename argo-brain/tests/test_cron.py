"""Cron scheduler tests."""

import unittest
from datetime import datetime, timezone

from argo_brain.cron import CronScheduler, parse_schedule


class TestParseSchedule(unittest.TestCase):
    def test_interval_minutes(self):
        self.assertEqual(parse_schedule("every 5 minutes"), {"interval": 300})

    def test_interval_single_unit(self):
        self.assertEqual(parse_schedule("every hour"), {"interval": 3600})

    def test_daily_at(self):
        self.assertEqual(
            parse_schedule("every day at 9:30"), {"daily_at": "09:30"}
        )

    def test_unparsed_falls_back_to_raw(self):
        result = parse_schedule("0 0 * * 1")
        self.assertIn("raw", result)


class TestCronScheduler(unittest.TestCase):
    def setUp(self):
        self.sched = CronScheduler()

    def test_add_job_computes_next_run(self):
        job = self.sched.add("hourly", "every hour", prompt="check")
        self.assertIsNotNone(job.next_run_at)

    def test_due_returns_passed_jobs(self):
        job = self.sched.add("fast", {"interval": 60})
        # force the job into the past
        job.next_run_at = datetime(2000, 1, 1, tzinfo=timezone.utc)
        self.assertIn(job, self.sched.due())

    def test_mark_ran_reschedules(self):
        job = self.sched.add("fast", {"interval": 60})
        first = job.next_run_at
        self.sched.mark_ran(job)
        self.assertEqual(job.run_count, 1)
        self.assertNotEqual(job.next_run_at, first)

    def test_remove_job(self):
        job = self.sched.add("temp", {"interval": 10})
        self.assertTrue(self.sched.remove(job.id))
        self.assertEqual(self.sched.list(), [])

    def test_disabled_job_not_due(self):
        job = self.sched.add("off", {"interval": 60})
        job.enabled = False
        job.next_run_at = datetime(2000, 1, 1, tzinfo=timezone.utc)
        self.assertNotIn(job, self.sched.due())


if __name__ == "__main__":
    unittest.main()
