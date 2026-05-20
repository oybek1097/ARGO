"""Offline tests for the OpenAI and Gemini providers — spec section 4.8.

These tests exercise the message-conversion and response-parsing helpers
directly; no network access is performed. The HTTP layer (`complete()`) is
deliberately not invoked here.
"""

from __future__ import annotations

import json
import unittest

from argo_brain.providers.gemini import (
    GeminiProvider,
    convert_messages as gemini_convert,
    convert_tools as gemini_convert_tools,
    extract_system as gemini_extract_system,
    parse_response as gemini_parse,
)
from argo_brain.providers.openai import (
    OpenAIProvider,
    convert_messages as openai_convert,
    parse_response as openai_parse,
)


class OpenAIConversionTests(unittest.TestCase):
    """Internal-format -> OpenAI Chat Completions conversion."""

    def test_system_and_user_mapping(self) -> None:
        out = openai_convert(
            [
                {"role": "system", "content": "be helpful"},
                {"role": "user", "content": "hello"},
            ]
        )
        self.assertEqual(out[0], {"role": "system", "content": "be helpful"})
        self.assertEqual(out[1], {"role": "user", "content": "hello"})

    def test_assistant_plain_text(self) -> None:
        out = openai_convert([{"role": "assistant", "content": "hi there"}])
        self.assertEqual(out[0]["role"], "assistant")
        self.assertEqual(out[0]["content"], "hi there")
        self.assertNotIn("tool_calls", out[0])

    def test_assistant_tool_calls_mapping(self) -> None:
        out = openai_convert(
            [
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "name": "calculate",
                            "arguments": {"expression": "2+2"},
                        }
                    ],
                }
            ]
        )
        msg = out[0]
        self.assertIsNone(msg["content"])
        self.assertEqual(len(msg["tool_calls"]), 1)
        call = msg["tool_calls"][0]
        self.assertEqual(call["id"], "call_1")
        self.assertEqual(call["type"], "function")
        self.assertEqual(call["function"]["name"], "calculate")
        # Arguments must be serialised to a JSON string for OpenAI.
        self.assertEqual(
            json.loads(call["function"]["arguments"]), {"expression": "2+2"}
        )

    def test_tool_result_mapping(self) -> None:
        out = openai_convert(
            [
                {
                    "role": "tool",
                    "tool_call_id": "call_1",
                    "content": "4",
                }
            ]
        )
        self.assertEqual(
            out[0],
            {"role": "tool", "tool_call_id": "call_1", "content": "4"},
        )

    def test_parse_text_response(self) -> None:
        raw = {
            "model": "gpt-4o",
            "choices": [{"message": {"content": "the answer is 4"}}],
        }
        resp = openai_parse(raw, "fallback")
        self.assertEqual(resp.content, "the answer is 4")
        self.assertFalse(resp.has_tool_calls)
        self.assertEqual(resp.model, "gpt-4o")

    def test_parse_tool_call_response(self) -> None:
        raw = {
            "model": "gpt-4o",
            "choices": [
                {
                    "message": {
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_9",
                                "function": {
                                    "name": "current_time",
                                    "arguments": '{"tz": "UTC"}',
                                },
                            }
                        ],
                    }
                }
            ],
        }
        resp = openai_parse(raw, "fallback")
        self.assertEqual(resp.content, "")
        self.assertTrue(resp.has_tool_calls)
        self.assertEqual(resp.tool_calls[0].name, "current_time")
        self.assertEqual(resp.tool_calls[0].arguments, {"tz": "UTC"})

    def test_parse_malformed_arguments(self) -> None:
        raw = {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "id": "call_x",
                                "function": {
                                    "name": "noop",
                                    "arguments": "not-json",
                                },
                            }
                        ]
                    }
                }
            ]
        }
        resp = openai_parse(raw, "fallback")
        # Invalid JSON arguments degrade gracefully to an empty dict.
        self.assertEqual(resp.tool_calls[0].arguments, {})

    def test_constructor_uses_explicit_key_and_alias(self) -> None:
        provider = OpenAIProvider(model="gpt", api_key="sk-test")
        self.assertEqual(provider.model, "gpt-4o")
        self.assertEqual(provider._api_key, "sk-test")


