"""Skill loader — spec section 4.7.

Loads agentskills.io-compatible markdown skills. Each skill is a `.md` file
with a YAML-style frontmatter block:

    ---
    name: deploy-k8s
    trigger: deploy, kubernetes, k8s
    category: devops
    ---
    # Deploy to Kubernetes
    ... instructions ...

The skeleton parses the frontmatter without a YAML dependency. The autonomous
curator (grading, consolidate, archive) arrives in Sprint 3.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Skill:
    """A single loaded skill."""

    name: str
    slug: str
    content: str
    trigger: list[str] = field(default_factory=list)
    category: str = "general"

    def matches(self, text: str) -> bool:
        """True if any trigger keyword occurs in `text`."""
        low = text.lower()
        return any(kw and kw in low for kw in self.trigger)


def _parse_frontmatter(raw: str) -> tuple[dict[str, str], str]:
    """Splits a `--- ... ---` frontmatter block from the markdown body."""
    if not raw.startswith("---"):
        return {}, raw
    end = raw.find("\n---", 3)
    if end == -1:
        return {}, raw
    header = raw[3:end].strip()
    body = raw[end + 4:].lstrip("\n")
    meta: dict[str, str] = {}
    for line in header.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip().lower()] = value.strip()
    return meta, body


class SkillLoader:
    """Discovers and serves skills from one or more directories."""

    def __init__(self, *directories: Path | str) -> None:
        self._dirs = [Path(d).expanduser() for d in directories]
        self._skills: dict[str, Skill] = {}

    def load(self) -> int:
        """(Re)scans the directories. Returns the number of skills loaded."""
        self._skills.clear()
        for directory in self._dirs:
            if not directory.is_dir():
                continue
            for md in sorted(directory.glob("*.md")):
                skill = self._parse_file(md)
                if skill:
                    self._skills[skill.slug] = skill
        return len(self._skills)

    @staticmethod
    def _parse_file(path: Path) -> Skill | None:
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError:
            return None
        meta, body = _parse_frontmatter(raw)
        slug = meta.get("slug") or meta.get("name") or path.stem
        triggers = [
            t.strip().lower()
            for t in meta.get("trigger", "").split(",")
            if t.strip()
        ]
        return Skill(
            name=meta.get("name", path.stem),
            slug=slug,
            content=body.strip(),
            trigger=triggers,
            category=meta.get("category", "general"),
        )

    def all(self) -> list[Skill]:
        return list(self._skills.values())

    def get(self, slug: str) -> Skill | None:
        return self._skills.get(slug)

    def get_relevant(self, query: str, limit: int = 3) -> list[Skill]:
        """Returns skills whose trigger keywords match the query."""
        matched = [s for s in self._skills.values() if s.matches(query)]
        return matched[:limit]
