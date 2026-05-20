# Multi-agent

ARGO can coordinate **more than one agent run** to tackle a job: fanning a
task out into independent sub-tasks, iteratively refining an answer, running a
dependency graph of tasks, or tracking longer-lived work on a durable Kanban
board.

The subsystem lives under `argo_brain/multi_agent/` and is built on top of the
single-agent `AgentCore`.

## Delegation — fan-out

**Module:** `argo_brain/multi_agent/delegate.py`

`delegate_task()` runs a list of prompts through the agent **independently**
and concurrently. Each sub-task gets a distinct `user_id`, so the sub-agents'
contexts never bleed into one another.

```python
from argo_brain.multi_agent import delegate_task

answers = await delegate_task(
    agent,
    prompts=[
        "Summarise the Q1 sales report.",
        "List the open security tickets.",
        "Draft a status update for the team.",
    ],
)
# answers is a list of strings, one per prompt, in order.
```

Use this when a job decomposes into pieces that do not depend on each other.

## Mixture-of-agents — iterative refinement

Also in `delegate.py`, `mixture_of_agents()` is the opposite pattern: a single
question is answered, and that answer is fed back to the agent for a number of
self-improvement passes. The final synthesized answer is returned.

```python
from argo_brain.multi_agent import mixture_of_agents

answer = await mixture_of_agents(agent, "Design a backup strategy for ARGO.")
```

Use this when quality matters more than latency and a single pass is not good
enough.

## DAG workflow runner

**Module:** `argo_brain/multi_agent/dag.py`

`DAGWorkflow` lets you describe a set of agent tasks **with dependencies**.
`run()` executes them in topological order: a task starts only after every
task it depends on has finished, and tasks with no pending dependencies run
**concurrently**.

- Dependency **cycles are detected up front** and reported with a clear
  `DAGCycleError` before anything runs.
- This is the right tool when later steps need the output of earlier ones —
  e.g. "gather data" → "analyse" → "write report", with two independent
  gather steps running in parallel.

## The Kanban board

**Module:** `argo_brain/multi_agent/kanban.py`

For work that outlives a single process, the `KanbanManager` provides a
**durable, SQLite-backed Kanban board**. It is the coordination substrate for
longer-running, multi-step or multi-worker jobs.

### Task lifecycle

```
todo ─► claimed ─► in_progress ─► done
                              └─► failed
   (a task may also be moved to: blocked)
```

A worker **claims** a task, moves it to **in_progress**, and finishes it as
**done** or **failed**; a task waiting on something else is marked
**blocked**. Because the board is in SQLite, the state survives restarts and
can be shared between processes.

### Boards and tasks

The schema has `kanban_boards` (each with a `user_id`, `name`, `goal` and
`status`) and `kanban_tasks`. A board groups the tasks for one goal.

> **Roadmap.** Heartbeat-based zombie reclaim (recovering a task whose worker
> died mid-run) and the LLM-judge hallucination gate are planned for a later
> sprint. The database schema already carries the columns for them.

## Choosing a pattern

| You have… | Use |
|---|---|
| Independent sub-tasks, want them all done | `delegate_task` |
| One hard question, want the best answer | `mixture_of_agents` |
| Tasks where later steps need earlier outputs | `DAGWorkflow` |
| Long-lived work, restarts, multiple workers | `KanbanManager` |

## See also

- [Architecture](architecture.md) — the single-agent loop these build on.
- [Tools](tools.md) — the `todo` and `plan` workflow tools an agent uses to
  pace itself within a single run.
