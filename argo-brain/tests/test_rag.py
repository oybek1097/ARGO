"""RAG document tool tests (spec section 4.4).

Covers the chunking helper, the ingest -> search retrieval workflow,
per-user isolation, extractive summarization and the shared-memory wiring
returned by `rag_tools()`.
"""

import unittest

from argo_brain.memory.vector import VectorMemory
from argo_brain.tools.builtin.rag import (
    DocumentIngestTool,
    DocumentSearchTool,
    DocumentSummarizeTool,
    chunk_text,
    rag_tools,
)

# A document long enough to span several chunks; the kubernetes paragraph
# is distinct from the cooking paragraph so retrieval can be checked.
_DOC = (
    "Kubernetes orchestrates containerized workloads across a cluster. "
    "It schedules pods onto nodes and restarts failed containers. "
    "The control plane reconciles desired state with observed state. "
    "Operators deploy applications by applying declarative manifests. "
    "Vault stores secrets and issues short-lived dynamic credentials. "
    "A baker prepares dough by mixing flour, water, yeast and salt. "
    "The dough must rest and rise before it is shaped into loaves. "
    "Sourdough relies on a wild yeast starter cultivated over many days."
)


class TestChunkText(unittest.TestCase):
    def test_overlapping_chunks_of_right_size(self):
        # Each chunk respects the size cap.
        text = "x" * 1200
        chunks = chunk_text(text, size=500, overlap=50)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 500)

    def test_chunks_actually_overlap(self):
        # The tail of one chunk reappears at the head of the next.
        text = "".join(chr(ord("a") + (i % 26)) for i in range(1100))
        chunks = chunk_text(text, size=500, overlap=50)
        self.assertEqual(chunks[0][-50:], chunks[1][:50])

    def test_chunks_cover_whole_text(self):
        # Reconstructing without the overlap yields the original text.
        text = "abcdefghij" * 120  # 1200 chars
        chunks = chunk_text(text, size=500, overlap=50)
        rebuilt = chunks[0] + "".join(c[50:] for c in chunks[1:])
        self.assertEqual(rebuilt, text)

    def test_short_text_single_chunk(self):
        chunks = chunk_text("a short document", size=500, overlap=50)
        self.assertEqual(chunks, ["a short document"])

    def test_empty_text_yields_no_chunks(self):
        self.assertEqual(chunk_text("", size=500, overlap=50), [])
        self.assertEqual(chunk_text("    ", size=500, overlap=50), [])

    def test_invalid_arguments_rejected(self):
        with self.assertRaises(ValueError):
            chunk_text("text", size=0)
        with self.assertRaises(ValueError):
            chunk_text("text", size=100, overlap=100)


class TestDocumentIngest(unittest.IsolatedAsyncioTestCase):
    async def test_ingest_returns_chunk_count(self):
        tool = DocumentIngestTool(memory=VectorMemory())
        result = await tool("u1", text="word " * 400, doc_id="d1")
        self.assertTrue(result.success)
        self.assertGreater(result.metadata["chunks"], 1)

    async def test_ingest_requires_doc_id(self):
        tool = DocumentIngestTool(memory=VectorMemory())
        result = await tool("u1", text="hello", doc_id="")
        self.assertFalse(result.success)

    async def test_ingest_requires_text_or_path(self):
        tool = DocumentIngestTool(memory=VectorMemory())
        result = await tool("u1", doc_id="d1")
        self.assertFalse(result.success)

    async def test_ingest_from_file_path(self):
        import tempfile
        from pathlib import Path

        tool = DocumentIngestTool(memory=VectorMemory())
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "doc.txt"
            path.write_text(_DOC, encoding="utf-8")
            result = await tool("u1", path=str(path), doc_id="from-file")
        self.assertTrue(result.success)
        self.assertGreaterEqual(result.metadata["chunks"], 1)


class TestIngestSearchWorkflow(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.memory = VectorMemory()
        self.ingest = DocumentIngestTool(memory=self.memory)
        self.search = DocumentSearchTool(memory=self.memory)

    async def test_search_finds_relevant_chunk(self):
        await self.ingest("u1", text=_DOC, doc_id="manual")
        result = await self.search("u1", query="kubernetes pods cluster nodes")
        self.assertTrue(result.success)
        # The retrieved text should be about kubernetes, not baking.
        self.assertIn("ubernetes", result.content)

    async def test_search_distinguishes_topics(self):
        await self.ingest("u1", text=_DOC, doc_id="manual")
        result = await self.search("u1", query="sourdough yeast flour dough baker")
        self.assertTrue(result.success)
        top = result.metadata["results"][0]["text"].lower()
        self.assertTrue("dough" in top or "yeast" in top or "flour" in top)

    async def test_search_without_ingest_is_empty(self):
        result = await self.search("u-empty", query="anything")
        self.assertTrue(result.success)
        self.assertEqual(result.metadata["hits"], 0)

    async def test_search_requires_query(self):
        result = await self.search("u1", query="")
        self.assertFalse(result.success)

    async def test_per_user_isolation(self):
        await self.ingest("alice", text="alice secret deployment notes", doc_id="a")
        await self.ingest("bob", text="bob private vault credentials", doc_id="b")
        hit = await self.search("alice", query="secret deployment notes")
        self.assertIn("alice", hit.content)
        self.assertNotIn("bob private", hit.content)


class TestDocumentSummarize(unittest.IsolatedAsyncioTestCase):
    async def test_summary_is_shorter(self):
        tool = DocumentSummarizeTool()
        result = await tool("u1", text=_DOC, max_sentences=2)
        self.assertTrue(result.success)
        self.assertLess(len(result.content), len(_DOC))

    async def test_summary_contains_key_sentences(self):
        tool = DocumentSummarizeTool()
        result = await tool("u1", text=_DOC, max_sentences=3)
        # Returned sentences must be drawn verbatim from the source.
        for sentence in result.content.split(". "):
            self.assertIn(sentence.split(".")[0][:20], _DOC)

    async def test_summary_requires_text(self):
        tool = DocumentSummarizeTool()
        result = await tool("u1", text="   ")
        self.assertFalse(result.success)

    async def test_short_text_returned_whole(self):
        tool = DocumentSummarizeTool()
        text = "Only one sentence here."
        result = await tool("u1", text=text, max_sentences=3)
        self.assertEqual(result.content, text)


class TestRagToolsWiring(unittest.IsolatedAsyncioTestCase):
    async def test_rag_tools_returns_three_tools(self):
        tools = rag_tools()
        names = {t.name for t in tools}
        self.assertEqual(
            names, {"document_ingest", "document_search", "document_summarize"}
        )

    async def test_ingest_and_search_share_memory(self):
        tools = {t.name: t for t in rag_tools()}
        ingest = tools["document_ingest"]
        search = tools["document_search"]
        # The two tools must point at the very same VectorMemory object.
        self.assertIs(ingest.memory, search.memory)

        await ingest("u1", text=_DOC, doc_id="shared")
        result = await search("u1", query="kubernetes cluster pods")
        self.assertGreater(result.metadata["hits"], 0)


if __name__ == "__main__":
    unittest.main()
