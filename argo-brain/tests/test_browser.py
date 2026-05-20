"""Tests for the browser / HTML-scraping tools — spec section 4.4.

All tests run OFFLINE: they feed sample HTML strings via the `html`
parameter (or the pure parser helpers) so the network is never touched.
"""

from __future__ import annotations

import unittest

from argo_brain.tools.builtin.browser import (
    ExtractFormsTool,
    ExtractLinksTool,
    ExtractMetadataTool,
    ExtractTablesTool,
    ExtractTextTool,
    browser_tools,
    parse_forms,
    parse_links,
    parse_metadata,
    parse_tables,
    tables_to_text,
)

_LINKS_HTML = """
<html><body>
  <a href="/home">Home</a>
  <a href="https://example.com/about">About Us</a>
  <a href="contact.html"><span>Contact</span></a>
  <p>not a link</p>
</body></html>
"""

_TABLE_HTML = """
<table>
  <tr><th>Name</th><th>Age</th></tr>
  <tr><td>Alice</td><td>30</td></tr>
  <tr><td>Bob</td><td>25</td></tr>
</table>
"""

_META_HTML = """
<html><head>
  <title>Sample Page</title>
  <meta name="description" content="A sample description.">
  <meta property="og:title" content="OG Sample">
  <meta property="og:image" content="https://example.com/img.png">
</head><body>x</body></html>
"""

_FORM_HTML = """
<form action="/login" method="POST">
  <input type="text" name="username">
  <input type="password" name="password">
  <button type="submit">Go</button>
</form>
"""

_TEXT_HTML = """
<html><head><style>.x{color:red}</style></head>
<body><h1>Title</h1><p>Hello&nbsp;world.</p><script>bad()</script></body></html>
"""


class ParseLinksTests(unittest.TestCase):
    def test_finds_all_links(self):
        links = parse_links(_LINKS_HTML)
        self.assertEqual(len(links), 3)

    def test_anchor_text_extracted(self):
        links = parse_links(_LINKS_HTML)
        self.assertEqual(links[0], {"href": "/home", "text": "Home"})
        self.assertEqual(links[2]["text"], "Contact")

    def test_base_url_resolution(self):
        links = parse_links(_LINKS_HTML, base_url="https://site.org/dir/")
        self.assertEqual(links[0]["href"], "https://site.org/home")
        self.assertEqual(links[2]["href"], "https://site.org/dir/contact.html")


class ParseTablesTests(unittest.TestCase):
    def test_table_matrix(self):
        tables = parse_tables(_TABLE_HTML)
        self.assertEqual(len(tables), 1)
        self.assertEqual(tables[0][0], ["Name", "Age"])
        self.assertEqual(tables[0][2], ["Bob", "25"])

    def test_tables_to_text_grid(self):
        text = tables_to_text(parse_tables(_TABLE_HTML))
        self.assertIn("Table 1:", text)
        self.assertIn("Alice", text)
        self.assertIn("|", text)


class ParseMetadataTests(unittest.TestCase):
    def test_title(self):
        data = parse_metadata(_META_HTML)
        self.assertEqual(data["title"], "Sample Page")

    def test_meta_tags(self):
        data = parse_metadata(_META_HTML)
        self.assertEqual(data["meta"]["description"], "A sample description.")
        self.assertEqual(data["meta"]["og:title"], "OG Sample")


class ParseFormsTests(unittest.TestCase):
    def test_form_action_method(self):
        forms = parse_forms(_FORM_HTML)
        self.assertEqual(len(forms), 1)
        self.assertEqual(forms[0]["action"], "/login")
        self.assertEqual(forms[0]["method"], "post")

    def test_form_fields(self):
        fields = parse_forms(_FORM_HTML)[0]["fields"]
        names = [f["name"] for f in fields]
        self.assertIn("username", names)
        self.assertIn("password", names)


class MalformedHtmlTests(unittest.TestCase):
    def test_unclosed_tags_links(self):
        # Missing </a> and </body> must not raise.
        links = parse_links("<a href='/x'>X<a href='/y'>Y")
        self.assertEqual([link["href"] for link in links], ["/x", "/y"])

    def test_empty_and_garbage(self):
        self.assertEqual(parse_links(""), [])
        self.assertEqual(parse_tables("<<<not html>>>"), [])
        self.assertEqual(parse_metadata("").get("title"), "")
        self.assertEqual(parse_forms("<form>"), [])


class BrowserToolsTests(unittest.IsolatedAsyncioTestCase):
    async def test_extract_links_tool(self):
        result = await ExtractLinksTool().run("u", html=_LINKS_HTML)
        self.assertTrue(result.success)
        self.assertIn("About Us -> https://example.com/about", result.content)
        self.assertEqual(result.metadata["count"], 3)

    async def test_extract_tables_tool(self):
        result = await ExtractTablesTool().run("u", html=_TABLE_HTML)
        self.assertTrue(result.success)
        self.assertIn("Alice", result.content)
        self.assertEqual(result.metadata["count"], 1)

    async def test_extract_metadata_tool(self):
        result = await ExtractMetadataTool().run("u", html=_META_HTML)
        self.assertTrue(result.success)
        self.assertIn("title: Sample Page", result.content)
        self.assertIn("og:image", result.content)

    async def test_extract_text_tool(self):
        result = await ExtractTextTool().run("u", html=_TEXT_HTML)
        self.assertTrue(result.success)
        self.assertIn("Hello world.", result.content)
        self.assertNotIn("bad()", result.content)

    async def test_extract_forms_tool(self):
        result = await ExtractFormsTool().run("u", html=_FORM_HTML)
        self.assertTrue(result.success)
        self.assertIn("method=POST", result.content)
        self.assertIn("username", result.content)

    async def test_missing_args_fails_gracefully(self):
        result = await ExtractLinksTool().run("u")
        self.assertFalse(result.success)
        self.assertIn("must be provided", result.content)

    async def test_no_results_messages(self):
        links = await ExtractLinksTool().run("u", html="<p>none</p>")
        tables = await ExtractTablesTool().run("u", html="<p>none</p>")
        forms = await ExtractFormsTool().run("u", html="<p>none</p>")
        self.assertEqual(links.content, "No links found.")
        self.assertEqual(tables.content, "No tables found.")
        self.assertEqual(forms.content, "No forms found.")

    async def test_browser_tools_registry(self):
        tools = browser_tools()
        names = {t.name for t in tools}
        self.assertEqual(
            names,
            {"extract_links", "extract_tables", "extract_metadata",
             "extract_text", "extract_forms"},
        )


if __name__ == "__main__":
    unittest.main()
