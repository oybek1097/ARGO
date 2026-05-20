"""Tests for the observability subsystem (spec section 8).

Covers the Prometheus metrics collector, span-based tracing, and the
structured JSON logger. Stdlib :mod:`unittest` only.
"""

import asyncio
import contextvars
import io
import json
import logging
import unittest

from argo_brain.observability import MetricsCollector, TraceSpan, get_logger
from argo_brain.observability.tracing import (
    current_trace,
    export_spans,
    reset_trace,
)


class TestMetricsCounters(unittest.TestCase):
    """Counter behaviour for MetricsCollector."""

    def test_counter_increments_by_default_one(self):
        """Calling counter() repeatedly accumulates by 1."""
        m = MetricsCollector()
        m.counter("requests_total")
        m.counter("requests_total")
        m.counter("requests_total")
        self.assertEqual(m.get_counter("requests_total"), 3.0)

    def test_counter_custom_increment(self):
        """A counter accepts an explicit increment value."""
        m = MetricsCollector()
        m.counter("bytes_total", value=10)
        m.counter("bytes_total", value=5)
        self.assertEqual(m.get_counter("bytes_total"), 15.0)

    def test_counter_labels_are_independent(self):
        """Counters with differing labels track separate series."""
        m = MetricsCollector()
        m.counter("hits", labels={"route": "/a"})
        m.counter("hits", labels={"route": "/b"})
        m.counter("hits", labels={"route": "/a"})
        self.assertEqual(m.get_counter("hits", {"route": "/a"}), 2.0)
        self.assertEqual(m.get_counter("hits", {"route": "/b"}), 1.0)

    def test_counter_rejects_negative(self):
        """Counters must not decrease."""
        m = MetricsCollector()
        with self.assertRaises(ValueError):
            m.counter("x", value=-1)


class TestMetricsGauges(unittest.TestCase):
    """Gauge behaviour for MetricsCollector."""

    def test_gauge_sets_value(self):
        """A gauge holds the most recently set value."""
        m = MetricsCollector()
        m.gauge("temp", 21.5)
        m.gauge("temp", 19.0)
        self.assertEqual(m.get_gauge("temp"), 19.0)

    def test_gauge_unseen_is_none(self):
        """Querying an unknown gauge returns None."""
        m = MetricsCollector()
        self.assertIsNone(m.get_gauge("missing"))


class TestMetricsHistograms(unittest.TestCase):
    """Histogram bucketing for MetricsCollector."""

    def test_histogram_counts_observations(self):
        """Histogram tracks total count and sum of observations."""
        m = MetricsCollector()
        for v in (0.1, 0.2, 0.3):
            m.histogram("latency", v)
        data = m.get_histogram("latency")
        self.assertIsNotNone(data)
        self.assertEqual(data["count"], 3)
        self.assertAlmostEqual(data["sum"], 0.6)

    def test_histogram_buckets_observations(self):
        """Observations fall into every bucket whose bound they fit."""
        m = MetricsCollector(buckets=(0.1, 0.5, 1.0))
        m.histogram("d", 0.05)  # fits all three buckets
        m.histogram("d", 0.7)   # fits only the 1.0 bucket
        data = m.get_histogram("d")
        # bucket[0]=le 0.1, bucket[1]=le 0.5, bucket[2]=le 1.0
        self.assertEqual(data["buckets"], [1, 1, 2])


class TestMetricsRender(unittest.TestCase):
    """Prometheus text-exposition rendering."""

    def test_render_contains_metric_names(self):
        """Rendered output mentions each registered metric name."""
        m = MetricsCollector()
        m.counter("argo_requests")
        m.gauge("argo_queue_depth", 4)
        m.histogram("argo_latency", 0.2)
        out = m.render_prometheus()
        self.assertIn("argo_requests", out)
        self.assertIn("argo_queue_depth", out)
        self.assertIn("argo_latency", out)

    def test_render_contains_type_lines(self):
        """Rendered output includes a # TYPE line for each metric kind."""
        m = MetricsCollector()
        m.counter("c")
        m.gauge("g", 1)
        m.histogram("h", 0.5)
        out = m.render_prometheus()
        self.assertIn("# TYPE c counter", out)
        self.assertIn("# TYPE g gauge", out)
        self.assertIn("# TYPE h histogram", out)

    def test_render_histogram_has_bucket_sum_count(self):
        """Histogram rendering emits _bucket, _sum and _count series."""
        m = MetricsCollector(buckets=(1.0,))
        m.histogram("h", 0.5)
        out = m.render_prometheus()
        self.assertIn("h_bucket", out)
        self.assertIn('le="+Inf"', out)
        self.assertIn("h_sum", out)
        self.assertIn("h_count", out)

    def test_render_includes_labels(self):
        """Labelled series render their labels in Prometheus syntax."""
        m = MetricsCollector()
        m.counter("hits", labels={"route": "/home"})
        out = m.render_prometheus()
        self.assertIn('route="/home"', out)


