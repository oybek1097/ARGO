# Memory

ARGO has a layered memory stack. Each layer has a different job — from
very-short-term conversation context to long-term structured knowledge — and
the `MemoryManager` (`argo_brain/memory/manager.py`) orchestrates them.

```
L0  working memory   — recent turns, in RAM, per user
L1  persistent       — full history, SQLite + FTS5 full-text search
L2  vector           — semantic recall by cosine similarity
L3  knowledge graph  — structured facts as subject–predicate–object triples
```

## L0 — working memory

**Module:** `argo_brain/memory/working.py`

A per-user **ring buffer** (a `collections.deque`) of the most recent
conversation turns. It is fast, bounded and in-memory only.

- Its size is set by the `working_memory_size` setting (default `200`).
- In a full deployment the canonical L0 buffer lives in `argo-core` (a Rust
  `DashMap`); the Python brain also keeps its own L0 buffer.
- When the buffer is full, the oldest turn is dropped — L0 is not durable
  storage, just a fast recent-context cache.

## L1 — persistent memory

**Module:** `argo_brain/memory/persistent.py`

A **SQLite database** with an **FTS5** full-text index. This is the durable
record of every conversation.

- The database lives at `db_path` (default `<data_dir>/argo.db`).
- Conversation history is written here and is full-text searchable.
- The agent loads up to `context_history` turns (default `20`) of L1 history
  into the prompt for each request.
- The `memory_search` tool queries this layer (see [Tools](tools.md)).

## L2 — vector memory

**Module:** `argo_brain/memory/vector.py`

A **vector store** for *semantic* recall — finding past content that is
*related in meaning* even when it shares no keywords.

- It uses a standard-library **hashing vectorizer** (no model download, no
  third-party dependency) and **cosine-similarity** search.
- Because it is hashing-based it is deterministic and cheap, at the cost of
  the precision a learned embedding model would give. A pluggable embedding
  backend is on the roadmap.

## L3 — knowledge graph

**Module:** `argo_brain/memory/graph.py`

The optional **L3** layer stores *structured facts* as a directed labeled
graph: entities (nodes) connected by predicates (edges) — i.e.
`subject --predicate--> object` triples.

- State is **partitioned per user**: each user owns an isolated set of
  entities and relations.
- The shipped implementation is a self-contained **in-memory** graph, kept
  pure-stdlib and fully deterministic.
- A real deployment could back this with a graph database (Neo4j, Memgraph);
  that integration is roadmap-only.

Where L2 retrieves *text* by similarity, L3 answers *structured* questions —
"what does ARGO know connects entity A to entity B".

## How the layers work together

For each incoming message the agent:

1. appends the turn to **L0** for immediate context;
2. loads recent history from **L1** (up to `context_history` turns) into the
   prompt;
3. can search **L1** (keyword/FTS) and **L2** (semantic) via memory tools when
   the model asks for older or related context;
4. can record and query structured facts in **L3**;
5. writes the user message and the assistant reply back to **L1** for
   durability.

## Related settings

| Setting | Default | Effect |
|---|---|---|
| `working_memory_size` | `200` | L0 ring-buffer size per user. |
| `context_history` | `20` | L1 turns loaded into the prompt. |
| `data_dir` | `~/.argo/data` | Where SQLite databases live. |
| `db_path` | `<data_dir>/argo.db` | The L1 database file. |

See [Configuration](configuration.md) for how to set these.

## See also

- [Architecture](architecture.md) — where memory sits in the request flow.
- [Tools](tools.md) — the `memory_search` and `memory_remember` tools.
