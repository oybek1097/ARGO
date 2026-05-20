"""Unit tests for the OpenAPI spec generator — spec section 6."""

from __future__ import annotations

import json
import re
import unittest

from argo_brain.api.openapi import build_openapi_spec, openapi_json


def _collect_refs(node, found):
    """Recursively collects every `$ref` string found in a spec node."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "$ref" and isinstance(value, str):
                found.append(value)
            else:
                _collect_refs(value, found)
    elif isinstance(node, list):
        for item in node:
            _collect_refs(item, found)


class TestOpenAPISpec(unittest.TestCase):
    """Validates the structure produced by build_openapi_spec()."""

    def setUp(self) -> None:
        self.spec = build_openapi_spec()

    def test_returns_dict(self) -> None:
        """build_openapi_spec() must return a dict."""
        self.assertIsInstance(self.spec, dict)

    def test_openapi_version_is_3_1_x(self) -> None:
        """The `openapi` field must declare a 3.1.x version."""
        self.assertIn("openapi", self.spec)
        self.assertRegex(self.spec["openapi"], r"^3\.1\.\d+$")

    def test_info_has_title_and_version(self) -> None:
        """The info object must carry the expected title and a version."""
        info = self.spec["info"]
        self.assertEqual(info["title"], "ARGO Agent API")
        self.assertIn("version", info)
        self.assertTrue(info["version"])

    def test_paths_non_empty(self) -> None:
        """The paths object must exist and contain entries."""
        self.assertIn("paths", self.spec)
        self.assertIsInstance(self.spec["paths"], dict)
        self.assertGreater(len(self.spec["paths"]), 0)

    def test_chat_post_present(self) -> None:
        """/api/chat must expose a POST operation."""
        self.assertIn("/api/chat", self.spec["paths"])
        self.assertIn("post", self.spec["paths"]["/api/chat"])

    def test_health_get_present(self) -> None:
        """/api/health must expose a GET operation."""
        self.assertIn("/api/health", self.spec["paths"])
        self.assertIn("get", self.spec["paths"]["/api/health"])

    def test_all_expected_endpoints_present(self) -> None:
        """Every gateway endpoint must be described."""
        for path in (
            "/api/health",
            "/api/version",
            "/api/chat",
            "/api/history",
            "/webhook/{platform}",
        ):
            self.assertIn(path, self.spec["paths"])

    def test_components_schemas_present(self) -> None:
        """A non-empty components/schemas section must exist."""
        self.assertIn("components", self.spec)
        self.assertIn("schemas", self.spec["components"])
        self.assertGreater(len(self.spec["components"]["schemas"]), 0)

    def test_chat_request_response_schemas_defined(self) -> None:
        """The chat request/response shapes must be defined as components."""
        schemas = self.spec["components"]["schemas"]
        self.assertIn("ChatRequest", schemas)
        self.assertIn("ChatResponse", schemas)
        # ChatResponse must include the AgentResponse fields.
        props = schemas["ChatResponse"]["properties"]
        for field in ("content", "language", "model", "tools_used"):
            self.assertIn(field, props)

    def test_schemas_referenced_via_ref(self) -> None:
        """The spec must reference component schemas with $ref."""
        refs: list[str] = []
        _collect_refs(self.spec, refs)
        self.assertGreater(len(refs), 0)
        self.assertIn("#/components/schemas/ChatRequest", refs)

    def test_all_refs_point_to_existing_components(self) -> None:
        """Every $ref must resolve to an existing component schema."""
        refs: list[str] = []
        _collect_refs(self.spec, refs)
        defined = set(self.spec["components"]["schemas"])
        prefix = "#/components/schemas/"
        for ref in refs:
            self.assertTrue(ref.startswith(prefix), f"unexpected ref: {ref}")
            name = ref[len(prefix):]
            self.assertIn(name, defined, f"dangling $ref: {ref}")

    def test_webhook_has_platform_path_parameter(self) -> None:
        """The webhook endpoint must declare its `platform` path parameter."""
        params = self.spec["paths"]["/webhook/{platform}"]["post"]["parameters"]
        names = {p["name"]: p for p in params}
        self.assertIn("platform", names)
        self.assertEqual(names["platform"]["in"], "path")
        self.assertTrue(names["platform"]["required"])

    def test_history_has_user_id_query_parameter(self) -> None:
        """/api/history must declare a `user_id` query parameter."""
        params = self.spec["paths"]["/api/history"]["get"]["parameters"]
        names = {p["name"]: p for p in params}
        self.assertIn("user_id", names)
        self.assertEqual(names["user_id"]["in"], "query")

    def test_chat_post_has_request_body(self) -> None:
        """The chat POST operation must declare a JSON request body."""
        post = self.spec["paths"]["/api/chat"]["post"]
        self.assertIn("requestBody", post)
        schema = post["requestBody"]["content"]["application/json"]["schema"]
        self.assertEqual(schema["$ref"], "#/components/schemas/ChatRequest")

    def test_openapi_json_round_trips(self) -> None:
        """openapi_json() must produce valid JSON equal to the source spec."""
        text = openapi_json()
        self.assertIsInstance(text, str)
        parsed = json.loads(text)
        self.assertEqual(parsed, self.spec)

    def test_openapi_json_is_valid_json(self) -> None:
        """openapi_json() output must parse without error."""
        # json.loads raises on malformed input; reaching the assert means OK.
        parsed = json.loads(openapi_json())
        self.assertIsInstance(parsed, dict)

    def test_operations_have_responses(self) -> None:
        """Every operation must define at least one response."""
        for path, methods in self.spec["paths"].items():
            for method, op in methods.items():
                self.assertIn("responses", op, f"{method} {path} missing responses")
                self.assertGreater(len(op["responses"]), 0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
