"""AgentCore — Plan -> Execute -> Reflect loop.

Implements the pseudocode from spec section 4.2. Flow: language detection ->
profile -> context (history + relevant skills) -> LLM loop -> tool dispatch
(with plugin hooks) -> persistence. The reflection queue, trajectory export
and prompt cache are still marked as TODOs for later sprints.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from argo_brain.cache.session import SessionCache, fingerprint
from argo_brain.config import Settings
from argo_brain.language import detect
from argo_brain.memory import MemoryManager
from argo_brain.observability.metrics import MetricsCollector
from argo_brain.plugin import PluginRegistry
from argo_brain.providers import LLMProvider, get_provider
from argo_brain.rl.trajectory import TrajectoryCollector
from argo_brain.skills import SkillLoader
from argo_brain.tools import ToolRegistry, build_default_registry


@dataclass
class AgentRequest:
    """An incoming request to the agent."""

    user_id: str
    message: str
    language: str = ""          # empty -> detected automatically
    channel: str = "cli"
    session_id: str | None = None
    stream: bool = False


@dataclass
class AgentResponse:
    """Agent response (matches the spec's IPC `Brain -> Core` format)."""

    content: str
    language: str
    model: str
    tools_used: list[str] = field(default_factory=list)
    iterations: int = 1
    duration_ms: int = 0
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "language": self.language,
            "model": self.model,
            "tools_used": self.tools_used,
            "iterations": self.iterations,
            "duration_ms": self.duration_ms,
            "error": self.error,
        }


_SYSTEM_TEMPLATE = (
    "You are ARGO, a multilingual AI agent. Reply to the user in their "
    "detected language ({language}), keeping answers short and precise. "
    "Use the available tools when needed."
)


class AgentCore:
    """The main execution loop of the ARGO agent."""

    def __init__(
        self,
        settings: Settings,
        memory: MemoryManager | None = None,
        registry: ToolRegistry | None = None,
        provider: LLMProvider | None = None,
        plugins: PluginRegistry | None = None,
        skills: SkillLoader | None = None,
        metrics: MetricsCollector | None = None,
        trajectories: TrajectoryCollector | None = None,
        cache: SessionCache | None = None,
    ) -> None:
        self.settings = settings
        self.memory = memory or MemoryManager(
            settings.resolved_db_path,
            working_size=settings.working_memory_size,
        )
        self.registry = registry or build_default_registry(memory=self.memory)
        self.provider = provider or get_provider(settings.model)
        self.plugins = plugins or PluginRegistry()
        self.skills = skills
        # Optional observability / cache / RL subsystems. When left as None
        # the agent loop behaves exactly as before (default fast path).
        self.metrics = metrics
        self.trajectories = trajectories
        self.cache = cache

    def close(self) -> None:
        self.memory.close()

    def _build_system_prompt(self, language: str, message: str) -> str:
        """Assembles the system prompt, injecting any relevant skills."""
        system = _SYSTEM_TEMPLATE.format(language=language)
        if self.skills is not None:
            relevant = self.skills.get_relevant(message)
            if relevant:
                blocks = "\n\n".join(
                    f"## Skill: {s.name}\n{s.content}" for s in relevant
                )
                system += f"\n\n# Relevant skills\n{blocks}"
        return system

    async def process(self, req: AgentRequest) -> AgentResponse:
        """Fully processes a single request."""
        t0 = time.perf_counter()

        # Observability: count every chat request received.
        if self.metrics is not None:
            self.metrics.counter("argo_chat_requests_total")

        # 1. Language detection + routing
        language = req.language or detect(req.message)

        # 2. User profile
        await self.memory.ensure_profile(req.user_id, language=language)

        # 3. Context assembly (history + relevant skills)
        history = await self.memory.history(
            req.user_id, limit=self.settings.context_history
        )

        # 4. System prompt
        system = self._build_system_prompt(language, req.message)
        llm_msgs: list[dict] = [{"role": "system", "content": system}]
        llm_msgs.extend(
            {"role": h["role"], "content": h["content"]}
            for h in history
            if h["role"] in ("user", "assistant")
        )
        llm_msgs.append({"role": "user", "content": req.message})

        # Prompt-cache: record a deterministic fingerprint of the request
        # prefix. This never changes the response content — it only seeds the
        # cache key so later sprints can wire in lookups safely.
        if self.cache is not None:
            try:
                fp = fingerprint(llm_msgs, self.provider.model)
                self.cache.set(req.user_id, fp, fp)
            except Exception:
                # The cache is best-effort: never let it break a request.
                pass

        # 5. Plan -> Execute loop
        tools_used: list[str] = []
        final = ""
        iterations = 0
        succeeded = False
        schemas = self.registry.schemas()

        for iterations in range(1, self.settings.max_iterations + 1):
            resp = await self.provider.complete(llm_msgs, tools=schemas)

            if resp.has_tool_calls:
                # Plugin pre-tool veto.
                calls = await self.plugins.run_pre_tool(
                    resp.tool_calls, req.user_id
                )
                # Keep the tool calls on the assistant message so real
                # providers can replay them as `tool_use` blocks.
                llm_msgs.append(
                    {
                        "role": "assistant",
                        "content": resp.content or "",
                        "tool_calls": [
                            {"id": c.id, "name": c.name, "arguments": c.arguments}
                            for c in calls
                        ],
                    }
                )
                results = await self.registry.execute_parallel(
                    calls, req.user_id,
                    max_workers=self.settings.max_parallel_tools,
                )
                for call, result in zip(calls, results):
                    result = await self.plugins.run_post_tool(
                        call, result, req.user_id
                    )
                    tools_used.append(call.name)
                    llm_msgs.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.id,
                            "content": result.content,
                        }
                    )
            else:
                final = resp.content
                succeeded = True
                break
        else:
            final = "The maximum number of iterations was exceeded."

        # 6. Persist to memory
        await self.memory.add(
            req.user_id, "user", req.message,
            language=language, channel=req.channel, session_id=req.session_id,
        )
        await self.memory.add(
            req.user_id, "assistant", final,
            language=language, channel=req.channel, session_id=req.session_id,
        )

        # 7. Plugin response hook
        await self.plugins.emit_response(req.user_id, final, self.provider.model)

        duration_ms = int((time.perf_counter() - t0) * 1000)

        # 8. Observability: record request latency in a histogram (seconds).
        if self.metrics is not None:
            self.metrics.histogram(
                "argo_chat_duration_seconds", duration_ms / 1000.0
            )

        # 9. Trajectory export: record this interaction for RL / SFT use.
        if self.trajectories is not None:
            self.trajectories.record(
                user_input=req.message,
                output=final,
                tools_used=tools_used,
                model=self.provider.model,
                success=succeeded,
                duration_ms=duration_ms,
            )

        return AgentResponse(
            content=final,
            language=language,
            model=self.provider.model,
            tools_used=tools_used,
            iterations=iterations,
            duration_ms=duration_ms,
        )
