"""Skill curator — spec section 4.7 (the curator pipeline).

The autonomous curator grades loaded skills against their real usage history,
detects near-duplicate skills and recommends which skills to keep, archive or
flag for human review. It depends only on the standard library: `difflib`
provides the textual-overlap measurement used for duplicate detection.

Usage stats are supplied externally as a mapping of skill slug -> dict with the
keys ``use_count``, ``success_count``, ``failure_count`` and ``age_days``.
"""

from __future__ import annotations

from difflib import SequenceMatcher

from .loader import Skill

# Default thresholds for the recommendation step. They are class attributes on
# SkillCurator so callers can tune them per instance, but live here as module
# constants for documentation purposes.
_KEEP_GRADE = 0.6
_ARCHIVE_GRADE = 0.3


class SkillCurator:
    """Grades skills, finds duplicates and recommends curation actions.

    The curator is stateless apart from its tuning thresholds; every method
    takes the skills and stats it needs as arguments so it can be reused
    across snapshots of the skill library.
    """

    def __init__(
        self,
        keep_grade: float = _KEEP_GRADE,
        archive_grade: float = _ARCHIVE_GRADE,
        duplicate_threshold: float = 0.8,
        recency_halflife_days: float = 30.0,
    ) -> None:
        """Configure the curation thresholds.

        Args:
            keep_grade: grades at or above this are recommended for "keep".
            archive_grade: grades below this (with no recent use) are archived.
            duplicate_threshold: textual-overlap ratio above which two skills
                count as duplicates.
            recency_halflife_days: age, in days, at which the recency component
                of a grade decays to 0.5.
        """
        self.keep_grade = keep_grade
        self.archive_grade = archive_grade
        self.duplicate_threshold = duplicate_threshold
        self.recency_halflife_days = recency_halflife_days

    # ------------------------------------------------------------------
    # Grading
    # ------------------------------------------------------------------
    def grade(
        self,
        skill: Skill,
        use_count: int,
        success_count: int,
        failure_count: int,
        age_days: float,
    ) -> float:
        """Compute a 0..1 quality score for a single skill.

        The score blends three signals:

        * **frequency** — how often the skill has been used, with diminishing
          returns (a skill used 10+ times is "frequently used").
        * **success rate** — successes divided by recorded outcomes; when there
          is no outcome history yet this defaults to a neutral 0.5.
        * **recency** — an exponential decay on ``age_days``; a freshly used
          skill scores near 1.0, an old one decays toward 0.

        Args:
            skill: the skill being graded (kept for API symmetry / future use).
            use_count: total number of times the skill was invoked.
            success_count: number of invocations that succeeded.
            failure_count: number of invocations that failed.
            age_days: days since the skill was last used (or created).

        Returns:
            A float clamped to the inclusive range [0.0, 1.0].
        """
        # Guard against negative or nonsensical inputs.
        use_count = max(0, use_count)
        success_count = max(0, success_count)
        failure_count = max(0, failure_count)
        age_days = max(0.0, float(age_days))

        # Frequency: saturates so the difference between 10 and 100 uses is
        # small, but the difference between 0 and 5 uses is large.
        frequency = min(1.0, use_count / 10.0)

        # Success rate: neutral 0.5 when there is no outcome history.
        outcomes = success_count + failure_count
        success_rate = success_count / outcomes if outcomes else 0.5

        # Recency: exponential half-life decay. At age == halflife the factor
        # is 0.5; at age 0 it is 1.0.
        recency = 0.5 ** (age_days / self.recency_halflife_days)

        # Weighted blend. Success rate is weighted highest because a skill that
        # fails is actively harmful; frequency and recency are secondary.
        score = 0.5 * success_rate + 0.3 * frequency + 0.2 * recency
        return _clamp(score)

    # ------------------------------------------------------------------
    # Duplicate detection
    # ------------------------------------------------------------------
    def find_duplicates(
        self, skills: list[Skill], threshold: float | None = None
    ) -> list[tuple[str, str]]:
        """Find pairs of skills whose content overlaps heavily.

        Every unordered pair of skills is compared with
        :class:`difflib.SequenceMatcher`. Pairs whose similarity ratio is at or
        above ``threshold`` are returned as ``(slug_a, slug_b)`` tuples.

        Args:
            skills: the skills to compare.
            threshold: overlap ratio in [0, 1]; defaults to the curator's
                configured ``duplicate_threshold``.

        Returns:
            A list of slug pairs, each pair ordered as encountered, with the
            overall list sorted for deterministic output.
        """
        if threshold is None:
            threshold = self.duplicate_threshold

        duplicates: list[tuple[str, str]] = []
        for i in range(len(skills)):
            for j in range(i + 1, len(skills)):
                a, b = skills[i], skills[j]
                # quick_ratio is a cheap upper bound; skip the expensive
                # ratio() call when even the optimistic estimate falls short.
                matcher = SequenceMatcher(None, a.content, b.content)
                if matcher.quick_ratio() < threshold:
                    continue
                if matcher.ratio() >= threshold:
                    duplicates.append((a.slug, b.slug))
        duplicates.sort()
        return duplicates

    # ------------------------------------------------------------------
    # Recommendation
    # ------------------------------------------------------------------
    def recommend(
        self, skills: list[Skill], stats: dict[str, dict]
    ) -> dict[str, list[str]]:
        """Produce a curation report categorising every skill.

        Each skill is graded, then sorted into one of three buckets:

        * **keep** — grade at or above ``keep_grade``.
        * **archive** — grade below ``archive_grade`` *and* the skill is
          effectively unused (no recorded uses).
        * **review** — everything else: mediocre skills, or low-grade skills
          that are still being used and therefore need a human decision.

        Args:
            skills: the skills to evaluate.
            stats: mapping of slug -> stats dict (see module docstring). Missing
                slugs are treated as having zero usage.

        Returns:
            A dict with the keys ``keep``, ``archive`` and ``review``, each
            mapping to a sorted list of skill slugs.
        """
        keep: list[str] = []
        archive: list[str] = []
        review: list[str] = []

        for skill in skills:
            st = stats.get(skill.slug, {})
            use_count = int(st.get("use_count", 0))
            grade = self.grade(
                skill,
                use_count=use_count,
                success_count=int(st.get("success_count", 0)),
                failure_count=int(st.get("failure_count", 0)),
                age_days=float(st.get("age_days", 0.0)),
            )
            if grade >= self.keep_grade:
                keep.append(skill.slug)
            elif grade < self.archive_grade and use_count == 0:
                archive.append(skill.slug)
            else:
                review.append(skill.slug)

        keep.sort()
        archive.sort()
        review.sort()
        return {"keep": keep, "archive": archive, "review": review}

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------
    def run(
        self, skills: list[Skill], stats: dict[str, dict]
    ) -> dict:
        """Run the full curation pipeline and return a complete report.

        Args:
            skills: the skills to curate.
            stats: mapping of slug -> stats dict (see module docstring).

        Returns:
            A report dict with keys:

            * ``total`` — number of skills examined.
            * ``grades`` — mapping of slug -> graded score.
            * ``duplicates`` — list of duplicate slug pairs.
            * ``recommendations`` — the ``recommend`` report (keep/archive/
              review).
        """
        grades: dict[str, float] = {}
        for skill in skills:
            st = stats.get(skill.slug, {})
            grades[skill.slug] = self.grade(
                skill,
                use_count=int(st.get("use_count", 0)),
                success_count=int(st.get("success_count", 0)),
                failure_count=int(st.get("failure_count", 0)),
                age_days=float(st.get("age_days", 0.0)),
            )

        return {
            "total": len(skills),
            "grades": grades,
            "duplicates": self.find_duplicates(skills),
            "recommendations": self.recommend(skills, stats),
        }


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp ``value`` into the inclusive range [low, high]."""
    return max(low, min(high, value))
