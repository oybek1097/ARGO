"""Agent-workflow tools — spec section 4.4.

These tools let the agent manage its own execution flow: keep a per-user
todo list, ask the user clarifying questions, pace itself with short waits
and lay out an explicit plan. They rely only on the stdlib.
"""

from __future__ import annotations

import asyncio

from argo_brain.tools.base import Tool, ToolResult


class TodoTool(Tool):
    """Manage a per-user todo list — spec section 4.4.

    Lists are kept in an in-memory dict on the tool instance, keyed by
    `user_id`, so each user has an isolated set of items.
    """

    name = "todo"
    description = (
        "Manage a per-user todo list. action: add | list | complete | clear. "
        "For 'add' and 'complete' the 'item' argument names the task."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["add", "list", "complete", "clear"],
            },
            "item": {
                "type": "string",
                "description": "Task text (required for add/complete).",
            },
        },
        "required": ["action"],
    }

    def __init__(self) -> None:
        # user_id -> list of {"item": str, "done": bool}
        self._lists: dict[str, list[dict]] = {}

    def _format(self, items: list[dict]) -> str:
        """Render a todo list as a human-readable checklist."""
        if not items:
            return "(todo list is empty)"
        lines = []
        for idx, entry in enumerate(items, start=1):
            mark = "x" if entry["done"] else " "
            lines.append(f"{idx}. [{mark}] {entry['item']}")
        return "\n".join(lines)

    async def run(
        self, user_id: str, action: str = "", item: str = "", **kwargs
    ) -> ToolResult:
        items = self._lists.setdefault(user_id, [])

        if action == "add":
            if not item:
                return ToolResult(
                    content="An 'item' is required to add a todo.", success=False
                )
            items.append({"item": item, "done": False})
            return ToolResult(content=f"Added todo: {item}")

        if action == "list":
            return ToolResult(content=self._format(items))

        if action == "complete":
            if not item:
                return ToolResult(
                    content="An 'item' is required to complete a todo.",
                    success=False,
                )
            for entry in items:
                if entry["item"] == item:
                    entry["done"] = True
                    return ToolResult(content=f"Completed todo: {item}")
            return ToolResult(content=f"Todo not found: {item}", success=False)

        if action == "clear":
            self._lists[user_id] = []
            return ToolResult(content="Todo list cleared.")

        return ToolResult(content=f"Unknown action: {action}", success=False)


class ClarifyTool(Tool):
    """Ask the user a clarifying question — spec section 4.4.

    The agent calls this when the request is ambiguous; the question is
    returned formatted as a clarification request for the user.
    """

    name = "clarify"
    description = "Ask the user a clarifying question when the request is ambiguous."
    parameters = {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The clarifying question to ask the user.",
            }
        },
        "required": ["question"],
    }

    async def run(self, user_id: str, question: str = "", **kwargs) -> ToolResult:
        if not question:
            return ToolResult(
                content="A 'question' is required to ask for clarification.",
                success=False,
            )
        return ToolResult(
            content=f"[Clarification needed] {question}",
            metadata={"clarification": True, "question": question},
        )


class WaitTool(Tool):
    """Pause execution for a short while — spec section 4.4.

    Useful for pacing (e.g. waiting between polling attempts). The wait is
    capped at 10 seconds to avoid blocking the agent loop for too long.
    """

    name = "wait"
    description = "Pause for a number of seconds (capped at 10) to pace the agent."
    parameters = {
        "type": "object",
        "properties": {
            "seconds": {
                "type": "number",
                "description": "Seconds to wait; values above 10 are capped.",
            }
        },
        "required": ["seconds"],
    }
    _MAX_SECONDS = 10

    async def run(self, user_id: str, seconds: float = 0, **kwargs) -> ToolResult:
        try:
            requested = float(seconds)
        except (TypeError, ValueError):
            return ToolResult(content=f"Invalid seconds: {seconds}", success=False)
        # Clamp to the [0, _MAX_SECONDS] range.
        waited = max(0.0, min(requested, float(self._MAX_SECONDS)))
        await asyncio.sleep(waited)
        return ToolResult(
            content=f"Waited {waited} second(s).",
            metadata={"requested": requested, "waited": waited},
        )


class PlanTool(Tool):
    """Lay out an explicit numbered plan — spec section 4.4.

    The agent records the steps it intends to take; the formatted plan is
    returned and stored per-user on the tool instance.
    """

    name = "plan"
    description = "Record an explicit numbered plan of steps for the current task."
    parameters = {
        "type": "object",
        "properties": {
            "steps": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Ordered list of step descriptions.",
            }
        },
        "required": ["steps"],
    }

    def __init__(self) -> None:
        # user_id -> most recent plan (list of step strings)
        self._plans: dict[str, list[str]] = {}

    async def run(self, user_id: str, steps=None, **kwargs) -> ToolResult:
        if not steps or not isinstance(steps, (list, tuple)):
            return ToolResult(
                content="A non-empty list of 'steps' is required.", success=False
            )
        clean_steps = [str(step) for step in steps]
        self._plans[user_id] = clean_steps
        body = "\n".join(
            f"{idx}. {step}" for idx, step in enumerate(clean_steps, start=1)
        )
        return ToolResult(content=f"Plan:\n{body}")


def workflow_tools() -> list[Tool]:
    """List of the agent-workflow tools — spec section 4.4."""
    return [TodoTool(), ClarifyTool(), WaitTool(), PlanTool()]
