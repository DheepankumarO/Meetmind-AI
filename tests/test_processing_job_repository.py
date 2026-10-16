import asyncio

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.database import Base
from backend.app.models import meeting  # noqa: F401
from backend.app.services import processing_job_repository


@pytest.fixture
def job_database(tmp_path, monkeypatch):
    # A separate database for this test, not your real meeting database.
    database_path = tmp_path / "jobs.db"

    engine = create_engine(
        f"sqlite:///{database_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )

    Base.metadata.create_all(bind=engine)

    test_session = sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )

    monkeypatch.setattr(
        processing_job_repository,
        "SessionLocal",
        test_session,
    )

    yield

    engine.dispose()


def test_job_can_be_loaded_after_creation(job_database):
    created_job = asyncio.run(
        processing_job_repository.create_processing_job(
            original_filename="meeting.wav",
            stored_filename="unique-meeting.wav",
            content_type="audio/wav",
            size_bytes=1000,
        )
    )

    # Creation closed its session. Retrieval opens a new one.
    saved_job = asyncio.run(
        processing_job_repository.get_processing_job(
            created_job.id,
        )
    )

    assert saved_job.id == created_job.id
    assert saved_job.original_filename == "meeting.wav"
    assert saved_job.stored_filename == "unique-meeting.wav"
    assert saved_job.size_bytes == 1000
    assert saved_job.status == "queued"
    assert saved_job.stage == "uploaded"
    assert saved_job.meeting_id is None
    assert saved_job.checkpoint is None


def test_missing_job_returns_404(job_database):
    with pytest.raises(HTTPException) as error:
        asyncio.run(
            processing_job_repository.get_processing_job(999)
        )

    assert error.value.status_code == 404
    assert error.value.detail == "Processing job not found."
    
def test_progress_updates_preserve_previous_checkpoints(job_database):
    job = asyncio.run(
        processing_job_repository.create_processing_job(
            original_filename="meeting.wav",
            stored_filename="progress-meeting.wav",
            content_type="audio/wav",
            size_bytes=1000,
        )
    )

    asyncio.run(
        processing_job_repository.update_processing_job(
            job.id,
            status="processing",
            stage="diarizing",
            checkpoint={
                "transcription": {
                    "transcript": "Release the beta on Friday.",
                },
            },
        )
    )

    asyncio.run(
        processing_job_repository.update_processing_job(
            job.id,
            status="processing",
            stage="analyzing",
            checkpoint={
                "speaker_segments": [
                    {"speaker": "Speaker 1", "text": "Release the beta on Friday."},
                ],
            },
        )
    )

    saved_job = asyncio.run(
        processing_job_repository.get_processing_job(job.id)
    )

    assert saved_job.status == "processing"
    assert saved_job.stage == "analyzing"
    assert saved_job.checkpoint == {
        "transcription": {
            "transcript": "Release the beta on Friday.",
        },
        "speaker_segments": [
            {"speaker": "Speaker 1", "text": "Release the beta on Friday."},
        ],
    }


def test_failure_keeps_completed_work(job_database):
    job = asyncio.run(
        processing_job_repository.create_processing_job(
            original_filename="meeting.wav",
            stored_filename="failed-meeting.wav",
            content_type="audio/wav",
            size_bytes=1000,
        )
    )

    asyncio.run(
        processing_job_repository.update_processing_job(
            job.id,
            status="processing",
            stage="analyzing",
            checkpoint={
                "transcription": {"transcript": "Hello team."},
            },
        )
    )

    asyncio.run(
        processing_job_repository.update_processing_job(
            job.id,
            status="failed",
            stage="analyzing",
            error_message="The analysis service is unavailable.",
        )
    )

    saved_job = asyncio.run(
        processing_job_repository.get_processing_job(job.id)
    )

    assert saved_job.status == "failed"
    assert saved_job.stage == "analyzing"
    assert saved_job.error_message == (
        "The analysis service is unavailable."
    )
    assert saved_job.checkpoint == {
        "transcription": {"transcript": "Hello team."},
    }


def test_updating_missing_job_returns_404(job_database):
    with pytest.raises(HTTPException) as error:
        asyncio.run(
            processing_job_repository.update_processing_job(
                999,
                status="processing",
                stage="transcribing",
            )
        )

    assert error.value.status_code == 404
    
def test_saved_meeting_is_linked_to_its_job(
    job_database,
    monkeypatch,
):
    from backend.app.schemas.meeting_analysis import MeetingAnalysis
    from backend.app.schemas.transcription import TranscriptSegment
    from backend.app.services import meeting_repository

    monkeypatch.setattr(
        meeting_repository,
        "SessionLocal",
        processing_job_repository.SessionLocal,
    )

    job = asyncio.run(
        processing_job_repository.create_processing_job(
            original_filename="meeting.wav",
            stored_filename="linked-meeting.wav",
            content_type="audio/wav",
            size_bytes=1000,
        )
    )

    saved_meeting = asyncio.run(
        meeting_repository.save_meeting(
            original_filename="meeting.wav",
            content_type="audio/wav",
            size_bytes=1000,
            transcript="Hello team.",
            segments=[
                TranscriptSegment(
                    segment_index=0,
                    start_seconds=0,
                    end_seconds=2,
                    text="Hello team.",
                ),
            ],
            language="en",
            language_probability=1.0,
            duration_seconds=2,
            analysis=MeetingAnalysis(
                summary="A greeting.",
            ),
            processing_job_id=job.id,
        )
    )

    saved_job = asyncio.run(
        processing_job_repository.get_processing_job(job.id)
    )

    assert saved_job.meeting_id == saved_meeting.id