class TestTracing(unittest.TestCase):
    """Span-based tracing behaviour."""

    def setUp(self):
        """Each test runs against a fresh trace context."""
        reset_trace()

    def test_span_records_positive_duration(self):
        """A finished span has a non-negative measured duration."""
        with TraceSpan("work") as span:
            sum(range(1000))
        self.assertIsNotNone(span.duration)
        self.assertGreaterEqual(span.duration, 0.0)
        self.assertIsNotNone(span.start_time)
        self.assertIsNotNone(span.end_time)

    def test_nested_spans_record_parent(self):
        """A child span links to its enclosing parent span."""
        with TraceSpan("parent") as parent:
            with TraceSpan("child") as child:
                pass
        self.assertEqual(child.parent_id, parent.span_id)
        self.assertIs(child.parent, parent)
        self.assertIsNone(parent.parent_id)

    def test_export_spans_returns_finished_spans(self):
        """export_spans returns one dict per finished span."""
        with TraceSpan("a"):
            with TraceSpan("b"):
                pass
        spans = export_spans()
        names = {s["name"] for s in spans}
        self.assertEqual(names, {"a", "b"})
        for s in spans:
            self.assertIn("span_id", s)
            self.assertIn("duration", s)

    def test_current_trace_collects_spans(self):
        """current_trace accumulates each finished span."""
        with TraceSpan("one"):
            pass
        with TraceSpan("two"):
            pass
        self.assertEqual(len(current_trace()), 2)

    def test_span_records_error_attribute(self):
        """An exception inside a span is recorded and re-raised."""
        with self.assertRaises(RuntimeError):
            with TraceSpan("fails") as span:
                raise RuntimeError("boom")
        self.assertIn("error", span.attributes)

    def test_async_span_records_duration(self):
        """A span used via 'async with' records its duration."""
        reset_trace()

        async def run():
            async with TraceSpan("async-work") as span:
                await asyncio.sleep(0)
            return span

        # Run inside its own context so the trace is isolated.
        ctx = contextvars.copy_context()
        span = ctx.run(lambda: asyncio.run(run()))
        self.assertIsNotNone(span.duration)
        self.assertGreaterEqual(span.duration, 0.0)


class TestStructuredLogging(unittest.TestCase):
    """Structured JSON logger behaviour."""

    def test_get_logger_returns_logger(self):
        """get_logger returns a configured logging.Logger instance."""
        logger = get_logger("argo.test.basic")
        self.assertIsInstance(logger, logging.Logger)
        self.assertTrue(logger.handlers)

    def test_log_line_is_parseable_json(self):
        """An emitted record is a single line of valid JSON."""
        logger = get_logger("argo.test.json")
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        from argo_brain.observability.logging import JsonFormatter

        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        try:
            logger.info("hello world")
        finally:
            logger.removeHandler(handler)
        payload = json.loads(stream.getvalue().strip())
        self.assertEqual(payload["message"], "hello world")
        self.assertEqual(payload["level"], "INFO")
        self.assertEqual(payload["logger"], "argo.test.json")
        self.assertIn("timestamp", payload)

    def test_log_includes_extra_fields(self):
        """Caller-supplied 'extra' fields appear in the JSON output."""
        logger = get_logger("argo.test.extra")
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        from argo_brain.observability.logging import JsonFormatter

        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        try:
            logger.info("request done", extra={"user_id": 42, "route": "/x"})
        finally:
            logger.removeHandler(handler)
        payload = json.loads(stream.getvalue().strip())
        self.assertEqual(payload["user_id"], 42)
        self.assertEqual(payload["route"], "/x")

    def test_get_logger_idempotent_handlers(self):
        """Repeated get_logger calls do not stack JSON handlers."""
        from argo_brain.observability.logging import JsonFormatter

        get_logger("argo.test.idem")
        logger = get_logger("argo.test.idem")
        json_handlers = [
            h for h in logger.handlers if isinstance(h.formatter, JsonFormatter)
        ]
        self.assertEqual(len(json_handlers), 1)


if __name__ == "__main__":
    unittest.main()
