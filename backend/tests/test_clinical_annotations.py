"""Owner-scoped encrypted clinical observation API coverage."""

from __future__ import annotations

import base64
import os
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine, select

from backend.app.api.clinical_annotations import router
from backend.app.core.security import require_api_auth
from backend.app.database.db import get_session
from backend.app.database.models.auth import User
from backend.app.database.models.clinical_annotation import ClinicalAnnotation
from backend.app.database.models.clinical_access_event import ClinicalAccessEvent
from backend.app.database.models.eeg import AnalysisStatus, EEGRecording, EEGSession
from backend.app.database.repository import delete_sessions_data


class ClinicalAnnotationApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)
        self.owner = User(id=1, public_id="USR-OWNER", email="owner@example.test")
        with Session(self.engine) as db:
            db.add(self.owner)
            db.add(User(id=2, public_id="USR-OTHER", email="other@example.test"))
            db.commit()
            session = EEGSession(
                session_id="SES-OWNER-01",
                owner_user_id=1,
                case_id="CASE-OWNER123",
                status=AnalysisStatus.COMPLETED,
            )
            db.add(session)
            db.commit()
            db.refresh(session)
            db.add(
                EEGRecording(
                    record_id="REC-OWNER-01",
                    session_db_id=session.id,
                    original_filename="",
                    duration_seconds=120,
                )
            )
            db.commit()
            self.owner = db.get(User, 1)
            db.refresh(self.owner)
            db.expunge(self.owner)
        self.owner_id = 1
        self.app = FastAPI()
        self.app.include_router(router)

        def database():
            with Session(self.engine) as db:
                yield db

        self.app.dependency_overrides[get_session] = database
        self.app.dependency_overrides[require_api_auth] = lambda: self.owner
        self.client = TestClient(self.app)
        self.key = patch.dict(
            os.environ,
            {"MDS01_STORAGE_KEY": base64.b64encode(b"x" * 32).decode("ascii")},
        )
        self.key.start()

    def tearDown(self) -> None:
        self.client.close()
        self.app.dependency_overrides.clear()
        self.key.stop()
        self.engine.dispose()

    def test_encrypted_owner_annotation_round_trip_and_author_delete(self) -> None:
        body = {
            "start_seconds": 12.25,
            "end_seconds": 16.5,
            "observations": ["left_arm_movement", "head_or_eye_deviation"],
            "description": "Synthetic observation note.",
        }
        created = self.client.post(
            "/api/recordings/REC-OWNER-01/clinical-annotations", json=body
        )
        self.assertEqual(created.status_code, 201, created.text)
        annotation = created.json()["annotation"]
        self.assertEqual(annotation["start_seconds"], body["start_seconds"])
        self.assertEqual(annotation["observations"], body["observations"])
        self.assertEqual(annotation["provenance"], "clinician_observation")
        self.assertEqual(annotation["annotator"], "authenticated owner")

        with Session(self.engine) as db:
            stored = db.exec(select(ClinicalAnnotation)).one()
            self.assertNotIn(b"Synthetic observation note", stored.payload_ciphertext)
            self.assertNotIn(b"left_arm_movement", stored.payload_ciphertext)
            self.assertEqual(stored.created_by_user_id, self.owner_id)

        listed = self.client.get(
            "/api/recordings/REC-OWNER-01/clinical-annotations"
        )
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertEqual(len(listed.json()["annotations"]), 1)
        self.assertIn("not a diagnosis", listed.json()["clinical_interpretation"])

        self.assertEqual(
            self.client.delete(
                f"/api/recordings/REC-OWNER-01/clinical-annotations/{annotation['annotation_id']}"
            ).status_code,
            204,
        )
        self.assertEqual(
            self.client.get(
                "/api/recordings/REC-OWNER-01/clinical-annotations"
            ).json()["annotations"],
            [],
        )
        with Session(self.engine) as db:
            events = db.exec(
                select(ClinicalAccessEvent).order_by(ClinicalAccessEvent.id)
            ).all()
            self.assertEqual(
                [event.action for event in events],
                [
                    "clinical_observation_create",
                    "clinical_observation_view",
                    "clinical_observation_delete",
                    "clinical_observation_view",
                ],
            )
            self.assertTrue(all(event.actor_user_id == self.owner_id for event in events))

    def test_invalid_interval_observation_and_cross_owner_access_are_rejected(self) -> None:
        base = {
            "start_seconds": 1,
            "end_seconds": 2,
            "observations": ["left_arm_movement"],
            "description": "",
        }
        for body in (
            {**base, "start_seconds": -1},
            {**base, "end_seconds": 121},
            {**base, "observations": ["invented_diagnosis"]},
        ):
            self.assertEqual(
                self.client.post(
                    "/api/recordings/REC-OWNER-01/clinical-annotations", json=body
                ).status_code,
                422,
            )

        self.app.dependency_overrides[require_api_auth] = lambda: User(
            id=2, public_id="USR-OTHER", email="other@example.test"
        )
        self.assertEqual(
            self.client.get(
                "/api/recordings/REC-OWNER-01/clinical-annotations"
            ).status_code,
            404,
        )

    def test_case_data_deletion_also_removes_its_access_events(self) -> None:
        self.client.get("/api/recordings/REC-OWNER-01/clinical-annotations")
        with Session(self.engine) as db:
            session = db.exec(select(EEGSession)).one()
            delete_sessions_data(db, [session])
            self.assertEqual(db.exec(select(ClinicalAccessEvent)).all(), [])
        self.assertEqual(
            self.client.get(
                "/api/recordings/REC-OWNER-01/clinical-annotations"
            ).status_code,
            404,
        )

    def test_case_recording_deletion_removes_annotations(self) -> None:
        created = self.client.post(
            "/api/recordings/REC-OWNER-01/clinical-annotations",
            json={
                "start_seconds": 0,
                "end_seconds": 1,
                "observations": ["uncertain_or_unobservable"],
                "description": "",
            },
        )
        self.assertEqual(created.status_code, 201, created.text)
        with Session(self.engine) as db:
            session = db.exec(select(EEGSession)).one()
            delete_sessions_data(db, [session])
        with Session(self.engine) as db:
            self.assertEqual(db.exec(select(ClinicalAnnotation)).all(), [])


if __name__ == "__main__":
    unittest.main()
