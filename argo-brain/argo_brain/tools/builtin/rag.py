"""RAG (retrieval-augmented generation) document tools — spec section 4.4.

A pure-stdlib retrieval toolset built on top of the L2 `VectorMemory`
(spec section 4.3). It provides a three-step document workflow:

  * ``document_ingest``    — chunk a document and store the chunks.
  * ``document_search``    — retrieve the most relevant chunks for a query.
  * ``document_summarize`` — produce an extractive summary of a text.

The ingest and search tools deliberately *share* a single
``VectorMemory`` instance so that whatever ``document_ingest`` writes is
immediately visible to ``document_search``. ``rag_tools()`` wires them up
with that shared memory.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from argo_brain.memory.vector import VectorMemory
from argo_brain.tools.base import Tool, ToolResult

# Tokenizer used for extractive summarization scoring.
_WORD_RE = re.compile(r"\w+", re.UNICODE)

# Naive sentence splitter: break on ., ! or ? followed by whitespace.
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")

# Common English stop words excluded from frequency scoring so that the
# summary is driven by content words rather than grammatical glue.
_STOP_WORDS = frozenset(
    """a an and are as at be but by for from has have he her his i in is it
    its of on or she that the their them they this to was were will with you
    your we our not no so if then than there here""".split()
)


def chunk_text(text: str, size: int = 500, overlap: int = 50) -> list[str]:
    """Splits ``text`` into overlapping fixed-size chunks (spec section 4.4).

    Each chunk is at most ``size`` characters long and consecutive chunks
    share ``overlap`` characters of context, so information that straddles
    a chunk boundary is still retrievable. An empty or whitespace-only text
    yields an empty list.
    """
    if size <= 0:
        raise ValueError("size must be positive")
    if overlap < 0 or overlap >= size:
        raise ValueError("overlap must be >= 0 and < size")

    text = text or ""
    if not text.strip():
        return []

    chunks: list[str] = []
    # The window advances by (size - overlap) so adjacent chunks overlap.
    step = size - overlap
    start = 0
    while start < len(text):
        chunk = text[start : start + size]
        if chunk.strip():
            chunks.append(chunk)
        if start + size >= len(text):
            break
        start += step
    return chunks


def _extractive_summary(text: str, max_sentences: int = 3) -> str:
    """Returns the most representative sentences of ``text``.

    Sentences are scored by the summed frequency of their content words
    (stop words excluded), normalized by sentence length so long sentences
    are not unfairly favoured. The top-scoring sentences are returned in
    their original document order. Pure stdlib — no LLM involved.
    """
    text = (text or "").strip()
    if not text:
        return ""

    sentences = [s.strip() for s in _SENTENCE_RE.split(text) if s.strip()]
    if len(sentences) <= max_sentences:
        return text

    # Word-frequency table over the whole document (content words only).
    freq: Counter[str] = Counter()
    for word in _WORD_RE.findall(text.lower()):
        if word not in _STOP_WORDS:
            freq[word] += 1

    scored: list[tuple[float, int, str]] = []
    for index, sentence in enumerate(sentences):
        words = [w for w in _WORD_RE.findall(sentence.lower()) if w not in _STOP_WORDS]
        if not words:
            score = 0.0
        else:
            # Length-normalized score keeps verbose sentences in check.
            score = sum(freq[w] for w in words) / len(words)
        scored.append((score, index, sentence))

    # Pick the highest-scoring sentences, then restore document order.
    top = sorted(scored, key=lambda item: item[0], reverse=True)[:max_sentences]
    top.sort(key=lambda item: item[1])
    return " ".join(sentence for _, _, sentence in top)


class DocumentIngestTool(Tool):
    """Chunks a document and stores its chunks in shared vector memory."""

    name = "document_ingest"
    description = (
        "Ingests a document by splitting it into overlapping chunks and "
        "storing them in semantic memory for later retrieval."
    )
    parameters = {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The raw document text to ingest.",
            },
            "path": {
                "type": "string",
                "description": "Path to a file to ingest instead of inline text.",
            },
            "doc_id": {
                "type": "string",
                "description": "Identifier recorded on every stored chunk.",
            },
        },
        "required": ["doc_id"],
    }

    def __init__(self, memory: VectorMemory | None = None) -> None:
        # The tool owns a VectorMemory; ingest and search share one instance.
        self.memory = memory if memory is not None else VectorMemory()

    async def run(
        self,
        user_id: str,
        text: str | None = None,
        path: str | None = None,
        doc_id: str = "",
        **kwargs,
    ) -> ToolResult:
        if not doc_id:
            return ToolResult(content="Error: doc_id is required", success=False)

        # Resolve the document body from inline text or a file path.
        if path:
            file = Path(path)
            if not file.is_file():
                return ToolResult(
                    content=f"Error: file not found: {path}", success=False
                )
            text = file.read_text(encoding="utf-8", errors="replace")
        if text is None:
            return ToolResult(
                content="Error: either 'text' or 'path' is required", success=False
            )

        chunks = chunk_text(text)
        if not chunks:
            return ToolResult(
                content=f"Document '{doc_id}' is empty; 0 chunks stored.",
                metadata={"doc_id": doc_id, "chunks": 0},
            )

        # Store each chunk, tagging it with the doc id and its position.
        for index, chunk in enumerate(chunks):
            self.memory.add(
                user_id,
                chunk,
                metadata={"doc_id": doc_id, "chunk_index": index},
            )

        return ToolResult(
            content=f"Ingested document '{doc_id}': {len(chunks)} chunk(s) stored.",
            metadata={"doc_id": doc_id, "chunks": len(chunks)},
        )


class DocumentSearchTool(Tool):
    """Retrieves the most relevant document chunks for a query."""

    name = "document_search"
    description = (
        "Searches ingested documents and returns the chunks most "
        "semantically relevant to the query."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The natural-language search query.",
            },
            "k": {
                "type": "integer",
                "description": "Maximum number of chunks to return (default 3).",
            },
        },
        "required": ["query"],
    }

    def __init__(self, memory: VectorMemory | None = None) -> None:
        # Must be the SAME instance the ingest tool writes to.
        self.memory = memory if memory is not None else VectorMemory()

    async def run(
        self,
        user_id: str,
        query: str = "",
        k: int = 3,
        **kwargs,
    ) -> ToolResult:
        if not query:
            return ToolResult(content="Error: query is required", success=False)

        hits = self.memory.search(user_id, query, k=k)
        if not hits:
            return ToolResult(
                content="No relevant chunks found.",
                metadata={"hits": 0},
            )

        # Render each hit with its score and source document id.
        lines = []
        for rank, hit in enumerate(hits, start=1):
            doc_id = hit["metadata"].get("doc_id", "?")
            lines.append(
                f"[{rank}] (doc={doc_id} score={hit['score']:.3f}) {hit['text']}"
            )

        return ToolResult(
            content="\n".join(lines),
            metadata={"hits": len(hits), "results": hits},
        )


class DocumentSummarizeTool(Tool):
    """Produces an extractive summary of a text — pure stdlib, no LLM."""

    name = "document_summarize"
    description = (
        "Summarizes a text extractively by selecting its most "
        "representative sentences via word-frequency scoring."
    )
    parameters = {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The text to summarize.",
            },
            "max_sentences": {
                "type": "integer",
                "description": "Number of sentences to keep (default 3).",
            },
        },
        "required": ["text"],
    }

    async def run(
        self,
        user_id: str,
        text: str = "",
        max_sentences: int = 3,
        **kwargs,
    ) -> ToolResult:
        if not text or not text.strip():
            return ToolResult(content="Error: text is required", success=False)

        max_sentences = max(1, max_sentences)
        summary = _extractive_summary(text, max_sentences=max_sentences)
        return ToolResult(
            content=summary,
            metadata={"max_sentences": max_sentences, "length": len(summary)},
        )


def rag_tools() -> list[Tool]:
    """Returns the RAG toolset wired with a shared `VectorMemory`.

    The ingest and search tools receive the *same* memory instance so a
    search immediately sees whatever was ingested (spec section 4.4).
    """
    memory = VectorMemory()
    return [
        DocumentIngestTool(memory=memory),
        DocumentSearchTool(memory=memory),
        DocumentSummarizeTool(),
    ]
