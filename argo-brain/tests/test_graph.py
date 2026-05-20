"""Tests for the L3 knowledge-graph memory layer (`KnowledgeGraph`)."""

from __future__ import annotations

import unittest

from argo_brain.memory.graph import KnowledgeGraph


class TestKnowledgeGraph(unittest.TestCase):
    def setUp(self) -> None:
        self.kg = KnowledgeGraph()

    def test_add_entity(self) -> None:
        """Adding an entity registers it with the given kind."""
        self.kg.add_entity("u1", "Alice", kind="person")
        ents = self.kg.entities("u1")
        self.assertEqual(len(ents), 1)
        self.assertEqual(ents[0], {"name": "Alice", "kind": "person"})

    def test_add_entity_default_kind(self) -> None:
        """An entity added without a kind defaults to 'thing'."""
        self.kg.add_entity("u1", "Widget")
        self.assertEqual(self.kg.entities("u1")[0]["kind"], "thing")

    def test_add_entity_updates_kind(self) -> None:
        """Re-adding an entity refines its kind without duplicating it."""
        self.kg.add_entity("u1", "Bob")
        self.kg.add_entity("u1", "Bob", kind="person")
        ents = self.kg.entities("u1")
        self.assertEqual(len(ents), 1)
        self.assertEqual(ents[0]["kind"], "person")

    def test_add_relation_creates_entities(self) -> None:
        """add_relation auto-creates any missing endpoint entities."""
        self.kg.add_relation("u1", "Alice", "knows", "Bob")
        names = {e["name"] for e in self.kg.entities("u1")}
        self.assertEqual(names, {"Alice", "Bob"})
        self.assertEqual(len(self.kg.relations("u1")), 1)

    def test_add_relation_deduplicates(self) -> None:
        """Adding the same triple twice stores it only once."""
        self.kg.add_relation("u1", "Alice", "knows", "Bob")
        self.kg.add_relation("u1", "Alice", "knows", "Bob")
        self.assertEqual(len(self.kg.relations("u1")), 1)

    def test_neighbors_directly_connected(self) -> None:
        """neighbors returns directly-connected nodes only."""
        self.kg.add_relation("u1", "Alice", "knows", "Bob")
        self.kg.add_relation("u1", "Bob", "knows", "Carol")
        names = {n["name"] for n in self.kg.neighbors("u1", "Alice")}
        self.assertEqual(names, {"Bob"})  # Carol is two hops away.

    def test_neighbors_direction(self) -> None:
        """neighbors reports outgoing and incoming edge directions."""
        self.kg.add_relation("u1", "Alice", "likes", "Pizza")
        self.kg.add_relation("u1", "Bob", "knows", "Alice")
        result = self.kg.neighbors("u1", "Alice")
        directions = {(n["name"], n["direction"]) for n in result}
        self.assertIn(("Pizza", "out"), directions)
        self.assertIn(("Bob", "in"), directions)

    def test_neighbors_empty_for_unknown(self) -> None:
        """An entity with no relations has no neighbors."""
        self.kg.add_entity("u1", "Lonely")
        self.assertEqual(self.kg.neighbors("u1", "Lonely"), [])

    def test_query_by_predicate(self) -> None:
        """query returns every (subject, object) pair for a predicate."""
        self.kg.add_relation("u1", "Alice", "likes", "Pizza")
        self.kg.add_relation("u1", "Bob", "likes", "Sushi")
        self.kg.add_relation("u1", "Alice", "knows", "Bob")
        pairs = self.kg.query("u1", "likes")
        self.assertEqual(
            sorted(pairs), [("Alice", "Pizza"), ("Bob", "Sushi")]
        )

    def test_query_unknown_predicate(self) -> None:
        """Querying an unused predicate yields an empty list."""
        self.kg.add_relation("u1", "Alice", "knows", "Bob")
        self.assertEqual(self.kg.query("u1", "hates"), [])

    def test_path_multi_hop(self) -> None:
        """path finds a multi-hop route between two entities."""
        self.kg.add_relation("u1", "Alice", "knows", "Bob")
        self.kg.add_relation("u1", "Bob", "knows", "Carol")
        self.kg.add_relation("u1", "Carol", "knows", "Dave")
        self.assertEqual(
            self.kg.path("u1", "Alice", "Dave"),
            ["Alice", "Bob", "Carol", "Dave"],
        )

    def test_path_shortest(self) -> None:
        """path returns the shortest route when several exist."""
        self.kg.add_relation("u1", "Alice", "knows", "Bob")
        self.kg.add_relation("u1", "Bob", "knows", "Dave")
        self.kg.add_relation("u1", "Alice", "knows", "Carol")
        self.kg.add_relation("u1", "Carol", "knows", "Eve")
        self.kg.add_relation("u1", "Eve", "knows", "Dave")
        self.assertEqual(self.kg.path("u1", "Alice", "Dave"), ["Alice", "Bob", "Dave"])

    def test_path_same_node(self) -> None:
        """The path from an entity to itself is a single-element list."""
        self.kg.add_entity("u1", "Alice")
        self.assertEqual(self.kg.path("u1", "Alice", "Alice"), ["Alice"])

    def test_path_disconnected_returns_none(self) -> None:
        """path returns None when no route connects the endpoints."""
        self.kg.add_relation("u1", "Alice", "knows", "Bob")
        self.kg.add_relation("u1", "Carol", "knows", "Dave")
        self.assertIsNone(self.kg.path("u1", "Alice", "Dave"))

    def test_path_unknown_entity_returns_none(self) -> None:
        """path returns None if either endpoint is not a known entity."""
        self.kg.add_relation("u1", "Alice", "knows", "Bob")
        self.assertIsNone(self.kg.path("u1", "Alice", "Ghost"))

    def test_path_respects_max_depth(self) -> None:
        """path returns None when the route exceeds max_depth hops."""
        self.kg.add_relation("u1", "A", "to", "B")
        self.kg.add_relation("u1", "B", "to", "C")
        self.kg.add_relation("u1", "C", "to", "D")
        self.kg.add_relation("u1", "D", "to", "E")
        self.assertIsNone(self.kg.path("u1", "A", "E", max_depth=2))
        self.assertEqual(
            self.kg.path("u1", "A", "E", max_depth=4),
            ["A", "B", "C", "D", "E"],
        )

    def test_per_user_isolation(self) -> None:
        """Entities and relations are strictly scoped per user."""
        self.kg.add_relation("u1", "Alice", "knows", "Bob")
        self.kg.add_relation("u2", "Carol", "knows", "Dave")
        self.assertEqual({e["name"] for e in self.kg.entities("u1")}, {"Alice", "Bob"})
        self.assertEqual({e["name"] for e in self.kg.entities("u2")}, {"Carol", "Dave"})
        self.assertEqual(self.kg.query("u1", "knows"), [("Alice", "Bob")])
        self.assertIsNone(self.kg.path("u1", "Alice", "Dave"))

    def test_count(self) -> None:
        """count reports entity and relation totals for a user."""
        self.kg.add_relation("u1", "Alice", "knows", "Bob")
        self.kg.add_relation("u1", "Bob", "likes", "Pizza")
        self.assertEqual(self.kg.count("u1"), {"entities": 3, "relations": 2})

    def test_count_empty_user(self) -> None:
        """count returns zeroes for a user with no data."""
        self.assertEqual(self.kg.count("nobody"), {"entities": 0, "relations": 0})


if __name__ == "__main__":
    unittest.main()
