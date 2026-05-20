"""A richer, stdlib-only terminal UI for the ARGO brain.

This module provides two pieces:

* ``SlashCommandRouter`` — a pure, testable parser for slash commands
  (``/help``, ``/clear``, ``/history``, ``/tools``, ``/model``, ``/exit``).
  It performs no terminal IO so it can be unit-tested in isolation.
* ``TUI`` — an async ``run(agent)`` loop that reads user input, renders a
  status line (model + message count), routes slash commands through the
  router and otherwise forwards the line to ``agent.process``. It keeps an
  in-memory command history.
"""

from __future__ import annotations

import asyncio
from typing import Any

from argo_brain.core import AgentRequest

# A sentinel returned by the router to ask the TUI loop to terminate.
EXIT_SIGNAL = "__ARGO_TUI_EXIT__"

# ANSI helpers — kept tiny and optional; they degrade gracefully because
# any terminal that does not understand them simply prints the codes.
_DIM = "\x1b[2m"
_BOLD = "\x1b[1m"
_RESET = "\x1b[0m"


class SlashCommandRouter:
    """Parses and executes slash commands.

    The router is intentionally free of terminal IO: every command returns a
    plain string (the text to display). ``handle`` returns ``None`` when the
    input line is *not* a slash command, signalling the caller to treat the
    line as a normal chat message.
    """

    #: The set of commands the router understands, with one-line help text.
    COMMANDS: dict[str, str] = {
        "/help": "show this help message",
        "/clear": "clear the in-memory command history",
        "/history": "show the in-memory command history",
        "/tools": "list the tools available to the agent",
        "/model": "show the active LLM model",
        "/exit": "leave the TUI",
    }

    def __init__(self) -> None:
        # The command history is shared with the TUI; the router both reads it
        # (for /history) and clears it (for /clear).
        self.history: list[str] = []

    # -- helpers ---------------------------------------------------------

    def is_slash_command(self, line: str) -> bool:
        """Returns True when ``line`` starts with a slash command token."""
        return line.strip().startswith("/")

    def help_text(self) -> str:
        """Renders the multi-line help block for ``/help``."""
        lines = ["Available commands:"]
        for name, desc in self.COMMANDS.items():
            lines.append(f"  {name:<10s} {desc}")
        return "\n".join(lines)

    def tools_text(self, agent: Any) -> str:
        """Renders the tool list for ``/tools`` from the agent's registry."""
        names = sorted(agent.registry.names())
        if not names:
            return "No tools registered."
        lines = [f"Tools ({len(names)}):"]
        lines.extend(f"  - {name}" for name in names)
        return "\n".join(lines)

    def history_text(self) -> str:
        """Renders the in-memory command history for ``/history``."""
        if not self.history:
            return "History is empty."
        lines = ["Command history:"]
        lines.extend(f"  {i:>3d}  {item}" for i, item in enumerate(self.history, 1))
        return "\n".join(lines)

    # -- dispatch --------------------------------------------------------

    def handle(self, line: str, agent: Any) -> str | None:
        """Routes a single input line.

        Returns:
            * ``None`` if ``line`` is not a slash command (treat as chat).
            * ``EXIT_SIGNAL`` if the user asked to quit.
            * Otherwise the result string to be displayed.
        """
        stripped = line.strip()
        if not self.is_slash_command(stripped):
            return None

        # Split into command token and the remaining argument string.
        parts = stripped.split(maxsplit=1)
        command = parts[0].lower()

        if command in ("/exit", "/quit", "/q"):
            return EXIT_SIGNAL
        if command == "/help":
            return self.help_text()
        if command == "/clear":
            self.history.clear()
            return "History cleared."
        if command == "/history":
            return self.history_text()
        if command == "/tools":
            return self.tools_text(agent)
        if command == "/model":
            return f"Model: {agent.provider.model}"

        # Unknown slash command — report it instead of treating it as chat.
        return f"Unknown command: {command} (try /help)"


class TUI:
    """An async, interactive terminal UI around an ``AgentCore``.

    The loop reads a line, shows a status line, routes slash commands through
    a :class:`SlashCommandRouter` and forwards everything else to the agent.
    """

    def __init__(self, user_id: str = "tui-user") -> None:
        self.user_id = user_id
        self.router = SlashCommandRouter()
        #: Count of chat messages exchanged with the agent (used in status).
        self.message_count = 0

    # -- rendering -------------------------------------------------------

    def status_line(self, agent: Any) -> str:
        """Builds the status line shown above each prompt."""
        return (
            f"{_DIM}[model: {agent.provider.model} | "
            f"messages: {self.message_count} | "
            f"history: {len(self.router.history)}]{_RESET}"
        )

    def banner(self, agent: Any) -> str:
        """Builds the welcome banner shown once at startup."""
        return (
            f"{_BOLD}ARGO brain — terminal UI{_RESET}\n"
            f"Provider: {agent.provider.model}\n"
            "Type a message, or /help for commands.\n"
        )

    # -- IO (kept thin so the loop stays testable in spirit) -------------

    def _read_line(self, prompt: str) -> str | None:
        """Reads one line of input; returns ``None`` on EOF/interrupt."""
        try:
            return input(prompt)
        except (EOFError, KeyboardInterrupt):
            return None

    # -- main loop -------------------------------------------------------

    async def run(self, agent: Any) -> int:
        """Runs the interactive loop until the user exits.

        Returns a process-style exit code (always 0 for a clean exit).
        """
        print(self.banner(agent))
        while True:
            print(self.status_line(agent))
            line = self._read_line("you> ")
            if line is None:  # EOF or Ctrl+C — leave cleanly.
                print()
                break

            line = line.strip()
            if not line:
                continue

            # Record every non-empty line in the in-memory history.
            self.router.history.append(line)

            result = self.router.handle(line, agent)
            if result == EXIT_SIGNAL:
                break
            if result is not None:
                # It was a slash command — just print the router's output.
                print(result + "\n")
                continue

            # Not a slash command: treat the line as a chat message.
            self.message_count += 1
            resp = await agent.process(
                AgentRequest(user_id=self.user_id, message=line, channel="tui")
            )
            tag = f" [{', '.join(resp.tools_used)}]" if resp.tools_used else ""
            print(f"argo> {resp.content}")
            print(
                f"{_DIM}      ({resp.language} · {resp.model} · "
                f"{resp.iterations} iter · {resp.duration_ms}ms{tag}){_RESET}\n"
            )

        print("Goodbye.")
        return 0


async def _demo() -> int:  # pragma: no cover - manual entry point helper
    """Builds a Mock-backed agent and runs the TUI (used by `python -m`)."""
    import tempfile
    from pathlib import Path

    from argo_brain.config import Settings
    from argo_brain.core import AgentCore

    with tempfile.TemporaryDirectory() as tmp:
        settings = Settings(data_dir=tmp, db_path=str(Path(tmp) / "tui.db"))
        agent = AgentCore(settings)
        try:
            return await TUI().run(agent)
        finally:
            agent.close()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(asyncio.run(_demo()))
