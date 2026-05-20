"""L2 vector memory tests (spec section 4.3)."""

import math
import unittest

from argo_brain.memory.vector import EMBED_DIM, VectorMemory, embed


class TestEmbed(unittest.TestCase):
    def test_deterministic(self):
        # The same input must always yield the exact same vector.
        self.assertEqual(embed("hello world"), embed("hello world"))

    def test_fixed_length(self):
        # Every vector has EMBED_DIM dimensions, regardless of input size.
        self.assertEqual(len(embed("short")), EMBED_DIM)
        self.assertEqual(len(embed("a much longer piece of text here")), EMBED_DIM)
        self.assertEqual(len(embed("")), EMBED_DIM)

    def test_normalized(self):
        # Non-empty text produces a unit-norm (L2 ~= 1.0) vector.
        norm = math.sqrt(sum(x * x for x in embed("kubernetes deploy vault")))
        self.assertAlmostEqual(norm, 1.0, places=6)

    def test_empty_text_is_zero_vector(self):
        # Token-less text has no buckets to fill -> all-zero vector.
        self.assertEqual(embed("   "), [0.0] * EMBED_DIM)


class TestVectorMemory(unittest.TestCase):
    def setUp(self):
        self.mem = VectorMemory()

    def test_search_returns_most_relevant_first(self):
        self.mem.add("u1", "deploy the service to the kubernetes cluster")
        self.mem.add("u1", "check the vault secret configuration")
        self.mem.add("u1", "the cat sat on the warm windowsill")

        hits = self.mem.search("u1", "kubernetes cluster deploy", k=3)
        self.assertEqual(len(hits), 3)
        self.assertIn("kubernetes", hits[0]["text"])
        # Scores must be sorted in descending order.
        self.assertGreaterEqual(hits[0]["score"], hits[1]["score"])
        self.assertGreaterEqual(hits[1]["score"], hits[2]["score"])

    def test_per_user_isolation(self):
        self.mem.add("u1", "secret data for user one")
        self.mem.add("u2", "different content for user two")

        hits = self.mem.search("u1", "secret data", k=5)
        self.assertEqual(len(hits), 1)
        self.assertIn("user one", hits[0]["text"])

    def test_count(self):
        self.assertEqual(self.mem.count("u1"), 0)
        self.mem.add("u1", "first")
        self.mem.add("u1", "second")
        self.assertEqual(self.mem.count("u1"), 2)
        # Other users are unaffected.
        self.assertEqual(self.mem.count("u2"), 0)

    def test_empty_search(self):
        # Searching a user with no entries yields an empty list.
        self.assertEqual(self.mem.search("nobody", "anything"), [])

    def test_k_limits_results(self):
        for i in range(10):
            self.mem.add("u1", f"entry number {i}")
        hits = self.mem.search("u1", "entry number", k=4)
        self.assertEqual(len(hits), 4)

    def test_metadata_roundtrip(self):
        self.mem.add("u1", "deploy notes", metadata={"source": "channel-x"})
        hits = self.mem.search("u1", "deploy notes", k=1)
        self.assertEqual(hits[0]["metadata"], {"source": "channel-x"})

    def test_metadata_defaults_to_empty_dict(self):
        self.mem.add("u1", "no metadata here")
        hits = self.mem.search("u1", "no metadata here", k=1)
        self.assertEqual(hits[0]["metadata"], {})


if __name__ == "__main__":
    unittest.main()
