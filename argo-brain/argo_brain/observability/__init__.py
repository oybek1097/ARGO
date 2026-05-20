"""Observability subsystem — metrics, tracing, structured logging.

Implements spec section 8: provides a Prometheus-compatible metrics
collector, a span-based tracing facility, and a structured JSON logger.
Stdlib-only.
"""

from argo_brain.observability.logging import get_logger
from argo_brain.observability.metrics import MetricsCollector
from argo_brain.observability.tracing import TraceSpan

__all__ = ["MetricsCollector", "TraceSpan", "get_logger"]
