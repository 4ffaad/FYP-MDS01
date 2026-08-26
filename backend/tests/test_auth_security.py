"""Security-boundary tests for public health and protected API routes."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from backend.app.database.db import get_session
from backend.app.main import app


@contextmanager
def auth_environment(**values: str):
    """Temporarily set authentication variables without leaking test state."""

    names = {
        "APP_ENV",
        "AUTH_MODE",
        "CLOUDFLARE_ACCESS_TEAM_DOMAIN",
        "CLOUDFLARE_ACCESS_AUD",
    }
    previous = {name: os.environ.get(name) for name in names}
    try:
        for name in names:
            if name in values:
                os.environ[name] = values[name]
            else:
                os.environ.pop(name, None)
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


class AuthenticationSecurityTests(unittest.TestCase):
    """Verify authentication at the application's public HTTP boundary."""

    @classmethod
    def setUpClass(cls) -> None:
        """Create an isolated database used by legitimate API requests."""

        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(cls.engine)

        def test_session():
            with Session(cls.engine) as session:
                yield session

        app.dependency_overrides[get_session] = test_session

    @classmethod
    def tearDownClass(cls) -> None:
        """Restore application dependencies and release the test database."""

        app.dependency_overrides.pop(get_session, None)
        cls.engine.dispose()

    def test_health_remains_public_in_cloudflare_mode(self) -> None:
        with auth_environment(
            AUTH_MODE="cloudflare",
            CLOUDFLARE_ACCESS_TEAM_DOMAIN="test.cloudflareaccess.com",
            CLOUDFLARE_ACCESS_AUD="test-audience",
        ):
            with TestClient(app) as client:
                response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "service": "backend"})
        self.assertEqual(
            response.headers["strict-transport-security"],
            "max-age=31536000; includeSubDomains",
        )

    def test_cloudflare_mode_rejects_missing_assertion_for_every_api_router(self) -> None:
        with auth_environment(
            AUTH_MODE="cloudflare",
            CLOUDFLARE_ACCESS_TEAM_DOMAIN="test.cloudflareaccess.com",
            CLOUDFLARE_ACCESS_AUD="test-audience",
        ):
            with TestClient(app) as client:
                responses = [
                    client.get("/api/sessions"),
                    client.get("/api/recordings/REC-UNKNOWN"),
                    client.get("/api/uploads/drafts/UPL-UNKNOWN"),
                    client.get("/api/video-privacy/jobs"),
                ]

        self.assertEqual([response.status_code for response in responses], [401, 401, 401, 401])

    def test_cloudflare_mode_rejects_missing_configuration_at_startup(self) -> None:
        with auth_environment(AUTH_MODE="cloudflare"):
            with self.assertRaisesRegex(RuntimeError, "Cloudflare Access"):
                with TestClient(app):
                    pass

    def test_cloudflare_mode_rejects_invalid_team_domain_at_startup(self) -> None:
        with auth_environment(
            AUTH_MODE="cloudflare",
            CLOUDFLARE_ACCESS_TEAM_DOMAIN="https://example.test/keys",
            CLOUDFLARE_ACCESS_AUD="test-audience",
        ):
            with self.assertRaisesRegex(RuntimeError, "Cloudflare Access"):
                with TestClient(app):
                    pass

    def test_production_rejects_local_authentication_at_startup(self) -> None:
        with auth_environment(APP_ENV="production", AUTH_MODE="local"):
            with self.assertRaisesRegex(RuntimeError, "production"):
                with TestClient(app):
                    pass

    def test_local_mode_preserves_existing_api_behavior(self) -> None:
        with auth_environment(AUTH_MODE="local"):
            with TestClient(app) as client:
                response = client.get("/api/sessions")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_valid_cloudflare_assertion_reaches_api(self) -> None:
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        assertion = jwt.encode(
            {
                "aud": "test-audience",
                "iss": "https://test.cloudflareaccess.com",
                "sub": "clinician@example.test",
                "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
            },
            private_key,
            algorithm="RS256",
            headers={"kid": "test-key"},
        )

        with auth_environment(
            AUTH_MODE="cloudflare",
            CLOUDFLARE_ACCESS_TEAM_DOMAIN="test.cloudflareaccess.com",
            CLOUDFLARE_ACCESS_AUD="test-audience",
        ), patch(
            "backend.app.core.security.PyJWKClient.get_signing_key_from_jwt",
            return_value=SimpleNamespace(key=private_key.public_key()),
        ):
            with TestClient(app) as client:
                response = client.get(
                    "/api/sessions",
                    headers={"Cf-Access-Jwt-Assertion": assertion},
                )

        self.assertEqual(response.status_code, 200)

    def test_cloudflare_mode_rejects_wrong_audience(self) -> None:
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        assertion = jwt.encode(
            {
                "aud": "wrong-audience",
                "iss": "https://test.cloudflareaccess.com",
                "sub": "clinician@example.test",
                "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
            },
            private_key,
            algorithm="RS256",
            headers={"kid": "test-key"},
        )

        with auth_environment(
            AUTH_MODE="cloudflare",
            CLOUDFLARE_ACCESS_TEAM_DOMAIN="test.cloudflareaccess.com",
            CLOUDFLARE_ACCESS_AUD="test-audience",
        ), patch(
            "backend.app.core.security.PyJWKClient.get_signing_key_from_jwt",
            return_value=SimpleNamespace(key=private_key.public_key()),
        ):
            with TestClient(app) as client:
                response = client.get(
                    "/api/sessions",
                    headers={"Cf-Access-Jwt-Assertion": assertion},
                )

        self.assertEqual(response.status_code, 401)

    def test_security_headers_are_added(self) -> None:
        with auth_environment(AUTH_MODE="local"):
            with TestClient(app) as client:
                response = client.get("/health")

        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        self.assertEqual(response.headers["x-frame-options"], "DENY")
        self.assertEqual(response.headers["referrer-policy"], "no-referrer")
        self.assertNotIn("strict-transport-security", response.headers)


if __name__ == "__main__":
    unittest.main()
