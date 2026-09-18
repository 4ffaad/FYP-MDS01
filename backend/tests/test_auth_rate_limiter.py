"""Tests for bounded local-authentication attempt admission."""

from __future__ import annotations

import unittest

from backend.app.services.auth_rate_limiter import AuthRateLimiter


class AuthRateLimiterTests(unittest.TestCase):
    def test_limits_both_ip_and_identity_buckets(self) -> None:
        limiter = AuthRateLimiter(window_seconds=60, max_attempts=2, max_registrations=1)

        self.assertTrue(limiter.allow("login", "192.0.2.1", "alice@example.test"))
        self.assertTrue(limiter.allow("login", "192.0.2.1", "bob@example.test"))
        self.assertFalse(limiter.allow("login", "192.0.2.1", "carol@example.test"))

    def test_registration_has_a_separate_lower_limit(self) -> None:
        limiter = AuthRateLimiter(window_seconds=60, max_attempts=10, max_registrations=1)

        self.assertTrue(limiter.allow("register", "192.0.2.1", "alice@example.test"))
        self.assertFalse(limiter.allow("register", "192.0.2.1", "bob@example.test"))
        self.assertTrue(limiter.allow("login", "192.0.2.1", "bob@example.test"))

    def test_old_events_are_removed_from_the_window(self) -> None:
        limiter = AuthRateLimiter(window_seconds=60, max_attempts=1, max_registrations=1)
        now = [100.0]
        limiter._clock = lambda: now[0]

        self.assertTrue(limiter.allow("login", "192.0.2.1", "alice@example.test"))
        self.assertFalse(limiter.allow("login", "192.0.2.1", "alice@example.test"))
        now[0] = 161.0
        self.assertTrue(limiter.allow("login", "192.0.2.1", "alice@example.test"))


if __name__ == "__main__":
    unittest.main()
