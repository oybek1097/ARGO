"""Greeting Injector — bundled ARGO plugin.

Responds to a /hello slash command with a friendly, context-aware greeting.
"""

from __future__ import annotations

from datetime import datetime

from argo_brain.plugin.api import ArgoPlugin


class GreetingInjectorPlugin(ArgoPlugin):
    """Provides a time-aware greeting command."""

    name = "greeting-injector"
    version = "1.0.0"
    description = "Adds a friendly /hello slash command."

    @staticmethod
    def _part_of_day(hour: int) -> str:
        if hour < 12:
            return "morning"
        if hour < 18:
            return "afternoon"
        return "evening"

    async def handle_command(self, command: str, user_id: str, args: str) -> str | None:
        if command != "hello":
            return None
        part = self._part_of_day(datetime.now().hour)
        return f"Good {part}, {user_id}. How can ARGO help?"
