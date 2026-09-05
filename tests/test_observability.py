from __future__ import annotations

import json
import logging
import unittest

from financial_manager.observability import (
    JsonFormatter,
    Metrics,
    TraceContext,
    agent_outcome,
    set_trace_context,
)


class ObservabilityTests(unittest.TestCase):
    def test_structured_log_has_identity_context_and_redaction(self) -> None:
        set_trace_context(TraceContext("trade-42", "a" * 32))
        formatter = JsonFormatter("decision", "0.1.0+sha.abc", "TEST")
        record = logging.LogRecord(
            "fm", logging.INFO, __file__, 1, "policy evaluated", (), None
        )
        record.attributes = {"token": "secret", "outcome": "allow"}
        event = json.loads(formatter.format(record))
        self.assertEqual(event["correlation_id"], "trade-42")
        self.assertEqual(event["trace_id"], "a" * 32)
        self.assertEqual(event["service"], "decision")
        self.assertEqual(event["attributes"]["token"], "[REDACTED]")

    def test_baseline_and_agent_metrics_are_prometheus_compatible(self) -> None:
        metrics = Metrics()
        metrics.increment("fm_http_requests_total", method="GET", status="200")
        metrics.gauge("fm_queue_depth", 3, queue="trade-intent")
        metrics.gauge("fm_service_up", 1, service="baseline")
        agent_outcome(metrics, "research", "market-data", "success", 0.25)
        output = metrics.render()
        self.assertIn("fm_http_requests_total", output)
        self.assertIn("fm_queue_depth", output)
        self.assertIn("fm_service_up", output)
        self.assertIn("fm_agent_executions_total", output)
        self.assertNotIn("secret", output)

    def test_trace_context_is_shared_with_audit_correlation(self) -> None:
        context = TraceContext.new("trade-flow-99")
        self.assertEqual(context.correlation_id, "trade-flow-99")
        self.assertEqual(len(context.trace_id), 32)


if __name__ == "__main__":
    unittest.main()
