"""Offline tests for the extra LLM providers — spec section 4.8.

Covers `OllamaProvider` message conversion and the `OpenAICompatibleProvider`
generic provider together with its vendor factory functions. All tests are
strictly OFFLINE — no network access is performed.
"""

from __future__ import annotations

import unittest

from argo_brain.providers.base import LLMResponse
from argo_brain.providers.compatible import (
    DEEPSEEK_BASE_URL,
    GROQ_BASE_URL,
    MISTRAL_BASE_URL,
    OPENROUTER_BASE_URL,
    TOGETHER_BASE_URL,
    OpenAICompatibleProvider,
    deepseek,
    groq,
    mistral,
    openrouter,
    together,
)
from argo_brain.providers.ollama import (
    OllamaProvider,
    convert_messages,
    parse_response,
)


class TestOllamaConversion(unittest.TestCase):
    """Message conversion for the Ollama chat format."""

    def test_system_and_user_passthrough(self):
        out = convert_messages(
            [
                {"role": "system", "content": "be brief"},
                {"role": "user", "content": "hi"},
            ]
        )
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0], {"role": "system", "content": "be brief"})
        self.assertEqual(out[1], {"role": "user", "content": "hi"})

    def test_assistant_plain_text(self):
        out = convert_messages([{"role": "assistant", "content": "hello"}])
        self.assertEqual(out[0]["role"], "assistant")
        self.assertEqual(out[0]["content"], "hello")
        self.assertNotIn("tool_calls", out[0])

    def test_assistant_empty_content_becomes_string(self):
        # Ollama expects a string content, never null.
        out = convert_messages([{"role": "assistant", "content": None}])
        self.assertEqual(out[0]["content"], "")

    def test_assistant_with_tool_calls_keeps_dict_arguments(self):
        out = convert_messages(
            [
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "c1",
                            "name": "calculate",
                            "arguments": {"expression": "2+2"},
                        }
                    ],
                }
            ]
        )
        calls = out[0]["tool_calls"]
        self.assertEqual(len(calls), 1)
        fn = calls[0]["function"]
        self.assertEqual(fn["name"], "calculate")
        # Unlike OpenAI, Ollama keeps arguments as a dict (not a JSON string).
        self.assertEqual(fn["arguments"], {"expression": "2+2"})

    def test_tool_message_drops_tool_call_id(self):
        out = convert_messages(
            [
                {
                    "role": "tool",
                    "tool_call_id": "c1",
                    "content": "4",
                }
            ]
        )
        self.assertEqual(out[0], {"role": "tool", "content": "4"})

    def test_unknown_role_is_ignored(self):
        out = convert_messages([{"role": "developer", "content": "x"}])
        self.assertEqual(out, [])

    def test_parse_response_plain_text(self):
        raw = {"model": "llama3", "message": {"content": "answer"}}
        resp = parse_response(raw, "fallback")
        self.assertIsInstance(resp, LLMResponse)
        self.assertEqual(resp.content, "answer")
        self.assertEqual(resp.model, "llama3")
        self.assertFalse(resp.has_tool_calls)

    def test_parse_response_with_tool_calls(self):
        raw = {
            "model": "llama3",
            "message": {
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "current_time",
                            "arguments": {},
                        }
                    }
                ],
            },
        }
        resp = parse_response(raw, "fallback")
        self.assertTrue(resp.has_tool_calls)
        self.assertEqual(resp.tool_calls[0].name, "current_time")
        # A synthetic id is generated since Ollama omits one.
        self.assertEqual(resp.tool_calls[0].id, "call_0")

    def test_parse_response_string_arguments_decoded(self):
        raw = {
            "message": {
                "tool_calls": [
                    {
                        "function": {
                            "name": "calculate",
                            "arguments": '{"expression": "1+1"}',
                        }
                    }
                ]
            }
        }
        resp = parse_response(raw, "fallback")
        self.assertEqual(
            resp.tool_calls[0].arguments, {"expression": "1+1"}
        )


class TestOllamaProviderConstruction(unittest.TestCase):
    """Construction defaults of `OllamaProvider` (no network)."""

    def test_default_url_and_model(self):
        p = OllamaProvider()
        self.assertEqual(p.base_url, "http://localhost:11434/api/chat")
        self.assertEqual(p.model, "llama3")

    def test_custom_url_and_model(self):
        p = OllamaProvider(model="mistral", base_url="http://host:1/api/chat")
        self.assertEqual(p.model, "mistral")
        self.assertEqual(p.base_url, "http://host:1/api/chat")


class TestCompatibleProviderConstruction(unittest.TestCase):
    """Construction of the generic `OpenAICompatibleProvider`."""

    def test_construction_stores_fields(self):
        p = OpenAICompatibleProvider(
            base_url="https://example.com/v1/chat/completions",
            api_key="secret",
            model="my-model",
        )
        self.assertEqual(
            p.base_url, "https://example.com/v1/chat/completions"
        )
        self.assertEqual(p.model, "my-model")
        self.assertEqual(p._api_key, "secret")

    def test_default_max_tokens(self):
        p = OpenAICompatibleProvider(
            base_url="https://example.com", api_key="k", model="m"
        )
        self.assertEqual(p._max_tokens, 2048)

    def test_empty_api_key_normalised(self):
        p = OpenAICompatibleProvider(
            base_url="https://example.com", api_key="", model="m"
        )
        self.assertEqual(p._api_key, "")


class TestVendorFactories(unittest.TestCase):
    """Each factory produces a provider with the correct base_url/model."""

    def test_deepseek_factory(self):
        p = deepseek(model="deepseek-chat", api_key="k")
        self.assertIsInstance(p, OpenAICompatibleProvider)
        self.assertEqual(p.base_url, DEEPSEEK_BASE_URL)
        self.assertEqual(p.model, "deepseek-chat")

    def test_groq_factory(self):
        p = groq(model="llama-3.1-70b", api_key="k")
        self.assertIsInstance(p, OpenAICompatibleProvider)
        self.assertEqual(p.base_url, GROQ_BASE_URL)
        self.assertEqual(p.model, "llama-3.1-70b")

    def test_mistral_factory(self):
        p = mistral(model="mistral-large-latest", api_key="k")
        self.assertIsInstance(p, OpenAICompatibleProvider)
        self.assertEqual(p.base_url, MISTRAL_BASE_URL)
        self.assertEqual(p.model, "mistral-large-latest")

    def test_openrouter_factory(self):
        p = openrouter(model="anthropic/claude-3.5-sonnet", api_key="k")
        self.assertIsInstance(p, OpenAICompatibleProvider)
        self.assertEqual(p.base_url, OPENROUTER_BASE_URL)
        self.assertEqual(p.model, "anthropic/claude-3.5-sonnet")

    def test_together_factory(self):
        p = together(model="meta-llama/Llama-3-70b", api_key="k")
        self.assertIsInstance(p, OpenAICompatibleProvider)
        self.assertEqual(p.base_url, TOGETHER_BASE_URL)
        self.assertEqual(p.model, "meta-llama/Llama-3-70b")

    def test_factories_carry_api_key(self):
        p = deepseek(model="deepseek-chat", api_key="my-key")
        self.assertEqual(p._api_key, "my-key")

    def test_all_base_urls_distinct(self):
        urls = {
            DEEPSEEK_BASE_URL,
            GROQ_BASE_URL,
            MISTRAL_BASE_URL,
            OPENROUTER_BASE_URL,
            TOGETHER_BASE_URL,
        }
        self.assertEqual(len(urls), 5)


if __name__ == "__main__":
    unittest.main()
