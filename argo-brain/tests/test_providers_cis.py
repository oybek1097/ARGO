"""CIS-region LLM provider tests — spec section 4.8 (offline — no network).

Covers the two Russia-data-residency providers added in `providers/cis.py`:
`YandexGPTProvider` (Yandex Foundation Models) and `GigaChatProvider`
(SberCloud GigaChat).  All tests are OFFLINE: only message conversion,
provider construction and the `model` attribute are exercised — no HTTP
request is ever made.
"""

import os
import unittest

from argo_brain.providers.cis import (
    GigaChatProvider,
    YandexGPTProvider,
    convert_messages_gigachat,
    convert_messages_yandex,
    parse_response_gigachat,
    parse_response_yandex,
)


class TestYandexMessageConversion(unittest.TestCase):
    """Message conversion for the YandexGPT completion format."""

    def test_system_role_mapped(self):
        out = convert_messages_yandex(
            [{"role": "system", "content": "be brief"}]
        )
        self.assertEqual(out, [{"role": "system", "text": "be brief"}])

    def test_user_role_mapped(self):
        out = convert_messages_yandex([{"role": "user", "content": "hi"}])
        self.assertEqual(out, [{"role": "user", "text": "hi"}])

    def test_assistant_role_mapped(self):
        out = convert_messages_yandex(
            [{"role": "assistant", "content": "hello there"}]
        )
        self.assertEqual(out, [{"role": "assistant", "text": "hello there"}])

    def test_full_conversation_order_preserved(self):
        out = convert_messages_yandex(
            [
                {"role": "system", "content": "sys"},
                {"role": "user", "content": "q"},
                {"role": "assistant", "content": "a"},
            ]
        )
        self.assertEqual([m["role"] for m in out], ["system", "user", "assistant"])
        self.assertTrue(all("text" in m for m in out))

    def test_tool_result_folded_back_as_user(self):
        # YandexGPT completion API has no tool role; results return as user.
        out = convert_messages_yandex(
            [{"role": "tool", "tool_call_id": "t1", "content": "42"}]
        )
        self.assertEqual(out[0]["role"], "user")
        self.assertIn("42", out[0]["text"])

    def test_assistant_tool_calls_flattened_to_text(self):
        out = convert_messages_yandex(
            [
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {"id": "t1", "name": "calc", "arguments": {"x": 1}}
                    ],
                }
            ]
        )
        self.assertEqual(out[0]["role"], "assistant")
        self.assertIn("calc", out[0]["text"])


class TestGigaChatMessageConversion(unittest.TestCase):
    """Message conversion for the GigaChat chat-completions format."""

    def test_system_role_mapped(self):
        out = convert_messages_gigachat(
            [{"role": "system", "content": "be brief"}]
        )
        self.assertEqual(out, [{"role": "system", "content": "be brief"}])

    def test_user_role_mapped(self):
        out = convert_messages_gigachat([{"role": "user", "content": "hi"}])
        self.assertEqual(out, [{"role": "user", "content": "hi"}])

    def test_assistant_role_mapped(self):
        out = convert_messages_gigachat(
            [{"role": "assistant", "content": "hello"}]
        )
        self.assertEqual(out, [{"role": "assistant", "content": "hello"}])

    def test_tool_result_folded_back_as_user(self):
        out = convert_messages_gigachat(
            [{"role": "tool", "tool_call_id": "t1", "content": "result"}]
        )
        self.assertEqual(out[0]["role"], "user")
        self.assertIn("result", out[0]["content"])

    def test_assistant_tool_calls_flattened_to_text(self):
        out = convert_messages_gigachat(
            [
                {
                    "role": "assistant",
                    "content": "thinking",
                    "tool_calls": [
                        {"id": "t1", "name": "search", "arguments": {}}
                    ],
                }
            ]
        )
        self.assertEqual(out[0]["role"], "assistant")
        self.assertIn("search", out[0]["content"])

    def test_full_conversation_order_preserved(self):
        out = convert_messages_gigachat(
            [
                {"role": "system", "content": "sys"},
                {"role": "user", "content": "q"},
                {"role": "assistant", "content": "a"},
            ]
        )
        self.assertEqual(
            [m["role"] for m in out], ["system", "user", "assistant"]
        )


