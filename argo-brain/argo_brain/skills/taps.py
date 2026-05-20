"""Skill taps — spec section 4.7 (multiple skill sources).

A *tap* is a source of skills. ARGO can draw skills from several places at
once: a local working directory the operator edits by hand, the read-only set
bundled with the ARGO distribution, and git repositories of community skills
cloned into a local cache.

Each tap exposes the same async interface so the :class:`TapRegistry` can merge
them. When two taps provide a skill with the same ``slug`` the skill from the
tap with the higher :attr:`SkillTap.priority` wins; this lets an operator's
local edits override a community or bundled skill of the same name.

The module depends only on the standard library. Git itself is intentionally
*not* invoked here: :class:`GitTap` simply reads whatever ``.md`` files already
exist in its cache directory, which keeps the class trivially testable and
leaves the actual ``git clone``/``git pull`` to an outer orchestration layer.
"""

from __future__ import annotations

import abc
from pathlib import Path

from .loader import Skill, SkillLoader


class SkillTap(abc.ABC):
    """Abstract base class for a skill source — spec section 4.7.

    A tap has a human-readable :attr:`name`, an integer :attr:`priority`
    (higher wins during deduplication) and an async :meth:`list_skills` method
    that yields the skills currently available from the source.
    """

    #: Higher-priority taps override lower-priority ones for the same slug.
    priority: int = 0

    #: Human-readable identifier for the tap.
    name: str = "tap"

    @abc.abstractmethod
    async def list_skills(self) -> list[Skill]:
        """Return the skills currently available from this tap."""
        raise NotImplementedError

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"{type(self).__name__}(name={self.name!r}, priority={self.priority})"


class LocalTap(SkillTap):
    """A tap backed by a local directory of ``.md`` skills — spec section 4.7.

    Wraps a :class:`~argo_brain.skills.loader.SkillLoader`. This is the tap an
    operator edits directly, so it defaults to a high priority so hand-written
    skills override bundled or community ones.
    """

    def __init__(
        self,
        directory: Path | str,
        name: str = "local",
        priority: int = 100,
    ) -> None:
        """Create a local tap.

        Args:
            directory: directory scanned for ``*.md`` skill files.
            name: human-readable tap name.
            priority: dedup priority; defaults high so local edits win.
        """
        self.name = name
        self.priority = priority
        self.directory = Path(directory).expanduser()
        # Each tap owns its own loader so re-scans are isolated.
        self._loader = SkillLoader(self.directory)

    async def list_skills(self) -> list[Skill]:
        """Load and return skills from the local directory.

        A missing directory is handled gracefully by the underlying loader,
        which simply skips directories that do not exist.
        """
        self._loader.load()
        return self._loader.all()


class BundledTap(SkillTap):
    """A tap for the skills shipped with ARGO — spec section 4.7.

    These are the curated defaults distributed inside the ARGO package. They
    sit at the *lowest* priority so any local or community skill of the same
    slug takes precedence.
    """

    def __init__(
        self,
        directory: Path | str,
        name: str = "bundled",
        priority: int = 0,
    ) -> None:
        """Create a bundled tap.

        Args:
            directory: directory containing the bundled ``*.md`` skills.
            name: human-readable tap name.
            priority: dedup priority; defaults to ``0`` (lowest).
        """
        self.name = name
        self.priority = priority
        self.directory = Path(directory).expanduser()
        self._loader = SkillLoader(self.directory)

    async def list_skills(self) -> list[Skill]:
        """Load and return the bundled skills."""
        self._loader.load()
        return self._loader.all()


class GitTap(SkillTap):
    """A tap for a git-hosted skill repository — spec section 4.7.

    Represents a community skill repo identified by its ``repo_url`` and cloned
    into ``cache_dir`` by an outer layer. This class never shells out to git:
    :meth:`list_skills` only loads whatever ``.md`` files are already present
    in the cache directory, so it is fully deterministic and easy to test. If
    the cache directory is missing (the repo has not been cloned yet) it simply
    yields no skills.
    """

    def __init__(
        self,
        repo_url: str,
        cache_dir: Path | str,
        name: str | None = None,
        priority: int = 50,
    ) -> None:
        """Create a git tap.

        Args:
            repo_url: the upstream repository URL (informational only here).
            cache_dir: local directory the repo is/will be cloned into.
            name: human-readable tap name; defaults to a name derived from the
                repo URL.
            priority: dedup priority; defaults to ``50`` — above bundled,
                below local.
        """
        self.repo_url = repo_url
        self.cache_dir = Path(cache_dir).expanduser()
        # Derive a friendly name from the repo URL when none is supplied.
        self.name = name or self._name_from_url(repo_url)
        self.priority = priority
        self._loader = SkillLoader(self.cache_dir)

    @staticmethod
    def _name_from_url(repo_url: str) -> str:
        """Derive a tap name from a repo URL (last path segment, no .git)."""
        tail = repo_url.rstrip("/").rsplit("/", 1)[-1]
        if tail.endswith(".git"):
            tail = tail[:-4]
        return f"git:{tail}" if tail else "git:repo"

    async def list_skills(self) -> list[Skill]:
        """Load skills from the local cache directory.

        Returns an empty list when the cache directory does not exist yet
        (i.e. the repository has not been cloned).
        """
        if not self.cache_dir.is_dir():
            return []
        self._loader.load()
        return self._loader.all()


class TapRegistry:
    """Registry that merges skills from multiple taps — spec section 4.7.

    Taps are registered in any order; :meth:`all_skills` merges them with
    priority-based deduplication so a higher-priority tap's skill overrides a
    lower-priority tap's skill that shares the same slug.
    """

    def __init__(self) -> None:
        self._taps: list[SkillTap] = []

    def register(self, tap: SkillTap) -> None:
        """Register a tap as a skill source."""
        self._taps.append(tap)

    def taps(self) -> list[SkillTap]:
        """Return the registered taps, ordered by priority (highest first)."""
        return sorted(self._taps, key=lambda t: t.priority, reverse=True)

    async def all_skills(self) -> list[Skill]:
        """Merge skills from every tap with priority-based deduplication.

        Each tap is queried for its skills. When two taps contribute a skill
        with the same ``slug``, the skill from the tap with the higher
        :attr:`SkillTap.priority` wins. Taps are processed from lowest to
        highest priority so that higher-priority skills simply overwrite
        earlier entries in the result map.

        Returns:
            The merged skills, sorted by slug for deterministic output.
        """
        merged: dict[str, Skill] = {}
        # Ascending priority: later (higher-priority) writes overwrite earlier
        # (lower-priority) ones for a shared slug.
        for tap in sorted(self._taps, key=lambda t: t.priority):
            for skill in await tap.list_skills():
                merged[skill.slug] = skill
        return [merged[slug] for slug in sorted(merged)]