class GeminiConversionTests(unittest.TestCase):
    """Internal-format -> Gemini `contents` conversion."""

    def test_extract_system(self) -> None:
        system = gemini_extract_system(
            [
                {"role": "system", "content": "rule one"},
                {"role": "system", "content": "rule two"},
                {"role": "user", "content": "ignored"},
            ]
        )
        self.assertEqual(system, "rule one\n\nrule two")

    def test_system_excluded_from_contents(self) -> None:
        contents = gemini_convert(
            [
                {"role": "system", "content": "rule"},
                {"role": "user", "content": "hi"},
            ]
        )
        # The system message is handled separately, not as a `content`.
        self.assertEqual(len(contents), 1)
        self.assertEqual(contents[0]["role"], "user")

    def test_user_mapping(self) -> None:
        contents = gemini_convert([{"role": "user", "content": "hello"}])
        self.assertEqual(
            contents[0],
            {"role": "user", "parts": [{"text": "hello"}]},
        )

    def test_assistant_text_uses_model_role(self) -> None:
        contents = gemini_convert(
            [{"role": "assistant", "content": "response"}]
        )
        self.assertEqual(contents[0]["role"], "model")
        self.assertEqual(contents[0]["parts"], [{"text": "response"}])

    def test_assistant_tool_calls_become_function_calls(self) -> None:
        contents = gemini_convert(
            [
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "name": "calculate",
                            "arguments": {"expression": "1+1"},
                        }
                    ],
                }
            ]
        )
        parts = contents[0]["parts"]
        self.assertEqual(len(parts), 1)
        self.assertEqual(
            parts[0]["functionCall"],
            {"name": "calculate", "args": {"expression": "1+1"}},
        )

    def test_tool_result_becomes_function_response(self) -> None:
        contents = gemini_convert(
            [
                {
                    "role": "tool",
                    "name": "calculate",
                    "content": "2",
                }
            ]
        )
        part = contents[0]["parts"][0]["functionResponse"]
        self.assertEqual(part["name"], "calculate")
        self.assertEqual(part["response"], {"result": "2"})
        self.assertEqual(contents[0]["role"], "user")

    def test_convert_tools(self) -> None:
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "calculate",
                    "description": "do math",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ]
        out = gemini_convert_tools(tools)
        self.assertEqual(len(out), 1)
        decls = out[0]["functionDeclarations"]
        self.assertEqual(decls[0]["name"], "calculate")
        self.assertEqual(decls[0]["description"], "do math")

    def test_parse_text_response(self) -> None:
        raw = {
            "modelVersion": "gemini-1.5-flash",
            "candidates": [
                {"content": {"parts": [{"text": "hello "}, {"text": "world"}]}}
            ],
        }
        resp = gemini_parse(raw, "fallback")
        self.assertEqual(resp.content, "hello world")
        self.assertFalse(resp.has_tool_calls)
        self.assertEqual(resp.model, "gemini-1.5-flash")

    def test_parse_function_call_response(self) -> None:
        raw = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "functionCall": {
                                    "name": "current_time",
                                    "args": {"tz": "UTC"},
                                }
                            }
                        ]
                    }
                }
            ]
        }
        resp = gemini_parse(raw, "fallback")
        self.assertTrue(resp.has_tool_calls)
        call = resp.tool_calls[0]
        self.assertEqual(call.name, "current_time")
        self.assertEqual(call.arguments, {"tz": "UTC"})
        self.assertEqual(call.id, "call_current_time")

    def test_constructor_uses_explicit_key_and_alias(self) -> None:
        provider = GeminiProvider(model="gemini-pro", api_key="g-test")
        self.assertEqual(provider.model, "gemini-1.5-pro")
        self.assertEqual(provider._api_key, "g-test")


if __name__ == "__main__":
    unittest.main()
