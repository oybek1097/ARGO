"""L3 — knowledge-graph memory.

Spec section 4.3: `KnowledgeGraph` is the optional L3 layer of the unified
memory stack (L0 working, L1 persistent, L2 vector). Where L2 retrieves text
by semantic similarity, L3 stores *structured* facts as a directed labeled
graph: entities (nodes) connected by predicates (edges).

A real deployment might back this with a graph database (Neo4j, Memgraph).
To keep the project pure-stdlib and fully deterministic, this module ships a
self-contained in-memory graph scoped per user. Each user owns an isolated
set of entities and relations.
"""

from __future__ import annotations

from collections import defaultdict, deque


class KnowledgeGraph:
    """L3 knowledge-graph memory — per-user directed labeled graph.

    Entities are nodes keyed by name; relations are directed edges labeled
    with a predicate (a `subject --predicate--> object` triple). All state
    lives in memory and is strictly partitioned by `user_id`.
    """

    def __init__(self) -> None:
        # user_id -> {entity name -> {"name": str, "kind": str}}
        self._entities: dict[str, dict[str, dict]] = defaultdict(dict)
        # user_id -> list of relation dicts
        # Each relation: {"subject": str, "predicate": str, "object": str}
        self._relations: dict[str, list[dict]] = defaultdict(list)

    def add_entity(self, user_id: str, name: str, kind: str = "thing") -> None:
        """Registers an entity (node) for `user_id`.

        If the entity already exists its `kind` is updated to the new value,
        so callers can refine a node's type after first creation.
        """
        self._entities[user_id][name] = {"name": name, "kind": kind}

    def add_relation(
        self,
        user_id: str,
        subject: str,
        predicate: str,
        obj: str,
    ) -> None:
        """Adds a directed labeled edge `subject --predicate--> obj`.

        Any endpoint that is not yet a known entity is auto-created with the
        default kind. Duplicate triples are ignored so the graph stays a set
        of distinct facts.
        """
        if subject not in self._entities[user_id]:
            self.add_entity(user_id, subject)
        if obj not in self._entities[user_id]:
            self.add_entity(user_id, obj)

        triple = {"subject": subject, "predicate": predicate, "object": obj}
        if triple not in self._relations[user_id]:
            self._relations[user_id].append(triple)

    def neighbors(self, user_id: str, name: str) -> list[dict]:
        """Returns entities directly related to `name` for `user_id`.

        Both outgoing and incoming edges are considered. Each result is a
        dict with the neighbour's `name`, the `predicate` of the connecting
        edge and the `direction` ("out" when `name` is the subject, "in"
        when `name` is the object). Returns an empty list if the entity has
        no relations.
        """
        results: list[dict] = []
        for rel in self._relations.get(user_id, []):
            if rel["subject"] == name:
                results.append(
                    {
                        "name": rel["object"],
                        "predicate": rel["predicate"],
                        "direction": "out",
                    }
                )
            if rel["object"] == name:
                results.append(
                    {
                        "name": rel["subject"],
                        "predicate": rel["predicate"],
                        "direction": "in",
                    }
                )
        return results

    def query(self, user_id: str, predicate: str) -> list[tuple[str, str]]:
        """Returns all `(subject, object)` pairs linked by `predicate`."""
        return [
            (rel["subject"], rel["object"])
            for rel in self._relations.get(user_id, [])
            if rel["predicate"] == predicate
        ]

    def entities(self, user_id: str) -> list[dict]:
        """Returns all entities stored for `user_id`."""
        return list(self._entities.get(user_id, {}).values())

    def relations(self, user_id: str) -> list[dict]:
        """Returns all relation triples stored for `user_id`."""
        return list(self._relations.get(user_id, []))

    def count(self, user_id: str) -> dict:
        """Returns entity and relation counts for `user_id`."""
        return {
            "entities": len(self._entities.get(user_id, {})),
            "relations": len(self._relations.get(user_id, [])),
        }

    def path(
        self,
        user_id: str,
        start: str,
        end: str,
        max_depth: int = 4,
    ) -> list[str] | None:
        """Finds the shortest path of entities between `start` and `end`.

        Performs a breadth-first search treating relations as undirected
        connections (an edge can be traversed in either direction). Returns
        the list of entity names along the path (inclusive of both ends), or
        `None` if no path exists within `max_depth` hops or if either
        endpoint is not a known entity.
        """
        ents = self._entities.get(user_id, {})
        if start not in ents or end not in ents:
            return None
        if start == end:
            return [start]

        # Build an undirected adjacency map from the relation triples.
        adjacency: dict[str, set[str]] = defaultdict(set)
        for rel in self._relations.get(user_id, []):
            adjacency[rel["subject"]].add(rel["object"])
            adjacency[rel["object"]].add(rel["subject"])

        # BFS: queue holds the path taken so far; first hit is shortest.
        queue: deque[list[str]] = deque([[start]])
        visited: set[str] = {start}
        while queue:
            current_path = queue.popleft()
            if len(current_path) - 1 >= max_depth:
                continue
            node = current_path[-1]
            for neighbour in sorted(adjacency.get(node, set())):
                if neighbour == end:
                    return current_path + [neighbour]
                if neighbour not in visited:
                    visited.add(neighbour)
                    queue.append(current_path + [neighbour])
        return None
