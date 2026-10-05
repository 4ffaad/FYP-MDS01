"""Owner-scoped case projections expose safe names and report summaries."""

from __future__ import annotations

import base64
import os
import unittest
from unittest.mock import patch

from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from backend.app.database.models.case_profile import CasePatientProfile, utc_now
from backend.app.database.models.eeg import AnalysisStatus, EEGSession
from backend.app.database.models.video import (
    VideoPrivacyJob,
    VideoPrivacyProfile,
    VideoPrivacyStatus,
)
from backend.app.services.case_profile_service import CRYPTO_VERSION, encrypt_profile
from backend.app.services.case_service import get_case, list_cases


class CaseSummaryProjectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.key_patch = patch.dict(
            os.environ,
            {"MDS01_STORAGE_KEY": base64.b64encode(b"k" * 32).decode("ascii")},
        )
        self.key_patch.start()
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

    def tearDown(self) -> None:
        self.engine.dispose()
        self.key_patch.stop()

    def _add_case(
        self,
        owner_id: int,
        case_id: str,
        details: list[dict[str, str]],
        *,
        verification_status: str = "reviewed",
    ) -> None:
        nonce, ciphertext = encrypt_profile(
            owner_id,
            case_id,
            {"name": "", "hospital_id": "", "age": "", "findings": "", "details": details},
        )
        with Session(self.engine) as db:
            db.add(
                EEGSession(
                    session_id=f"SES-{case_id[-8:]}",
                    owner_user_id=owner_id,
                    case_id=case_id,
                    status=AnalysisStatus.COMPLETED,
                )
            )
            db.add(
                CasePatientProfile(
                    case_id=case_id,
                    owner_user_id=owner_id,
                    identity_nonce=nonce,
                    identity_ciphertext=ciphertext,
                    crypto_version=CRYPTO_VERSION,
                    verification_status=verification_status,
                    reviewed_by_user_id=(
                        owner_id if verification_status == "reviewed" else None
                    ),
                    reviewed_at=(
                        utc_now() if verification_status == "reviewed" else None
                    ),
                )
            )
            db.commit()

    def test_owner_list_and_detail_return_only_name_and_safe_conclusion(self) -> None:
        self._add_case(
            7,
            "CASE-ABCD1234",
            [
                {"label": "Patient Name", "value": "Synthetic Review Patient"},
                {"label": "Conclusion", "value": "Synthetic conclusion for review."},
                {"label": "Address", "value": "7 Synthetic Road"},
                {"label": "Contact phone", "value": "+1 555 555 5555"},
                {"label": "Hospital ID", "value": "SYNTHETIC-42"},
            ],
        )

        with Session(self.engine) as db:
            listing = list_cases(db, owner_user_id=7)
            detail = get_case(db, "CASE-ABCD1234", owner_user_id=7)

        self.assertEqual(len(listing), 1)
        self.assertEqual(listing[0]["patient_name"], "Synthetic Review Patient")
        self.assertEqual(listing[0]["report_summary"], "Synthetic conclusion for review.")
        assert detail is not None
        self.assertEqual(detail["patient_name"], "Synthetic Review Patient")
        self.assertEqual(detail["report_summary"], "Synthetic conclusion for review.")
        output = repr((listing, detail))
        for private_value in ("Synthetic Road", "555 555 5555", "SYNTHETIC-42"):
            self.assertNotIn(private_value, output)

    def test_global_admin_projection_never_decrypts_owner_names(self) -> None:
        self._add_case(
            7,
            "CASE-ABCD1234",
            [{"label": "Patient Name", "value": "Synthetic Private Name"}],
        )

        with Session(self.engine) as db:
            listing = list_cases(db, owner_user_id=None)
            detail = get_case(db, "CASE-ABCD1234", owner_user_id=None)

        self.assertIsNone(listing[0]["patient_name"])
        self.assertIsNone(listing[0]["report_summary"])
        assert detail is not None
        self.assertIsNone(detail["patient_name"])
        self.assertNotIn("Synthetic Private Name", repr((listing, detail)))

    def test_global_history_only_projects_the_requesting_admins_own_profile(self) -> None:
        self._add_case(
            7,
            "CASE-ABCD1234",
            [{"label": "Patient Name", "value": "Synthetic Owner Name"}],
        )
        self._add_case(
            8,
            "CASE-WXYZ9876",
            [{"label": "Patient Name", "value": "Synthetic Other Name"}],
        )

        with Session(self.engine) as db:
            listing = list_cases(db, owner_user_id=None, profile_owner_user_id=7)

        names_by_case = {item["case_id"]: item["patient_name"] for item in listing}
        self.assertEqual(names_by_case["CASE-ABCD1234"], "Synthetic Owner Name")
        self.assertIsNone(names_by_case["CASE-WXYZ9876"])
        self.assertNotIn("Synthetic Other Name", repr(listing))

    def test_owner_summaries_show_auto_extracted_names_without_revealing_other_fields(self) -> None:
        self._add_case(
            7,
            "CASE-A0701234",
            [
                {"label": "Patient Name", "value": "Synthetic Auto Patient"},
                {"label": "Hospital ID", "value": "SYNTHETIC-HOSPITAL-42"},
                {"label": "Diagnosis", "value": "Synthetic diagnosis."},
            ],
            verification_status="auto_extracted",
        )

        with Session(self.engine) as db:
            listing = list_cases(db, owner_user_id=7)
            detail = get_case(db, "CASE-A0701234", owner_user_id=7)
            other_owner_view = list_cases(db, profile_owner_user_id=8)

        self.assertEqual(listing[0]["patient_name"], "Synthetic Auto Patient")
        self.assertEqual(
            listing[0]["patient_name_verification_status"], "auto_extracted"
        )
        assert detail is not None
        self.assertEqual(detail["patient_name"], "Synthetic Auto Patient")
        self.assertNotIn("SYNTHETIC-HOSPITAL-42", repr((listing, detail)))
        self.assertIsNone(other_owner_view[0]["patient_name"])

    def test_conclusion_with_contact_data_is_not_projected(self) -> None:
        self._add_case(
            7,
            "CASE-ABCD1234",
            [
                {"label": "Patient Name", "value": "Synthetic Review Patient"},
                {
                    "label": "Conclusions",
                    "value": "Synthetic summary. Contact +1 555 555 5555.",
                },
            ],
        )

        with Session(self.engine) as db:
            listing = list_cases(db, owner_user_id=7)

        self.assertIsNone(listing[0]["report_summary"])
        self.assertNotIn("555 555 5555", repr(listing))

    def test_privacy_only_case_remains_in_history_without_counting_as_vsvig(self) -> None:
        case_id = "CASE-ABCDEF12"
        with Session(self.engine) as db:
            db.add(
                VideoPrivacyJob(
                    case_id=case_id,
                    job_id="VPR-SYNTHETIC-1",
                    profile=VideoPrivacyProfile.FACE_REDACTED_POSE_PREVIEW,
                    status=VideoPrivacyStatus.READY,
                    display_label="Synthetic privacy preview",
                )
            )
            db.commit()
            listing = list_cases(db, owner_user_id=None)
            detail = get_case(db, case_id, owner_user_id=None)

        self.assertEqual(listing[0]["case_id"], case_id)
        self.assertEqual(listing[0]["analysis_count"], 0)
        self.assertEqual(listing[0]["privacy_preview_count"], 1)
        self.assertEqual(listing[0]["modalities"], ["video"])
        assert detail is not None
        self.assertEqual(detail["analyses"], [])

    def test_case_list_uses_bounded_recording_summary_queries(self) -> None:
        with Session(self.engine) as db:
            for index in range(4):
                db.add(
                    EEGSession(
                        session_id=f"SES-SYNTHETIC-{index}",
                        owner_user_id=7,
                        case_id=f"CASE-SYNTH{index:02d}",
                        status=AnalysisStatus.COMPLETED,
                    )
                )
            db.commit()

        selects = 0

        def count_selects(_connection, _cursor, statement, _parameters, _context, _executemany):
            nonlocal selects
            if statement.lstrip().upper().startswith("SELECT"):
                selects += 1

        event.listen(self.engine, "before_cursor_execute", count_selects)
        try:
            with Session(self.engine) as db:
                listing = list_cases(db, owner_user_id=7)
        finally:
            event.remove(self.engine, "before_cursor_execute", count_selects)

        self.assertEqual(len(listing), 4)
        self.assertEqual(selects, 5)


if __name__ == "__main__":
    unittest.main()
