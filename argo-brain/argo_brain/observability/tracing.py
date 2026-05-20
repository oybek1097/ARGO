"""Span-based distributed tracing (spec section 8).

Provides :class:`TraceSpan`, a context manager usable in both synchronous
(``with``) and asynchronous (``async with``) code. Finished spans are
collected into a per-context trace accessible via :func:`current_trace`
and exportable as plain dictionaries with :func:`export_spans`.

Stdlib-only: uses :mod:`time` and :mod:`contextvars`.
"""

from __future__ import annotations

import contextvars
import time
from typing import Dict, List, Optional

# Holds the list of finished spans for the current logical context.
_trace_var: contextvars.ContextVar[Optional[List["TraceSpan"]]] = contextvars.ContextVar(
    "argo_trace", default=None
)
# Tracks the currently-active span so children can discover their parent.
_active_span_var: contextvars.ContextVar[Optional["TraceSpan"]] = contextvars.ContextVar(
    "argo_active_span", default=None
)

# Monotonically increasing identifier source for spans.
_id_counter = 0


def _next_id() -> int:
    """Return a process-unique, increasing integer span id."""
    global _id_counter
    _id_counter += 1
    return _id_counter


def current_trace() -> List["TraceSpan"]:
    """Return the list of finished spans for the current context.

    The list is created lazily on first access and is shared by every
    span that finishes within the same context.
    """
    trace = _trace_var.get()
    if trace is None:
        trace = []
        _trace_var.set(trace)
    return trace


def reset_trace() -> None:
    """Clear the current context's collected spans (useful for tests)."""
    _trace_var.set([])
    _active_span_var.set(None)


class TraceSpan:
    """A single timed unit of work.

    Use it as a context manager::

        with TraceSpan("db.query") as span:
            ...

        async with TraceSpan("http.call"):
            ...

    On exit, the span records its end time / duration, registers itself
    with :func:`current_trace`, and links to its parent span if any.
    """

    def __init__(self, name: str, **attributes: object) -> None:
        self.name: str = name
        self.span_id: int = _next_id()
        self.parent_id: Optional[int] = None
        self.parent: Optional["TraceSpan"] = None
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.duration: Optional[float] = None
        self.attributes: Dict[str, object] = dict(attributes)
        self._token: Optional[contextvars.Token] = None

    # -- lifecycle --------------------------------------------------------
    def start(self) -> "TraceSpan":
        """Begin timing the span and mark it as the active span."""
        self.parent = _active_span_var.get()
        if self.parent is not None:
            self.parent_id = self.parent.span_id
        self.start_time = time.monotonic()
        self._token = _active_span_var.set(self)
        return self

    def finish(self) -> "TraceSpan":
        """Stop timing, restore the parent span, and record the span."""
        self.end_time = time.monotonic()
        if self.start_time is not None:
            self.duration = self.end_time - self.start_time
        if self._token is not None:
            _active_span_var.reset(self._token)
            self._token = None
        current_trace().append(self)
        return self

    def set_attribute(self, key: str, value: object) -> None:
        """Attach an arbitrary key/value attribute to the span."""
        self.attributes[key] = value

    def to_dict(self) -> Dict[str, object]:
        """Return a JSON-serialisable representation of the span."""
        return {
            "name": self.name,
            "span_id": self.span_id,
            "parent_id": self.parent_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "attributes": dict(self.attributes),
        }

    # -- synchronous context manager -------------------------------------
    def __enter__(self) -> "TraceSpan":
        return self.start()

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc is not None:
            self.set_attribute("error", repr(exc))
        self.finish()
        return False

    # -- asynchronous context manager ------------------------------------
    async def __aenter__(self) -> "TraceSpan":
        return self.start()

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        if exc is not None:
            self.set_attribute("error", repr(exc))
        self.finish()
        return False


def export_spans() -> List[Dict[str, object]]:
    """Return the current trace's finished spans as a list of dicts."""
    return [span.to_dict() for span in current_trace()]
