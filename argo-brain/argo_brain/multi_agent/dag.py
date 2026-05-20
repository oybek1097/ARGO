"""DAG-based task workflow — spec section 4.11.

:class:`DAGWorkflow` lets callers describe a set of agent tasks together with
their dependencies. ``run`` executes the tasks in topological order: a task
starts only after every task it depends on has finished, and tasks that have
no pending dependencies run concurrently. Dependency cycles are detected up
front and reported with a clear error.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from argo_brain.core.agent import AgentCore, AgentRequest


class DAGCycleError(ValueError):
    """Raised when the workflow's dependency graph contains a cycle."""


@dataclass
class _DAGTask:
    """A single node in the workflow graph."""

    id: str
    prompt: str
    depends_on: list[str] = field(default_factory=list)


class DAGWorkflow:
    """A directed-acyclic graph of dependent agent tasks."""

    def __init__(self) -> None:
        # Insertion-ordered mapping of task id -> task definition.
        self._tasks: dict[str, _DAGTask] = {}

    def add_task(
        self,
        task_id: str,
        prompt: str,
        depends_on: list[str] | None = None,
    ) -> None:
        """Register a task in the workflow.

        Args:
            task_id: Unique identifier for the task.
            prompt: The prompt that will be sent to the agent.
            depends_on: Ids of tasks that must finish before this one runs.

        Raises:
            ValueError: If ``task_id`` is empty or already registered.
        """
        if not task_id:
            raise ValueError("task_id must be a non-empty string")
        if task_id in self._tasks:
            raise ValueError(f"duplicate task id: {task_id}")
        self._tasks[task_id] = _DAGTask(
            id=task_id,
            prompt=prompt,
            depends_on=list(depends_on or []),
        )

    def _topological_order(self) -> list[list[str]]:
        """Group task ids into dependency-ordered execution levels.

        Each level is a list of task ids that may run concurrently because
        all of their dependencies belong to earlier levels.

        Returns:
            A list of levels (lists of task ids).

        Raises:
            ValueError: If a dependency references an unknown task.
            DAGCycleError: If the graph contains a cycle.
        """
        # Validate dependency references first.
        for task in self._tasks.values():
            for dep in task.depends_on:
                if dep not in self._tasks:
                    raise ValueError(
                        f"task '{task.id}' depends on unknown task '{dep}'"
                    )

        # Kahn's algorithm: repeatedly peel off tasks with no unmet deps.
        remaining = {
            tid: set(task.depends_on) for tid, task in self._tasks.items()
        }
        levels: list[list[str]] = []

        while remaining:
            ready = sorted(
                tid for tid, deps in remaining.items() if not deps
            )
            if not ready:
                # No task is free of dependencies -> a cycle exists.
                stuck = ", ".join(sorted(remaining))
                raise DAGCycleError(
                    f"dependency cycle detected among tasks: {stuck}"
                )
            levels.append(ready)
            for tid in ready:
                del remaining[tid]
            # Clear the satisfied dependencies from the rest.
            for deps in remaining.values():
                deps.difference_update(ready)

        return levels

    async def run(self, agent: AgentCore) -> dict[str, str]:
        """Execute every task in dependency order.

        Tasks within the same topological level run concurrently. The prompt
        of each task is sent to ``agent`` with an isolated ``user_id`` so the
        tasks do not share conversation context.

        Args:
            agent: The :class:`AgentCore` used to process the tasks.

        Returns:
            A mapping of ``task_id`` to the agent's result string.

        Raises:
            DAGCycleError: If the dependency graph contains a cycle.
            ValueError: If a task depends on an unknown task.
        """
        levels = self._topological_order()
        results: dict[str, str] = {}

        for level in levels:

            async def _run(task_id: str) -> tuple[str, str]:
                task = self._tasks[task_id]
                req = AgentRequest(
                    user_id=f"dag-{task_id}",
                    message=task.prompt,
                )
                resp = await agent.process(req)
                return task_id, resp.content

            # All tasks in this level are independent -> run concurrently.
            level_results = await asyncio.gather(
                *(_run(tid) for tid in level)
            )
            for task_id, content in level_results:
                results[task_id] = content

        return results
