"""OpenAI-compatible proxy tests — spec section 4.9.

Covers the pure converter functions and basic `OpenAIProxy` construction.
The proxy is intentionally not bound to a port here: tests verify that
construction only stores configuration and does not open a socket.
"""

import tempfile
import unittest
from pathlib import Path

from argo_brain.config import Settings
from argo_brain.core import AgentCore
from argo_brain.providers.base import MockProvider
from argo_brain.proxy import (
    OpenAIProxy,
    agent_response_to_openai,
    openai_request_to_message,
)


class TestOpenAIRequestToMessage(unittest.TestCase):
    """Tests for the request -> message converter."""

    def test_extracts_single_user_message(self):
        body = {"messages": [{"role": "user", "content": "Hello"}]}
        self.assertEqual(openai_request_to_message(body), "Hello")

    def test_extracts_last_user_message(self):
        body = {
            "messages": [
                {"role": "user", "content": "first"},
                {"role": "assistant", "content": "reply"},
                {"role": "user", "content": "second"},
            ]
        }
        self.assertEqual(openai_request_to_message(body), "second")

    def test_ignores_trailing_assistant_message(self):
        body = {
            "messages": [
                {"role": "user", "content": "the question"},
                {"role": "assistant", "content": "the answer"},
            ]
        }
        self.assertEqual(openai_request_to_message(body), "the question")

    def test_skips_system_message(self):
        body = {
            "messages": [
                {"role": "system", "content": "be helpful"},
                {"role": "user", "content": "ping"},
            ]
        }
        self.assertEqual(openai_request_to_message(body), "ping")

    def test_empty_messages_list(self):
        self.assertEqual(openai_request_to_message({"messages": []}), "")

    def test_missing_messages_key(self):
        self.assertEqual(openai_request_to_message({}), "")

    def test_non_dict_body(self):
        self.assertEqual(openai_request_to_message("not a dict"), "")

    def test_no_user_message(self):
        body = {"messages": [{"role": "assistant", "content": "hi"}]}
        self.assertEqual(openai_request_to_message(body), "")

    def test_multipart_content(self):
        body = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "part one "},
                        {"type": "text", "text": "part two"},
                    ],
                }
            ]
        }
        self.assertEqual(openai_request_to_message(body), "part one part two")

    def test_malformed_message_entry_skipped(self):
        body = {"messages": ["garbage", {"role": "user", "content": "ok"}]}
        self.assertEqual(openai_request_to_message(body), "ok")


class TestAgentResponseToOpenAI(unittest.TestCase):
    """Tests for the agent text -> OpenAI envelope converter."""

    def test_object_field(self):
        env = agent_response_to_openai("hi", "mock")
        self.assertEqual(env["object"], "chat.completion")

    def test_content_carried_through(self):
        env = agent_response_to_openai("the answer", "mock")
        self.assertEqual(env["choices"][0]["message"]["content"], "the answer")

    def test_message_role_is_assistant(self):
        env = agent_response_to_openai("x", "mock")
        self.assertEqual(env["choices"][0]["message"]["role"], "assistant")

    def test_finish_reason_is_stop(self):
        env = agent_response_to_openai("x", "mock")
        self.assertEqual(env["choices"][0]["finish_reason"], "stop")

    def test_model_echoed(self):
        env = agent_response_to_openai("x", "claude-sonnet-4-6")
        self.assertEqual(env["model"], "claude-sonnet-4-6")

    def test_has_id_and_usage(self):
        env = agent_response_to_openai("x", "mock")
        self.assertTrue(env["id"].startswith("chatcmpl-"))
        self.assertIn("usage", env)
        self.assertEqual(env["usage"]["total_tokens"], 0)

    def test_unique_ids(self):
        a = agent_response_to_openai("x", "mock")
        b = agent_response_to_openai("x", "mock")
        self.assertNotEqual(a["id"], b["id"])


class TestOpenAIProxyConstruction(unittest.TestCase):
    """Verifies the proxy stores config without binding a port."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        settings = Settings(
            data_dir=self._tmp.name,
            db_path=str(Path(self._tmp.name) / "proxy.db"),
        )
        self.agent = AgentCore(settings, provider=MockProvider())

    def tearDown(self):
        self.agent.close()
        self._tmp.cleanup()

    def test_stores_config_without_binding(self):
        proxy = OpenAIProxy(self.agent, host="127.0.0.1", port=9999)
        self.assertIs(proxy.agent, self.agent)
        self.assertEqual(proxy.host, "127.0.0.1")
        self.assertEqual(proxy.port, 9999)
        # No socket should have been opened by the constructor.
        self.assertIsNone(proxy._httpd)

    def test_default_host_and_port(self):
        proxy = OpenAIProxy(self.agent)
        self.assertEqual(proxy.host, "127.0.0.1")
        self.assertEqual(proxy.port, 8001)

    def test_stop_is_safe_when_not_serving(self):
        # stop() must not raise when serve_forever() was never called.
        proxy = OpenAIProxy(self.agent)
        proxy.stop()


if __name__ == "__main__":
    unittest.main()
