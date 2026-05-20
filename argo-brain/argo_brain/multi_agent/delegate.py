"""Task delegation and mixture-of-agents — spec section 4.11.

Two collaboration primitives built on top of :class:`AgentCore`:

* :func:`delegate_task` — fan-out: each prompt is processed independently as
  an isolated sub-task so the sub-agents' contexts never bleed into each
  other (a distinct ``user_id`` per sub-task guarantees the isolation).
* :func:`mixture_of_agents` — iterative refinement: an initial answer is fed
  back to the agent for a number of self-improvement passes, returning the
  final synthesized answer.
"""

from __future__ import annotations

import asyncio

from argo_brain.core.agent import AgentCore, AgentRequest


async def delegate_task(
    agent: AgentCore,
    prompts: list[str],
    user_id: str = "subagent",
) -> list[str]:
    """Run each prompt through the agent independently.

    Every prompt is dispatched as its own isolated sub-task. To keep the
    sub-tasks from mixing conversation context, each one gets a distinct
    ``user_id`` derived from ``user_id`` plus its index. The sub-tasks are
    executed concurrently and their result strings are returned in the same
    order as the input prompts.

    Args:
        agent: The :class:`AgentCore` used to process every sub-task.
        prompts: The list of independent sub-task prompts.
        user_id: Base identifier; each sub-task uses ``f"{user_id}-{i}"``.

    Returns:
        A list of result strings, one per prompt, preserving order.
    """
    if not prompts:
        return []

    async def _run(index: int, prompt: str) -> str:
        # A distinct user_id per sub-task isolates memory/history so the
        # sub-agents do not influence one another.
        req = AgentRequest(user_id=f"{user_id}-{index}", message=prompt)
        resp = await agent.process(req)
        return resp.content

    tasks = [_run(i, p) for i, p in enumerate(prompts)]
    return list(await asyncio.gather(*tasks))


async def mixture_of_agents(
    agent: AgentCore,
    query: str,
    rounds: int = 2,
) -> str:
    """Iteratively refine an answer through several agent passes.

    The query is first answered normally. The answer is then fed back to the
    agent ``rounds`` more times, each pass asked to critique and improve the
    previous draft. The final synthesized answer is returned.

    Args:
        agent: The :class:`AgentCore` used for every pass.
        query: The original user query.
        rounds: Number of refinement passes after the initial answer
            (values <= 0 yield just the initial answer).

    Returns:
        The final synthesized answer string.
    """
    # Initial pass — produce a first draft answer.
    first = await agent.process(
        AgentRequest(user_id="moa-initial", message=query)
    )
    answer = first.content

    # Each refinement pass runs in its own isolated context so the agent
    # treats the previous draft purely as input to improve upon.
    for round_index in range(max(0, rounds)):
        refine_prompt = (
            "Original query:\n"
            f"{query}\n\n"
            "Current draft answer:\n"
            f"{answer}\n\n"
            "Review the draft above for correctness, completeness and "
            "clarity, then produce an improved, final answer. "
            "Reply with the improved answer only."
        )
        resp = await agent.process(
            AgentRequest(
                user_id=f"moa-refine-{round_index}",
                message=refine_prompt,
            )
        )
        if resp.content:
            answer = resp.content

    return answer
