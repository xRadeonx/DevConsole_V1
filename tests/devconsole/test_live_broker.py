# tests/devconsole/test_live_broker.py
"""Tests for Phase 6R: LiveConsoleBroker and streaming wall endpoints."""

from __future__ import annotations

import collections
import queue
import time
import unittest
from unittest import mock

from devconsole.services.terminal.live_broker import (
    DEFAULT_MAX_LINES,
    LiveConsoleBroker,
    LiveConsoleItem,
    get_live_broker,
)
from tests.devconsole.support import DevConsoleTestCase, json_body, make_handler


class TestLiveBroker(unittest.TestCase):
    def setUp(self):
        self.broker = LiveConsoleBroker(max_lines=100)

    def tearDown(self):
        self.broker.stop()

    def test_item_initialization_and_serialization(self):
        item = LiveConsoleItem(
            id="ms_test",
            service="ms_test",
            name="ms_test",
            category="backend",
            service_type="backend",
            port=8000,
            tmux_session="sisper_ms_test",
            status="RUNNING",
        )
        item.ring_buffer.append("line 1")
        item.ring_buffer.append("line 2")

        d_no_lines = item.to_dict(include_lines=False)
        self.assertEqual(d_no_lines["id"], "ms_test")
        self.assertEqual(d_no_lines["category"], "backend")
        self.assertEqual(d_no_lines["line_count"], 2)
        self.assertNotIn("lines", d_no_lines)

        d_with_lines = item.to_dict(include_lines=True)
        self.assertIn("lines", d_with_lines)
        self.assertEqual(d_with_lines["lines"], ["line 1", "line 2"])

    def test_subscriber_queue_lifecycle_and_snapshot(self):
        q = queue.Queue(maxsize=10)
        sub_id = self.broker.subscribe(q)
        self.assertTrue(bool(sub_id))

        # First item must be snapshot
        event = q.get_nowait()
        self.assertEqual(event["type"], "snapshot")
        self.assertIn("services", event["data"])

        self.broker.unsubscribe(sub_id)
        self.assertNotIn(sub_id, self.broker._subscribers)

    def test_broadcast_backpressure_drops_oldest(self):
        q = queue.Queue(maxsize=2)
        sub_id = self.broker.subscribe(q)
        # Drain snapshot
        q.get_nowait()

        # Fill queue to maxsize
        q.put_nowait({"msg": 1})
        q.put_nowait({"msg": 2})
        self.assertTrue(q.full())

        # Broadcasting another message should not raise queue.Full
        self.broker._broadcast({"msg": 3})
        self.assertTrue(q.full())

        self.broker.unsubscribe(sub_id)

    @mock.patch("subprocess.check_output")
    def test_reconcile_and_parse_sessions(self, mock_output):
        mock_output.return_value = (
            b"sisper_ms_sisper_contratos\n"
            b"sisper_aux_ms_sisper_contratos_consumer\n"
            b"foreign_session\n"
        )
        sessions = self.broker._list_managed_tmux_sessions()
        self.assertIn("sisper_ms_sisper_contratos", sessions)
        self.assertEqual(sessions["sisper_ms_sisper_contratos"], "ms_sisper_contratos")
        self.assertIn("sisper_aux_ms_sisper_contratos_consumer", sessions)
        self.assertEqual(sessions["sisper_aux_ms_sisper_contratos_consumer"], "ms_sisper_contratos_consumer")
        self.assertNotIn("foreign_session", sessions)


class TestLiveBrokerEndpoints(DevConsoleTestCase):
    def get(self, path: str, headers: dict | None = None):
        from devconsole.api.handlers import DevConsoleHandler
        h = make_handler(DevConsoleHandler, path=path, headers=headers or {})
        h.do_GET()
        return h

    def test_get_catalog_endpoint(self):
        h = self.get("/api/services/catalog")
        self.assertEqual(200, h.captured["status"])
        body = json_body(h)
        self.assertIn("catalog", body)
        self.assertIn("count", body)
        self.assertGreater(body["count"], 0)

    def test_get_wall_endpoint(self):
        h = self.get("/api/services/wall")
        self.assertEqual(200, h.captured["status"])
        body = json_body(h)
        self.assertIn("services", body)
        self.assertIn("count", body)
        self.assertGreater(body["count"], 0)
