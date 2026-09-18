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

from backend.app.core.config import MAX_UPLOAD_BYTES, auth_configuration
from backend.app.core.security import owner_id
from backend.app.database.db import get_session
from backend.app.database.models.auth import User
from backend.app.services.auth_service import DEMO_ADMIN_PUBLIC_ID
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
        for mode in ("local", "local-accounts"):
            with self.subTest(mode=mode), auth_environment(APP_ENV="production", AUTH_MODE=mode):
                with self.assertRaisesRegex(RuntimeError, "production"):
                    with TestClient(app):
                        pass

    def test_unauthenticated_compatibility_mode_is_test_only(self) -> None:
        with auth_environment(AUTH_MODE="local"):
            with self.assertRaisesRegex(RuntimeError, "only when APP_ENV=test"):
                with TestClient(app):
                    pass

    def test_development_defaults_to_authenticated_local_accounts(self) -> None:
        with auth_environment(APP_ENV="development"):
            self.assertEqual(auth_configuration()[0], "local-accounts")

    def test_login_rate_limit_rejects_before_password_verification(self) -> None:
        with auth_environment(APP_ENV="test", AUTH_MODE="local-accounts"), patch(
            "backend.app.api.auth.auth_rate_limiter.allow", return_value=False
        ), patch("backend.app.api.auth.authenticate_local_user") as authenticate:
            with TestClient(app) as client:
                response = client.post(
                    "/api/auth/login",
                    json={"email": "alice@example.test", "password": "wrong"},
                    headers={"Origin": "http://localhost:3000"},
                )

        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers.get("retry-after"), "60")
        authenticate.assert_not_called()

    def test_non_demo_admin_is_still_owner_scoped(self) -> None:
        admin = User(id=73, public_id="USR-ADMIN", email="admin@example.test", is_admin=True)
        with auth_environment(APP_ENV="development", AUTH_MODE="local-accounts"), patch.dict(
            os.environ, {"DEMO_ADMIN_ENABLED": "false"}
        ):
            self.assertEqual(owner_id(admin), 73)

    def test_enabled_development_demo_admin_can_use_global_read_scope(self) -> None:
        admin = User(id=74, public_id=DEMO_ADMIN_PUBLIC_ID, email="demo@example.test", is_admin=True)
        with auth_environment(APP_ENV="development", AUTH_MODE="local-accounts"), patch.dict(
            os.environ, {"DEMO_ADMIN_ENABLED": "true"}
        ):
            self.assertIsNone(owner_id(admin))

    def test_cloudflare_state_changes_require_configured_origin(self) -> None:
        with auth_environment(
            AUTH_MODE="cloudflare",
            CLOUDFLARE_ACCESS_TEAM_DOMAIN="test.cloudflareaccess.com",
            CLOUDFLARE_ACCESS_AUD="test-audience",
        ):
            with TestClient(app) as client:
                response = client.post(
                    "/api/sessions/upload",
                    files={"archive": ("recordings.zip", b"not a zip", "application/zip")},
                )

        self.assertEqual(response.status_code, 403)

    def test_inactive_cloudflare_identity_is_rejected(self) -> None:
        with Session(self.engine) as db:
            db.add(
                User(
                    public_id="USR-INACTIVE-CF",
                    email="inactive@example.test",
                    auth_provider="cloudflare",
                    external_subject="inactive-subject",
                    active=False,
                )
            )
            db.commit()

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        assertion = jwt.encode(
            {
                "aud": "test-audience",
                "iss": "https://test.cloudflareaccess.com",
                "sub": "inactive-subject",
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

    def test_local_mode_preserves_existing_api_behavior(self) -> None:
        with auth_environment(APP_ENV="test", AUTH_MODE="local"):
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

    def test_private_api_responses_are_not_cacheable(self) -> None:
        with auth_environment(APP_ENV="test", AUTH_MODE="local"):
            with TestClient(app) as client:
                response = client.get("/api/sessions")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "no-store, private")
        self.assertEqual(response.headers["pragma"], "no-cache")
        self.assertIn("Cookie", response.headers["vary"])

    def test_openapi_advertises_protected_api_security(self) -> None:
        schema = app.openapi()
        schemes = schema["components"]["securitySchemes"]
        self.assertIn("SessionCookie", schemes)
        self.assertIn("CloudflareAccess", schemes)
        self.assertTrue(schema["paths"]["/api/sessions"]["get"]["security"])
        self.assertNotIn("security", schema["paths"]["/api/auth/session"]["get"])

    def test_security_headers_are_added(self) -> None:
        with auth_environment(APP_ENV="test", AUTH_MODE="local"):
            with TestClient(app) as client:
                response = client.get("/health")

        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        self.assertEqual(response.headers["x-frame-options"], "DENY")
        self.assertEqual(response.headers["referrer-policy"], "no-referrer")
        self.assertNotIn("strict-transport-security", response.headers)

    def test_oversized_upload_body_is_rejected_before_multipart_parsing(self) -> None:
        with auth_environment(APP_ENV="test", AUTH_MODE="local"):
            with TestClient(app) as client:
                response = client.post(
                    "/api/uploads/drafts",
                    content=b"x",
                    headers={
                        "Content-Type": "application/octet-stream",
                        "Content-Length": str(MAX_UPLOAD_BYTES + 2 * 1024 * 1024),
                    },
                )

        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.json()["detail"], "Request body exceeds the configured upload limit.")


if __name__ == "__main__":
    unittest.main()
