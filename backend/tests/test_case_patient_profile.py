"""Owner-scoped encrypted patient profile tests for the local demo workflow."""

from __future__ import annotations

import base64
import json
import os
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from backend.app.database.db import get_session
from backend.app.database.models.auth import User
from backend.app.database.models.eeg import AnalysisStatus, EEGSession
from backend.app.database.models.case_profile import CasePatientProfile
from backend.app.main import app
from backend.app.services.case_profile_service import (
    PatientProfileCryptoError,
    _associated_data,
    _profile_key,
    decrypt_profile,
    encrypt_profile,
)


def key_b64(value: bytes = b"p" * 32) -> str:
    return base64.b64encode(value).decode("ascii")


@contextmanager
def local_profile_environment():
    values = {
        "APP_ENV": "test",
        "AUTH_MODE": "local-accounts",
        "MDS01_STORAGE_KEY": key_b64(),
    }
    with patch.dict(os.environ, values):
        yield


class PatientProfileCryptoTests(unittest.TestCase):
    def test_identity_is_authenticated_encrypted_and_owner_bound(self) -> None:
        with local_profile_environment():
            owner_id = 41
            case_id = "CASE-ABCD1234"
            nonce, ciphertext = encrypt_profile(
                owner_id,
                case_id,
                {
                    "name": "Synthetic Patient",
                    "hospital_id": "HOSP-001",
                    "age": "47 years",
                    "findings": "Synthetic reviewed finding.",
                },
            )
            self.assertEqual(
                decrypt_profile(owner_id, case_id, nonce, ciphertext),
                {
                    "name": "Synthetic Patient",
                    "hospital_id": "HOSP-001",
                    "age": "47 years",
                    "findings": "Synthetic reviewed finding.",
                },
            )
            self.assertNotIn(b"Synthetic Patient", ciphertext)
            self.assertNotIn(b"47 years", ciphertext)
            self.assertNotIn(b"Synthetic reviewed finding", ciphertext)
            with self.assertRaises(PatientProfileCryptoError):
                decrypt_profile(owner_id + 1, case_id, nonce, ciphertext)
            corrupted = bytearray(ciphertext)
            corrupted[-1] ^= 1
            with self.assertRaises(PatientProfileCryptoError):
                decrypt_profile(owner_id, case_id, nonce, bytes(corrupted))

    def test_legacy_v1_identity_decrypts_with_empty_new_fields(self) -> None:
        with local_profile_environment():
            owner_id = 41
            case_id = "CASE-ABCD1234"
            nonce = b"n" * 12
            plaintext = json.dumps(
                {"name": "Synthetic Patient", "hospital_id": "HOSP-001"},
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
            ciphertext = AESGCM(_profile_key(1)).encrypt(
                nonce, plaintext, _associated_data(owner_id, case_id, 1)
            )

            self.assertEqual(
                decrypt_profile(owner_id, case_id, nonce, ciphertext, version=1),
                {
                    "name": "Synthetic Patient",
                    "hospital_id": "HOSP-001",
                    "age": "",
                    "findings": "",
                },
            )

    def test_flexible_reviewed_details_are_encrypted_and_owner_bound(self) -> None:
        with local_profile_environment():
            owner_id = 41
            case_id = "CASE-ABCD1234"
            details = [
                {"label": "Patient name", "value": "Synthetic Patient"},
                {"label": "Birth date", "value": "1980-01-01"},
                {"label": "Medication", "value": "Synthetic medication"},
            ]
            nonce, ciphertext = encrypt_profile(
                owner_id,
                case_id,
                {
                    "name": "",
                    "hospital_id": "",
                    "age": "",
                    "findings": "",
                    "details": details,
                },
            )

            self.assertEqual(
                decrypt_profile(owner_id, case_id, nonce, ciphertext)["details"],
                details,
            )
            self.assertNotIn(b"Synthetic Patient", ciphertext)
            self.assertNotIn(b"Synthetic medication", ciphertext)
            with self.assertRaises(PatientProfileCryptoError):
                decrypt_profile(owner_id + 1, case_id, nonce, ciphertext)

    def test_missing_configured_key_fails_closed(self) -> None:
        with patch.dict(os.environ, {"MDS01_STORAGE_KEY": ""}):
            with self.assertRaises(PatientProfileCryptoError):
                encrypt_profile(41, "CASE-ABCD1234", {"name": "A", "hospital_id": "B"})


class PatientProfileApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.environment = local_profile_environment()
        self.environment.__enter__()
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        def test_session():
            with Session(self.engine) as session:
                yield session

        app.dependency_overrides[get_session] = test_session
        self.client = TestClient(app)
        self.client.__enter__()
        self.alice = self._register("alice@example.test")
        self.case_id = "CASE-ABCD1234"
        with Session(self.engine) as db:
            db.add(
                EEGSession(
                    session_id="SES-ALICE-01",
                    owner_user_id=self.alice.id,
                    case_id=self.case_id,
                    status=AnalysisStatus.QUEUED,
                )
            )
            db.commit()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        app.dependency_overrides.pop(get_session, None)
        self.engine.dispose()
        self.environment.__exit__(None, None, None)

    def _register(self, email: str) -> User:
        headers = {"Origin": "http://localhost:3000"}
        response = self.client.post(
            "/api/auth/register",
            json={"email": email, "password": "correct horse battery"},
            headers=headers,
        )
        self.assertEqual(response.status_code, 201, response.text)
        login = self.client.post(
            "/api/auth/login",
            json={"email": email, "password": "correct horse battery"},
            headers=headers,
        )
        self.assertEqual(login.status_code, 200, login.text)
        with Session(self.engine) as db:
            user = db.exec(select(User).where(User.email == email)).one()
            db.expunge(user)
            return user

    def test_reviewed_profile_stays_private_except_for_safe_case_display_fields(self) -> None:
        headers = {"Origin": "http://localhost:3000"}
        response = self.client.put(
            f"/api/cases/{self.case_id}/patient-profile",
            json={
                "name": "Synthetic Patient",
                "hospital_id": "HOSP-001",
                "age": "47 years",
                "findings": "Synthetic reviewed finding.",
                "review_confirmed": True,
            },
            headers=headers,
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["profile"]["name"], "Synthetic Patient")
        self.assertEqual(response.json()["profile"]["hospital_id"], "HOSP-001")
        self.assertEqual(response.json()["profile"]["age"], "47 years")
        self.assertEqual(
            response.json()["profile"]["findings"], "Synthetic reviewed finding."
        )
        self.assertTrue(response.json()["profile"]["reviewed"])

        with Session(self.engine) as db:
            stored = db.exec(select(CasePatientProfile)).one()
            self.assertNotIn(b"Synthetic Patient", stored.identity_ciphertext)
            self.assertNotIn(b"HOSP-001", stored.identity_ciphertext)
            self.assertNotIn(b"47 years", stored.identity_ciphertext)
            self.assertNotIn(b"Synthetic reviewed finding", stored.identity_ciphertext)

        generic_payloads = [
            self.client.get("/api/cases", headers=headers).text,
            self.client.get(f"/api/cases/{self.case_id}", headers=headers).text,
        ]
        for payload in generic_payloads:
            self.assertIn("Synthetic Patient", payload)
            self.assertNotIn("HOSP-001", payload)
            self.assertNotIn("47 years", payload)
            self.assertNotIn("Synthetic reviewed finding", payload)

        case_list = self.client.get("/api/cases", headers=headers).json()
        case_detail = self.client.get(
            f"/api/cases/{self.case_id}", headers=headers
        ).json()
        self.assertEqual(case_list[0]["patient_name"], "Synthetic Patient")
        self.assertEqual(
            case_list[0]["patient_name_verification_status"], "reviewed"
        )
        self.assertEqual(case_detail["patient_name"], "Synthetic Patient")
        self.assertEqual(
            case_detail["patient_name_verification_status"], "reviewed"
        )
        loaded = self.client.get(
            f"/api/cases/{self.case_id}/patient-profile", headers=headers
        )
        self.assertEqual(loaded.status_code, 200, loaded.text)
        self.assertEqual(loaded.json()["profile"]["hospital_id"], "HOSP-001")
        self.assertEqual(loaded.json()["profile"]["age"], "47 years")
        self.assertEqual(
            loaded.json()["profile"]["findings"], "Synthetic reviewed finding."
        )

    def test_dynamic_report_details_need_no_hospital_id_and_stay_owner_private(self) -> None:
        headers = {"Origin": "http://localhost:3000"}
        details = [
            {"label": "Patient name", "value": "Synthetic Patient"},
            {"label": "Birth date", "value": "1980-01-01"},
            {"label": "Medication", "value": "Synthetic medication"},
        ]
        response = self.client.put(
            f"/api/cases/{self.case_id}/patient-profile",
            json={"details": details, "review_confirmed": True},
            headers=headers,
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["profile"]["details"], details)
        with Session(self.engine) as db:
            stored = db.exec(select(CasePatientProfile)).one()
            self.assertNotIn(b"Synthetic Patient", stored.identity_ciphertext)
            self.assertNotIn(b"Synthetic medication", stored.identity_ciphertext)

        loaded = self.client.get(
            f"/api/cases/{self.case_id}/patient-profile", headers=headers
        )
        self.assertEqual(loaded.status_code, 200, loaded.text)
        self.assertEqual(loaded.json()["profile"]["details"], details)

    def test_auto_extracted_profile_is_encrypted_owner_scoped_and_unverified(self) -> None:
        headers = {"Origin": "http://localhost:3000"}
        details = [
            {"label": "Patient Name", "value": "Synthetic Patient"},
            {"label": "Hospital ID", "value": "HOSP-001"},
            {"label": "Findings", "value": "Synthetic extracted finding."},
        ]
        response = self.client.put(
            f"/api/cases/{self.case_id}/patient-profile/extracted",
            json={"details": details},
            headers=headers,
        )

        self.assertEqual(response.status_code, 200, response.text)
        profile = response.json()["profile"]
        self.assertEqual(profile["verification_status"], "auto_extracted")
        self.assertFalse(profile["reviewed"])
        self.assertIsNone(profile["reviewed_at"])
        self.assertEqual(profile["details"], details)
        self.assertEqual(profile["name"], "Synthetic Patient")
        for generic_response in (
            self.client.get("/api/cases", headers=headers),
            self.client.get(f"/api/cases/{self.case_id}", headers=headers),
        ):
            self.assertEqual(generic_response.status_code, 200)
            self.assertNotIn("Synthetic Patient", generic_response.text)
            self.assertNotIn("HOSP-001", generic_response.text)
            self.assertNotIn("47 years", generic_response.text)
            self.assertNotIn("Synthetic extracted finding", generic_response.text)
            payload = generic_response.json()
            summary = payload[0] if isinstance(payload, list) else payload
            self.assertIsNone(summary["patient_name"])
            self.assertIsNone(summary["patient_name_verification_status"])
            self.assertIsNone(summary.get("report_summary"))

        with Session(self.engine) as db:
            stored = db.exec(select(CasePatientProfile)).one()
            self.assertEqual(stored.verification_status, "auto_extracted")
            self.assertIsNone(stored.reviewed_by_user_id)
            self.assertIsNone(stored.reviewed_at)
            self.assertNotIn(b"Synthetic Patient", stored.identity_ciphertext)
            self.assertNotIn(b"Synthetic extracted finding", stored.identity_ciphertext)

        loaded = self.client.get(
            f"/api/cases/{self.case_id}/patient-profile", headers=headers
        )
        self.assertEqual(loaded.status_code, 200, loaded.text)
        self.assertEqual(
            loaded.json()["profile"]["verification_status"], "auto_extracted"
        )
        self.assertFalse(loaded.json()["profile"]["reviewed"])

        self.client.post("/api/auth/logout", headers=headers)
        self._register("bob@example.test")
        bob_headers = {"Origin": "http://localhost:3000"}
        forbidden_read = self.client.get(
            f"/api/cases/{self.case_id}/patient-profile", headers=bob_headers
        )
        self.assertEqual(forbidden_read.status_code, 404)
        forbidden = self.client.put(
            f"/api/cases/{self.case_id}/patient-profile/extracted",
            json={"details": details},
            headers=bob_headers,
        )
        self.assertEqual(forbidden.status_code, 404)

    def test_legacy_age_field_rejects_dates_and_dob_labels(self) -> None:
        url = f"/api/cases/{self.case_id}/patient-profile"
        headers = {"Origin": "http://localhost:3000"}
        for age in ("DOB: 1980-01-01", "1980-01-01"):
            with self.subTest(age=age):
                response = self.client.put(
                    url,
                    json={
                        "name": "Synthetic Patient",
                        "hospital_id": "HOSP-001",
                        "age": age,
                        "findings": "Synthetic finding.",
                        "review_confirmed": True,
                    },
                    headers=headers,
                )
                self.assertEqual(response.status_code, 422)

        age_detail = self.client.put(
            url,
            json={
                "details": [{"label": "Age", "value": "DOB: 1980-01-01"}],
                "review_confirmed": True,
            },
            headers=headers,
        )
        self.assertEqual(age_detail.status_code, 422)

    def test_unreviewed_or_extra_report_content_is_rejected(self) -> None:
        url = f"/api/cases/{self.case_id}/patient-profile"
        headers = {"Origin": "http://localhost:3000"}
        unreviewed = self.client.put(
            url,
            json={"name": "Draft", "hospital_id": "H-1", "review_confirmed": False},
            headers=headers,
        )
        self.assertEqual(unreviewed.status_code, 422)
        extra = self.client.put(
            url,
            json={
                "name": "Draft",
                "hospital_id": "H-1",
                "review_confirmed": True,
                "report_text": "must not be stored",
            },
            headers=headers,
        )
        self.assertEqual(extra.status_code, 422)
        self.assertEqual(self.client.get(url, headers=headers).json()["profile"], None)

    def test_profile_reads_and_writes_are_owner_scoped(self) -> None:
        self.client.post("/api/auth/logout", headers={"Origin": "http://localhost:3000"})
        self._register("bob@example.test")
        headers = {"Origin": "http://localhost:3000"}
        response = self.client.get(
            f"/api/cases/{self.case_id}/patient-profile", headers=headers
        )
        self.assertEqual(response.status_code, 404)
        write = self.client.put(
            f"/api/cases/{self.case_id}/patient-profile",
            json={"name": "Other", "hospital_id": "H-2", "review_confirmed": True},
            headers=headers,
        )
        self.assertEqual(write.status_code, 404)


if __name__ == "__main__":
    unittest.main()
