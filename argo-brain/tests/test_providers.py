"""LLM provider tests (offline — no network calls)."""

import unittest

from argo_brain.providers.anthropic import _split_messages


class TestAnthropicMessageConversion(unittest.TestCase):
    def test_system_extracted(self):
        system, conv = _split_messages(
            [{"role": "system", "content": "be brief"},
             {"role": "user", "content": "hi"}]
        )
        self.assertEqual(system, "be brief")
        self.assertEqual(conv, [{"role": "user", "content": "hi"}])

    def test_assistant_tool_calls_become_blocks(self):
        _, conv = _split_messages(
            [{"role": "assistant", "content": "let me check",
              "tool_calls": [{"id": "t1", "name": "calc", "arguments": {"x": 1}}]}]
        )
        blocks = conv[0]["content"]
        self.assertEqual(blocks[0]["type"], "text")
        self.assertEqual(blocks[1]["type"], "tool_use")
        self.assertEqual(blocks[1]["id"], "t1")

    def test_tool_result_becomes_user_block(self):
        _, conv = _split_messages(
            [{"role": "tool", "tool_call_id": "t1", "content": "result"}]
        )
        self.assertEqual(conv[0]["role"], "user")
        self.assertEqual(conv[0]["content"][0]["type"], "tool_result")
        self.assertEqual(conv[0]["content"][0]["tool_use_id"], "t1")

    def test_consecutive_tool_results_merge(self):
        _, conv = _split_messages(
            [{"role": "tool", "tool_call_id": "a", "content": "r1"},
             {"role": "tool", "tool_call_id": "b", "content": "r2"}]
        )
        self.assertEqual(len(conv), 1)
        self.assertEqual(len(conv[0]["content"]), 2)


if __name__ == "__main__":
    unittest.main()
