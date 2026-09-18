"""Admission regressions for standalone privacy jobs."""

import asyncio
import io
from datetime import timedelta
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import UploadFile
from sqlmodel import Session, SQLModel, create_engine

from backend.app.database.models.video import (
    VideoPrivacyJob,
    VideoPrivacyProfile,
    VideoPrivacyStatus,
    utc_now,
)
from backend.app.services.video_privacy_service import (
    VideoPrivacyCapacityError,
    create_video_job,
)
from backend.app.services.video_storage_service import VideoStorage


class VideoPrivacyAdmissionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
        SQLModel.metadata.create_all(self.engine)

    def test_second_active_job_for_one_owner_is_rejected_before_encryption(self) -> None:
        with Session(self.engine) as db:
            db.add(
                VideoPrivacyJob(
                    owner_user_id=7,
                    job_id="VID-ACTIVE",
                    profile=VideoPrivacyProfile.FACE_REDACTED,
                    display_label="Video upload 01",
                    content_type="video/mp4",
                    status=VideoPrivacyStatus.PROCESSING,
                    current_stage="privacy-transform",
                    retention_expires_at=utc_now() + timedelta(hours=1),
                )
            )
            db.commit()
            upload = UploadFile(filename="patient.mp4", file=io.BytesIO(b"not-written"))
            with patch("backend.app.services.video_privacy_service.engine", self.engine), patch(
                "backend.app.services.video_privacy_service.VIDEO_PRIVACY_MAX_ACTIVE_JOBS_PER_OWNER", 1
            ), patch("backend.app.services.video_privacy_service.VIDEO_PRIVACY_MAX_ACTIVE_JOBS", 10), patch.object(
                VideoStorage, "save_upload", new=AsyncMock()
            ) as save_upload:
                with self.assertRaises(VideoPrivacyCapacityError):
                    asyncio.run(
                        create_video_job(
                            db,
                            VideoStorage(),
                            upload,
                            VideoPrivacyProfile.FACE_REDACTED,
                            owner_user_id=7,
                        )
                    )
            save_upload.assert_not_awaited()
