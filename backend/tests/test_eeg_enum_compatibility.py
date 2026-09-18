import unittest

from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, select

from backend.app.database.models import (
    AnalysisStatus,
    EEGRecording,
    EEGSession,
    ProcessingAttempt,
    ProcessingStage,
    ProcessingStatus,
    RecordingStatus,
)


class EEGEnumCompatibilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_legacy_lowercase_values_load_for_all_eeg_enum_columns(self) -> None:
        with Session(self.engine) as database:
            session = EEGSession(session_id="SES-LEGACY-ENUM")
            database.add(session)
            database.flush()
            assert session.id is not None
            recording = EEGRecording(
                record_id="REC-LEGACY-ENUM",
                session_db_id=session.id,
                original_filename="legacy.edf",
            )
            database.add(recording)
            database.flush()
            assert recording.id is not None
            database.add(
                ProcessingAttempt(
                    recording_db_id=recording.id,
                    session_db_id=session.id,
                    stage=ProcessingStage.PREPROCESSING,
                    status=ProcessingStatus.RUNNING,
                )
            )
            database.commit()

        with self.engine.begin() as connection:
            connection.execute(
                text("UPDATE sessions SET status = 'queued' WHERE session_id = :session_id"),
                {"session_id": "SES-LEGACY-ENUM"},
            )
            connection.execute(
                text("UPDATE recordings SET status = 'inferred' WHERE record_id = :record_id"),
                {"record_id": "REC-LEGACY-ENUM"},
            )
            connection.execute(
                text("UPDATE processing_attempts SET stage = 'preprocessing', status = 'running'"),
            )

        with Session(self.engine) as database:
            loaded_session = database.exec(select(EEGSession)).one()
            loaded_recording = database.exec(select(EEGRecording)).one()
            loaded_attempt = database.exec(select(ProcessingAttempt)).one()

        self.assertEqual(loaded_session.status, AnalysisStatus.QUEUED)
        self.assertEqual(loaded_recording.status, RecordingStatus.INFERRED)
        self.assertEqual(loaded_attempt.stage, ProcessingStage.PREPROCESSING)
        self.assertEqual(loaded_attempt.status, ProcessingStatus.RUNNING)

        with self.engine.begin() as connection:
            connection.execute(
                text("UPDATE sessions SET status = 'COMPLETED' WHERE session_id = :session_id"),
                {"session_id": "SES-LEGACY-ENUM"},
            )
            connection.execute(
                text("UPDATE recordings SET status = 'PROCESSED' WHERE record_id = :record_id"),
                {"record_id": "REC-LEGACY-ENUM"},
            )
            connection.execute(
                text("UPDATE processing_attempts SET stage = 'INFERENCE', status = 'SUCCEEDED'"),
            )

        with Session(self.engine) as database:
            loaded_session = database.exec(select(EEGSession)).one()
            loaded_recording = database.exec(select(EEGRecording)).one()
            loaded_attempt = database.exec(select(ProcessingAttempt)).one()

        self.assertEqual(loaded_session.status, AnalysisStatus.COMPLETED)
        self.assertEqual(loaded_recording.status, RecordingStatus.PROCESSED)
        self.assertEqual(loaded_attempt.stage, ProcessingStage.INFERENCE)
        self.assertEqual(loaded_attempt.status, ProcessingStatus.SUCCEEDED)


if __name__ == "__main__":
    unittest.main()