class TestResponseParsing(unittest.TestCase):
    """Offline parsing of canned raw responses."""

    def test_parse_yandex_response(self):
        raw = {
            "result": {
                "alternatives": [
                    {"message": {"role": "assistant", "text": "privet"}}
                ],
                "modelVersion": "yandexgpt/rc",
            }
        }
        resp = parse_response_yandex(raw, "yandexgpt")
        self.assertEqual(resp.content, "privet")
        self.assertEqual(resp.model, "yandexgpt/rc")
        self.assertFalse(resp.has_tool_calls)

    def test_parse_yandex_empty_response(self):
        resp = parse_response_yandex({}, "yandexgpt")
        self.assertEqual(resp.content, "")
        self.assertEqual(resp.model, "yandexgpt")

    def test_parse_gigachat_response(self):
        raw = {
            "choices": [{"message": {"role": "assistant", "content": "hi"}}],
            "model": "GigaChat",
        }
        resp = parse_response_gigachat(raw, "GigaChat")
        self.assertEqual(resp.content, "hi")
        self.assertEqual(resp.model, "GigaChat")

    def test_parse_gigachat_empty_response(self):
        resp = parse_response_gigachat({}, "GigaChat")
        self.assertEqual(resp.content, "")
        self.assertEqual(resp.model, "GigaChat")


class TestYandexProviderConstruction(unittest.TestCase):
    """Construction of `YandexGPTProvider` with explicit and env credentials."""

    def test_explicit_credentials(self):
        p = YandexGPTProvider(api_key="explicit-key", folder_id="folder-123")
        self.assertEqual(p._api_key, "explicit-key")
        self.assertEqual(p._folder_id, "folder-123")

    def test_credentials_from_env(self):
        os.environ["YANDEX_API_KEY"] = "env-key"
        os.environ["YANDEX_FOLDER_ID"] = "env-folder"
        try:
            p = YandexGPTProvider()
            self.assertEqual(p._api_key, "env-key")
            self.assertEqual(p._folder_id, "env-folder")
        finally:
            del os.environ["YANDEX_API_KEY"]
            del os.environ["YANDEX_FOLDER_ID"]

    def test_explicit_overrides_env(self):
        os.environ["YANDEX_API_KEY"] = "env-key"
        try:
            p = YandexGPTProvider(api_key="explicit-key", folder_id="f")
            self.assertEqual(p._api_key, "explicit-key")
        finally:
            del os.environ["YANDEX_API_KEY"]

    def test_default_model_attribute(self):
        p = YandexGPTProvider(folder_id="f")
        self.assertEqual(p.model, "yandexgpt")

    def test_model_alias_resolved(self):
        p = YandexGPTProvider(model="yagpt", folder_id="f")
        self.assertEqual(p.model, "yandexgpt")

    def test_model_uri_built_from_folder_and_model(self):
        p = YandexGPTProvider(model="yandexgpt", folder_id="folder-xyz")
        self.assertEqual(p.model_uri, "gpt://folder-xyz/yandexgpt")


class TestGigaChatProviderConstruction(unittest.TestCase):
    """Construction of `GigaChatProvider` with explicit and env credentials."""

    def test_explicit_token(self):
        p = GigaChatProvider(access_token="explicit-token")
        self.assertEqual(p._access_token, "explicit-token")

    def test_token_from_env(self):
        os.environ["GIGACHAT_TOKEN"] = "env-token"
        try:
            p = GigaChatProvider()
            self.assertEqual(p._access_token, "env-token")
        finally:
            del os.environ["GIGACHAT_TOKEN"]

    def test_explicit_overrides_env(self):
        os.environ["GIGACHAT_TOKEN"] = "env-token"
        try:
            p = GigaChatProvider(access_token="explicit-token")
            self.assertEqual(p._access_token, "explicit-token")
        finally:
            del os.environ["GIGACHAT_TOKEN"]

    def test_default_model_attribute(self):
        p = GigaChatProvider()
        self.assertEqual(p.model, "GigaChat")

    def test_model_alias_resolved(self):
        p = GigaChatProvider(model="gigachat-pro")
        self.assertEqual(p.model, "GigaChat-Pro")


if __name__ == "__main__":
    unittest.main()
