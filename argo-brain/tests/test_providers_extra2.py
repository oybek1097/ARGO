"""Offline tests for extra LLM providers — spec section 4.8.

Covers `argo_brain.providers.extra`:

  * Cohere message conversion + response parsing.
  * `AzureOpenAIProvider` construction and URL building.
  * The `nvidia_nim` / `fireworks` / `perplexity` factories.

All tests are fully offline — no network calls are made.
"""

from __future__ import annotations

import unittest

from argo_brain.providers.base import LLMResponse
from argo_brain.providers.compatible import OpenAICompatibleProvider
from argo_brain.providers.extra import (
    AZURE_DEFAULT_API_VERSION,
    AzureOpenAIProvider,
    CohereProvider,
    FIREWORKS_BASE_URL,
    NVIDIA_NIM_BASE_URL,
    PERPLEXITY_BASE_URL,
    azure_chat_url,
    cohere_convert_messages,
    cohere_parse_response,
    fireworks,
    nvidia_nim,
    perplexity,
)
from argo_brain.tools.base import ToolCall


class CohereConversionTest(unittest.TestCase):
    """Cohere v2 message-conversion helper."""

    def test_basic_roles_passthrough(self) -> None:
        out = cohere_convert_messages(
            [
                {"role": "system", "content": "be brief"},
                {"role": "user", "content": "hi"},
            ]
        )
        self.assertEqual(out[0], {"role": "system", "content": "be brief"})
        self.assertEqual(out[1], {"role": "user", "content": "hi"})

    def test_assistant_tool_calls_serialised(self) -> None:
        out = cohere_convert_messages(
            [
                {
                    "role": "assistant",
                    "content": "",
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
        call = out[0]["tool_calls"][0]
        self.assertEqual(call["id"], "c1")
        self.assertEqual(call["type"], "function")
        self.assertEqual(call["function"]["name"], "calculate")
        # Arguments must be a JSON string, not a dict.
        self.assertIsInstance(call["function"]["arguments"], str)
        self.assertIn("expression", call["function"]["arguments"])

    def test_tool_message_wrapped_in_content_blocks(self) -> None:
        out = cohere_convert_messages(
            [
                {
                    "role": "tool",
                    "tool_call_id": "c1",
                    "content": "4",
                }
            ]
        )
        msg = out[0]
        self.assertEqual(msg["role"], "tool")
        self.assertEqual(msg["tool_call_id"], "c1")
        self.assertIsInstance(msg["content"], list)
        self.assertEqual(msg["content"][0]["document"]["data"], "4")

    def test_assistant_without_tool_calls_has_no_key(self) -> None:
        out = cohere_convert_messages(
            [{"role": "assistant", "content": "hello"}]
        )
        self.assertEqual(out[0]["content"], "hello")
        self.assertNotIn("tool_calls", out[0])


class CohereParseTest(unittest.TestCase):
    """Cohere v2 response-parsing helper."""

    def test_parse_text_blocks(self) -> None:
        raw = {
            "model": "command-r-plus",
            "message": {
                "content": [
                    {"type": "text", "text": "Hello "},
                    {"type": "text", "text": "world"},
                ]
            },
        }
        resp = cohere_parse_response(raw, "fallback")
        self.assertIsInstance(resp, LLMResponse)
        self.assertEqual(resp.content, "Hello world")
        self.assertEqual(resp.model, "command-r-plus")
        self.assertFalse(resp.has_tool_calls)

    def test_parse_tool_calls(self) -> None:
        raw = {
            "message": {
                "content": [],
                "tool_calls": [
                    {
                        "id": "tc1",
                        "function": {
                            "name": "current_time",
                            "arguments": "{}",
                        },
                    }
                ],
            }
        }
        resp = cohere_parse_response(raw, "fallback")
        self.assertTrue(resp.has_tool_calls)
        call = resp.tool_calls[0]
        self.assertIsInstance(call, ToolCall)
        self.assertEqual(call.name, "current_time")
        self.assertEqual(call.arguments, {})

    def test_parse_tool_call_arguments_decoded(self) -> None:
        raw = {
            "message": {
                "content": [],
                "tool_calls": [
                    {
                        "id": "tc2",
                        "function": {
                            "name": "calculate",
                            "arguments": '{"expression": "7*6"}',
                        },
                    }
                ],
            }
        }
        resp = cohere_parse_response(raw, "fallback")
        self.assertEqual(
            resp.tool_calls[0].arguments, {"expression": "7*6"}
        )

    def test_parse_uses_fallback_model(self) -> None:
        resp = cohere_parse_response({"message": {"content": []}}, "fb-model")
        self.assertEqual(resp.model, "fb-model")

    def test_parse_string_content(self) -> None:
        raw = {"message": {"content": "plain string answer"}}
        resp = cohere_parse_response(raw, "fb")
        self.assertEqual(resp.content, "plain string answer")


class CohereProviderTest(unittest.TestCase):
    """`CohereProvider` construction (no network)."""

    def test_api_key_from_constructor(self) -> None:
        p = CohereProvider(model="command-r", api_key="secret-key")
        self.assertEqual(p.model, "command-r")
        self.assertEqual(p._api_key, "secret-key")

    def test_api_key_from_env(self) -> None:
        import os

        os.environ["COHERE_API_KEY"] = "env-key"
        try:
            p = CohereProvider()
            self.assertEqual(p._api_key, "env-key")
        finally:
            del os.environ["COHERE_API_KEY"]


class AzureUrlTest(unittest.TestCase):
    """Azure OpenAI URL building."""

    def test_azure_chat_url_shape(self) -> None:
        url = azure_chat_url(
            "https://my-res.openai.azure.com", "gpt4o", "2024-06-01"
        )
        self.assertEqual(
            url,
            "https://my-res.openai.azure.com/openai/deployments/gpt4o"
            "/chat/completions?api-version=2024-06-01",
        )

    def test_azure_chat_url_strips_trailing_slash(self) -> None:
        url = azure_chat_url(
            "https://my-res.openai.azure.com/", "dep", "2024-06-01"
        )
        self.assertNotIn(".com//openai", url)
        self.assertIn(".com/openai/deployments/dep/", url)


class AzureProviderTest(unittest.TestCase):
    """`AzureOpenAIProvider` construction."""

    def test_construction_sets_fields(self) -> None:
        p = AzureOpenAIProvider(
            endpoint="https://res.openai.azure.com",
            deployment="my-gpt",
            api_key="azure-secret",
        )
        self.assertEqual(p.deployment, "my-gpt")
        # On Azure the model id is the deployment name.
        self.assertEqual(p.model, "my-gpt")
        self.assertEqual(p._api_key, "azure-secret")
        self.assertEqual(p.api_version, AZURE_DEFAULT_API_VERSION)

    def test_base_url_built_from_parts(self) -> None:
        p = AzureOpenAIProvider(
            endpoint="https://res.openai.azure.com",
            deployment="my-gpt",
            api_key="k",
            api_version="2025-01-01",
        )
        self.assertEqual(
            p.base_url,
            "https://res.openai.azure.com/openai/deployments/my-gpt"
            "/chat/completions?api-version=2025-01-01",
        )

    def test_api_key_from_env(self) -> None:
        import os

        os.environ["AZURE_OPENAI_KEY"] = "azure-env-key"
        try:
            p = AzureOpenAIProvider(
                endpoint="https://res.openai.azure.com",
                deployment="dep",
            )
            self.assertEqual(p._api_key, "azure-env-key")
        finally:
            del os.environ["AZURE_OPENAI_KEY"]


class CompatibleFactoryTest(unittest.TestCase):
    """The nvidia_nim / fireworks / perplexity factories."""

    def test_nvidia_nim_base_url(self) -> None:
        p = nvidia_nim("meta/llama-3.1-70b", "nv-key")
        self.assertIsInstance(p, OpenAICompatibleProvider)
        self.assertEqual(p.base_url, NVIDIA_NIM_BASE_URL)
        self.assertEqual(p.model, "meta/llama-3.1-70b")
        self.assertEqual(p._api_key, "nv-key")

    def test_nvidia_nim_base_url_override(self) -> None:
        p = nvidia_nim(
            "m", "k", base_url="http://localhost:8000/v1/chat/completions"
        )
        self.assertEqual(
            p.base_url, "http://localhost:8000/v1/chat/completions"
        )

    def test_fireworks_base_url(self) -> None:
        p = fireworks("accounts/fireworks/models/llama-v3", "fw-key")
        self.assertIsInstance(p, OpenAICompatibleProvider)
        self.assertEqual(p.base_url, FIREWORKS_BASE_URL)
        self.assertEqual(p.model, "accounts/fireworks/models/llama-v3")

    def test_perplexity_base_url(self) -> None:
        p = perplexity("sonar-pro", "pplx-key")
        self.assertIsInstance(p, OpenAICompatibleProvider)
        self.assertEqual(p.base_url, PERPLEXITY_BASE_URL)
        self.assertEqual(p.model, "sonar-pro")
        self.assertEqual(p._api_key, "pplx-key")


if __name__ == "__main__":
    unittest.main()
