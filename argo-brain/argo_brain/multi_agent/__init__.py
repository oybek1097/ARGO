"""Multi-agent subsystem — spec section 4.11.

Provides the durable Kanban board, task delegation, mixture-of-agents and
DAG workflow execution.
"""

from argo_brain.multi_agent.dag import DAGWorkflow
from argo_brain.multi_agent.delegate import delegate_task, mixture_of_agents
from argo_brain.multi_agent.kanban import KanbanManager

__all__ = [
    "DAGWorkflow",
    "KanbanManager",
    "delegate_task",
    "mixture_of_agents",
]
