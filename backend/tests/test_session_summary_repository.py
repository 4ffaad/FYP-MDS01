"""Focused regressions for safe, bulk session prediction summaries."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from sqlalchemy import event
from sqlmodel import SQLModel, Session, create_engine

from backend.app.database.models.eeg import (
    AnalysisStatus,
    EEGRecording,
    EEGSession,
    Prediction,
    RecordingStatus,
)
from backend.app.database.repository import (
    list_flagged_prediction_windows,
    list_flagged_window_counts,
    list_model_metadata,
    list_predictions,
)
from backend.app.services.session_service import public_session, public_session_list


class SessionSummaryRepositoryTests(unittest.TestCase):
    """Verify only completed recordings contribute public model results."""

    def setUp(self) -> None:
        """Create a disposable SQLite database for each regression."""

        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
        SQLModel.metadata.create_all(self.engine)
        self.addCleanup(self.engine.dispose)

    @staticmethod
    def _prediction(recording_id: int, window_index: int, detected: bool = True) -> Prediction:
        """Build one deterministic prediction row for summary assertions."""

        start = float(window_index * 4)
        return Prediction(
            recording_db_id=recording_id,
            window_index=window_index,
            model_name="summary-model",
            model_version="1.0",
            probability=0.9 if detected else 0.1,
            score_type="development_score",
            seizure_detected=detected,
            start_seconds=start,
            end_seconds=start + 4.0,
        )

    def test_failed_predictions_are_excluded_from_every_public_summary(self) -> None:
        """Stale failed-record predictions must not create public alerts or results."""

        with Session(self.engine) as db:
            session = EEGSession(
                session_id="SES-SAFE-SUMMARY",
                status=AnalysisStatus.COMPLETED_WITH_ERRORS,
            )
            db.add(session)
            db.commit()
            db.refresh(session)

            completed = EEGRecording(
                record_id="REC-COMPLETED",
                session_db_id=session.id,
                sequence_index=1,
                original_filename="completed.edf",
                status=RecordingStatus.INFERRED,
            )
            failed = EEGRecording(
                record_id="REC-FAILED",
                session_db_id=session.id,
                sequence_index=2,
                original_filename="failed.edf",
                status=RecordingStatus.FAILED,
                error_message="Safe processing failure.",
            )
            db.add(completed)
            db.add(failed)
            db.commit()
            db.refresh(completed)
            db.refresh(failed)

            db.add(self._prediction(completed.id, 0))
            db.add(self._prediction(completed.id, 1))
            db.add(self._prediction(failed.id, 20))
            db.commit()

            record_ids = [completed.id, failed.id]
            payload = public_session(db, session)
            counts = list_flagged_window_counts(db, record_ids)
            metadata = list_model_metadata(db, record_ids)
            windows = list_flagged_prediction_windows(db, record_ids)
            failed_predictions = list_predictions(db, failed.id)

        records = {record["record_id"]: record for record in payload["recordings"]}
        completed_payload = records["REC-COMPLETED"]
        failed_payload = records["REC-FAILED"]

        self.assertEqual(payload["summary"], {"model_alert_recordings": 1})
        self.assertEqual(counts, {completed.id: 2, failed.id: 0})
        self.assertIn(completed.id, metadata)
        self.assertNotIn(failed.id, metadata)
        self.assertIn(completed.id, windows)
        self.assertNotIn(failed.id, windows)
        self.assertEqual(failed_predictions, [])

        self.assertTrue(completed_payload["model_alert"])
        self.assertEqual(completed_payload["model_alert_window_count"], 2)
        self.assertEqual(
            completed_payload["alert_intervals"],
            [{"start_seconds": 0.0, "end_seconds": 8.0}],
        )
        self.assertFalse(failed_payload["model_alert"])
        self.assertEqual(failed_payload["model_alert_window_count"], 0)
        self.assertEqual(failed_payload["alert_intervals"], [])
        self.assertIsNone(failed_payload["model_name"])
        self.assertIsNone(failed_payload["model_version"])
        self.assertIsNone(failed_payload["score_type"])
        self.assertEqual(set(completed_payload), set(failed_payload))

    def test_session_list_bulk_queries_preserve_each_session_summary(self) -> None:
        """Session listing uses fixed bulk prediction queries, not one per recording."""

        with Session(self.engine) as db:
            older = EEGSession(
                session_id="SES-OLDER",
                status=AnalysisStatus.COMPLETED,
                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )
            newer = EEGSession(
                session_id="SES-NEWER",
                status=AnalysisStatus.COMPLETED_WITH_ERRORS,
                created_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
            )
            db.add(older)
            db.add(newer)
            db.commit()
            db.refresh(older)
            db.refresh(newer)

            older_record = EEGRecording(
                record_id="REC-OLDER",
                session_db_id=older.id,
                sequence_index=1,
                original_filename="older.edf",
                status=RecordingStatus.INFERRED,
            )
            newer_record = EEGRecording(
                record_id="REC-NEWER",
                session_db_id=newer.id,
                sequence_index=1,
                original_filename="newer.edf",
                status=RecordingStatus.INFERRED,
            )
            failed_record = EEGRecording(
                record_id="REC-NEWER-FAILED",
                session_db_id=newer.id,
                sequence_index=2,
                original_filename="newer-failed.edf",
                status=RecordingStatus.FAILED,
            )
            db.add(older_record)
            db.add(newer_record)
            db.add(failed_record)
            db.commit()
            db.refresh(older_record)
            db.refresh(newer_record)
            db.refresh(failed_record)

            db.add(self._prediction(older_record.id, 0, detected=False))
            db.add(self._prediction(newer_record.id, 3))
            db.add(self._prediction(failed_record.id, 4))
            db.commit()

            prediction_selects: list[str] = []

            def capture_prediction_selects(_connection, _cursor, statement, _parameters, _context, _many):
                normalized = statement.lstrip().lower()
                if normalized.startswith("select") and "predictions" in normalized:
                    prediction_selects.append(normalized)

            event.listen(self.engine, "before_cursor_execute", capture_prediction_selects)
            try:
                payloads = public_session_list(db)
            finally:
                event.remove(self.engine, "before_cursor_execute", capture_prediction_selects)

        self.assertEqual([payload["session_id"] for payload in payloads], ["SES-NEWER", "SES-OLDER"])
        summaries = {payload["session_id"]: payload["summary"] for payload in payloads}
        self.assertEqual(summaries["SES-NEWER"], {"model_alert_recordings": 1})
        self.assertEqual(summaries["SES-OLDER"], {"model_alert_recordings": 0})
        newer_records = {record["record_id"]: record for record in payloads[0]["recordings"]}
        self.assertEqual(
            newer_records["REC-NEWER"]["alert_intervals"],
            [{"start_seconds": 12.0, "end_seconds": 16.0}],
        )
        self.assertFalse(newer_records["REC-NEWER-FAILED"]["model_alert"])
        self.assertEqual(newer_records["REC-NEWER-FAILED"]["alert_intervals"], [])
        self.assertEqual(len(prediction_selects), 3)


if __name__ == "__main__":
    unittest.main()
