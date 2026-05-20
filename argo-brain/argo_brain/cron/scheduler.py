"""Cron scheduler — spec section 4.13.

A lightweight in-process scheduler. The skeleton supports interval and
daily-time schedules plus a small natural-language parser. The full
APScheduler-backed engine with delivery routing and `no_agent` mode arrives
in a later sprint; `CronJob` already carries the fields for it.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

_UNIT_SECONDS = {
    "second": 1, "seconds": 1, "sekund": 1,
    "minute": 60, "minutes": 60, "daqiqa": 60,
    "hour": 3600, "hours": 3600, "soat": 3600,
    "day": 86400, "days": 86400, "kun": 86400,
}
_EVERY_RE = re.compile(r"every\s+(?:(\d+)\s+)?(\w+)", re.IGNORECASE)
_AT_RE = re.compile(r"at\s+(\d{1,2}):(\d{2})", re.IGNORECASE)


def parse_schedule(text: str) -> dict:
    """Parses a natural-language schedule into a structured descriptor.

    Returns one of:
      * ``{"interval": <seconds>}``         — recurring interval
      * ``{"daily_at": "HH:MM"}``           — once per day at a wall-clock time
      * ``{"raw": <text>}``                 — unparsed (cron expr, future work)
    """
    low = text.strip().lower()

    at = _AT_RE.search(low)
    if at and ("daily" in low or "every day" in low or "har kuni" in low or
               low.startswith("at ")):
        return {"daily_at": f"{int(at.group(1)):02d}:{at.group(2)}"}

    every = _EVERY_RE.search(low)
    if every:
        count = int(every.group(1)) if every.group(1) else 1
        unit = every.group(2)
        if unit in _UNIT_SECONDS:
            return {"interval": count * _UNIT_SECONDS[unit]}

    return {"raw": text}


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class CronJob:
    """A scheduled job."""

    name: str
    schedule: dict
    prompt: str = ""
    enabled: bool = True
    delivery_target: str | None = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    next_run_at: datetime | None = None
    run_count: int = 0

    def compute_next(self, after: datetime | None = None) -> datetime | None:
        """Computes the next run time given the schedule descriptor."""
        base = after or _now()
        if "interval" in self.schedule:
            return base + timedelta(seconds=self.schedule["interval"])
        if "daily_at" in self.schedule:
            hh, mm = (int(x) for x in self.schedule["daily_at"].split(":"))
            candidate = base.replace(hour=hh, minute=mm, second=0, microsecond=0)
            if candidate <= base:
                candidate += timedelta(days=1)
            return candidate
        return None  # unparsed schedules never fire (skeleton)


class CronScheduler:
    """Holds cron jobs and reports which ones are due."""

    def __init__(self) -> None:
        self._jobs: dict[str, CronJob] = {}

    def add(self, name: str, schedule: str | dict, prompt: str = "",
            delivery_target: str | None = None) -> CronJob:
        desc = parse_schedule(schedule) if isinstance(schedule, str) else schedule
        job = CronJob(
            name=name, schedule=desc, prompt=prompt,
            delivery_target=delivery_target,
        )
        job.next_run_at = job.compute_next()
        self._jobs[job.id] = job
        return job

    def remove(self, job_id: str) -> bool:
        return self._jobs.pop(job_id, None) is not None

    def list(self) -> list[CronJob]:
        return list(self._jobs.values())

    def due(self, at: datetime | None = None) -> list[CronJob]:
        """Returns enabled jobs whose `next_run_at` has passed."""
        now = at or _now()
        return [
            j for j in self._jobs.values()
            if j.enabled and j.next_run_at is not None and j.next_run_at <= now
        ]

    def mark_ran(self, job: CronJob, at: datetime | None = None) -> None:
        """Records a run and reschedules the job."""
        now = at or _now()
        job.run_count += 1
        job.next_run_at = job.compute_next(now)
