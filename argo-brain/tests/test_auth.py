"""Tests for the authentication primitives (spec section 10)."""

import time
import unittest

from argo_brain.security.auth import (
    AuthError,
    generate_api_key,
    hash_api_key,
    jwt_decode,
    jwt_encode,
    verify_api_key,
)


class TestApiKey(unittest.TestCase):
    """Tests for API-key generation, hashing and verification."""

    def test_generated_key_has_prefix(self):
        self.assertTrue(generate_api_key().startswith("argo_"))

    def test_generated_keys_are_unique(self):
        keys = {generate_api_key() for _ in range(50)}
        self.assertEqual(len(keys), 50)

    def test_hash_round_trip(self):
        key = generate_api_key()
        stored = hash_api_key(key)
        self.assertTrue(verify_api_key(key, stored))

    def test_wrong_key_rejected(self):
        key = generate_api_key()
        stored = hash_api_key(key)
        self.assertFalse(verify_api_key(generate_api_key(), stored))

    def test_hash_is_salted(self):
        # Same input must hash differently each time (random salt).
        key = generate_api_key()
        self.assertNotEqual(hash_api_key(key), hash_api_key(key))

    def test_hash_format_is_self_describing(self):
        stored = hash_api_key("argo_test")
        parts = stored.split("$")
        self.assertEqual(len(parts), 4)
        self.assertEqual(parts[0], "pbkdf2_sha256")
        self.assertTrue(parts[1].isdigit())

    def test_hash_does_not_contain_plaintext(self):
        key = generate_api_key()
        self.assertNotIn(key, hash_api_key(key))

    def test_malformed_stored_hash_returns_false(self):
        self.assertFalse(verify_api_key("argo_x", "not-a-valid-hash"))
        self.assertFalse(verify_api_key("argo_x", "$$$"))

    def test_unknown_algorithm_returns_false(self):
        self.assertFalse(
            verify_api_key("argo_x", "md5$1$abc$def")
        )

    def test_empty_key_round_trip(self):
        stored = hash_api_key("")
        self.assertTrue(verify_api_key("", stored))
        self.assertFalse(verify_api_key("x", stored))


class TestJwtEncodeDecode(unittest.TestCase):
    """Tests for JWT signing and verification."""

    SECRET = "super-secret-signing-key"

    def test_sign_and_verify_round_trip(self):
        token = jwt_encode({"sub": "alice", "role": "admin"}, self.SECRET)
        claims = jwt_decode(token, self.SECRET)
        self.assertEqual(claims["sub"], "alice")
        self.assertEqual(claims["role"], "admin")

    def test_token_has_three_segments(self):
        token = jwt_encode({"sub": "x"}, self.SECRET)
        self.assertEqual(len(token.split(".")), 3)

    def test_iat_claim_added_automatically(self):
        token = jwt_encode({"sub": "x"}, self.SECRET)
        claims = jwt_decode(token, self.SECRET)
        self.assertIn("iat", claims)

    def test_exp_claim_added_when_expires_in_given(self):
        token = jwt_encode({"sub": "x"}, self.SECRET, expires_in=3600)
        claims = jwt_decode(token, self.SECRET)
        self.assertIn("exp", claims)
        self.assertGreater(claims["exp"], claims["iat"])

    def test_caller_payload_not_mutated(self):
        payload = {"sub": "x"}
        jwt_encode(payload, self.SECRET, expires_in=10)
        self.assertEqual(payload, {"sub": "x"})

    def test_wrong_secret_rejected(self):
        token = jwt_encode({"sub": "x"}, self.SECRET)
        with self.assertRaises(AuthError):
            jwt_decode(token, "the-wrong-secret")

    def test_tampered_payload_rejected(self):
        token = jwt_encode({"sub": "alice"}, self.SECRET)
        header, payload, signature = token.split(".")
        # Swap in a different (validly encoded) payload, keep old signature.
        forged_payload = jwt_encode({"sub": "attacker"}, self.SECRET).split(
            "."
        )[1]
        forged = f"{header}.{forged_payload}.{signature}"
        with self.assertRaises(AuthError):
            jwt_decode(forged, self.SECRET)

    def test_tampered_signature_rejected(self):
        token = jwt_encode({"sub": "x"}, self.SECRET)
        header, payload, _ = token.split(".")
        forged = f"{header}.{payload}.AAAAAAAAAAAAAAAAAAAAAA"
        with self.assertRaises(AuthError):
            jwt_decode(forged, self.SECRET)

    def test_malformed_token_rejected(self):
        with self.assertRaises(AuthError):
            jwt_decode("only.two", self.SECRET)
        with self.assertRaises(AuthError):
            jwt_decode("not-a-token", self.SECRET)

    def test_alg_none_rejected(self):
        # A classic JWT attack: forging a token with "alg": "none".
        import base64
        import json

        header = base64.urlsafe_b64encode(
            json.dumps({"alg": "none", "typ": "JWT"}).encode()
        ).rstrip(b"=").decode()
        payload = base64.urlsafe_b64encode(
            json.dumps({"sub": "attacker"}).encode()
        ).rstrip(b"=").decode()
        forged = f"{header}.{payload}."
        with self.assertRaises(AuthError):
            jwt_decode(forged, self.SECRET)

    def test_expired_token_rejected(self):
        token = jwt_encode({"sub": "x"}, self.SECRET, expires_in=-10)
        with self.assertRaises(AuthError) as ctx:
            jwt_decode(token, self.SECRET)
        self.assertIn("expired", str(ctx.exception))

    def test_expired_token_accepted_when_verify_exp_false(self):
        token = jwt_encode({"sub": "x"}, self.SECRET, expires_in=-10)
        claims = jwt_decode(token, self.SECRET, verify_exp=False)
        self.assertEqual(claims["sub"], "x")

    def test_expired_token_accepted_within_leeway(self):
        token = jwt_encode({"sub": "x"}, self.SECRET, expires_in=-5)
        claims = jwt_decode(token, self.SECRET, leeway=60)
        self.assertEqual(claims["sub"], "x")

    def test_not_yet_valid_token_rejected(self):
        future = int(time.time()) + 3600
        token = jwt_encode({"sub": "x", "nbf": future}, self.SECRET)
        with self.assertRaises(AuthError) as ctx:
            jwt_decode(token, self.SECRET)
        self.assertIn("not yet valid", str(ctx.exception))

    def test_nbf_in_past_accepted(self):
        past = int(time.time()) - 3600
        token = jwt_encode({"sub": "x", "nbf": past}, self.SECRET)
        claims = jwt_decode(token, self.SECRET)
        self.assertEqual(claims["sub"], "x")

    def test_valid_token_with_future_exp_accepted(self):
        token = jwt_encode({"sub": "x"}, self.SECRET, expires_in=3600)
        claims = jwt_decode(token, self.SECRET)
        self.assertEqual(claims["sub"], "x")


if __name__ == "__main__":
    unittest.main()
