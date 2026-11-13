from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app import main
from backend.app.database import Base
from backend.app.routers import meetings
from backend.app.schemas.meeting_analysis import MeetingAnalysis
from backend.app.schemas.transcription import TranscriptSegment, TranscriptionResult
from backend.app.services import (
    file_storage,
    meeting_processor,
    meeting_repository,
    processing_job_repository,
)


@pytest.fixture
def retry_client(tmp_path, monkeypatch):
    database_path = tmp_path / "meetings.db"
    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(main, "create_db_and_tables", lambda: None)
    monkeypatch.setattr(meeting_repository, "SessionLocal", session)
    monkeypatch.setattr(processing_job_repository, "SessionLocal", session)
    for module in (file_storage, meetings, meeting_processor):
        monkeypatch.setattr(module, "UPLOAD_DIRECTORY", tmp_path / "uploads")

    try:
        with TestClient(main.app) as client:
            yield client
    finally:
        engine.dispose()


def test_retry_reuses_saved_transcript_and_speaker_labels(
    retry_client, tmp_path, monkeypatch,
):
    segment = TranscriptSegment(
        segment_index=0, start_seconds=0, end_seconds=2, text="Hello team.",
    )
    transcription = TranscriptionResult(
        transcript="Hello team.",
        segments=[segment],
        language="en",
        language_probability=1.0,
        duration_seconds=2,
    )
    audio_path = tmp_path / "extracted.wav"
    audio_path.write_bytes(b"extracted")
    extract = AsyncMock(return_value=audio_path)
    transcribe = AsyncMock(return_value=transcription)
    diarize = AsyncMock(
        return_value=[segment.model_copy(update={"speaker": "Speaker 2"})],
    )
    analyze = AsyncMock(side_effect=[
        HTTPException(504, "The local meeting-analysis service timed out."),
        HTTPException(503, "The local meeting-analysis service is unavailable."),
        MeetingAnalysis(summary="The team said hello."),
    ])

    async def create_playback(input_path: Path, temporary_name: str) -> Path:
        assert input_path.read_bytes() == b"original recording"
        playback = tmp_path / f"{temporary_name}.mp3"
        playback.write_bytes(b"playback")
        return playback

    monkeypatch.setattr(meeting_processor, "extract_audio", extract)
    monkeypatch.setattr(meeting_processor, "transcribe_audio", transcribe)
    monkeypatch.setattr(meeting_processor, "diarize_transcript", diarize)
    monkeypatch.setattr(meeting_processor, "analyze_transcript", analyze)
    monkeypatch.setattr(meeting_processor, "create_playback_audio", create_playback)
    monkeypatch.setattr(
        meeting_processor, "get_playback_path", lambda meeting_id: tmp_path / f"{meeting_id}.mp3",
    )

    upload = retry_client.post(
        "/meetings/upload",
        files={"file": ("meeting.wav", b"original recording", "audio/wav")},
        headers={"Origin": "http://localhost:5173"},
    )
    assert upload.status_code == 504
    assert "X-Processing-Job-ID" in upload.headers["access-control-expose-headers"]
    job_id = upload.headers["X-Processing-Job-ID"]
    job_url = f"/meetings/jobs/{job_id}"
    retry_url = f"{job_url}/retry"
    assert not audio_path.exists()

    failed_retry = retry_client.post(retry_url)
    assert failed_retry.status_code == 503
    assert failed_retry.headers["X-Processing-Job-ID"] == job_id
    failed_job = retry_client.get(job_url).json()
    assert (failed_job["status"], failed_job["stage"], failed_job["retry_count"]) == (
        "failed", "analyzing", 1,
    )

    response = retry_client.post(retry_url)
    assert response.status_code == 200, response.text
    meeting = response.json()
    assert meeting["transcript"] == "Hello team."
    assert meeting["segments"][0]["speaker"] == "Speaker 2"
    assert meeting["summary"] == "The team said hello."
    assert (tmp_path / f"{meeting['id']}.mp3").is_file()
    assert list((tmp_path / "uploads").iterdir()) == []

    completed_job = retry_client.get(job_url).json()
    assert completed_job["status"] == "completed"
    assert completed_job["meeting_id"] == meeting["id"]
    assert completed_job["retry_count"] == 2
    assert completed_job["error_message"] is None
    assert retry_client.post(retry_url).status_code == 409
    assert len(retry_client.get("/meetings").json()) == 1
    assert analyze.await_count == 3
    for call in analyze.await_args_list:
        assert call.args == ("Hello team.",)
    for operation in (extract, transcribe, diarize):
        operation.assert_awaited_once()


def test_claim_rejects_an_old_retry_request(retry_client):
    repository = processing_job_repository
    job = repository.create_processing_job_sync(
        original_filename="meeting.wav",
        stored_filename="recording.wav",
        content_type="audio/wav",
        size_bytes=100,
    )
    repository.update_processing_job_sync(job.id, status="failed", stage="analyzing")
    repository.claim_analysis_retry_sync(job.id, retry_count=0)

    with pytest.raises(HTTPException) as duplicate:
        repository.claim_analysis_retry_sync(job.id, retry_count=0)
    assert duplicate.value.status_code == 409

    repository.update_processing_job_sync(job.id, status="failed", stage="analyzing")
    with pytest.raises(HTTPException) as stale:
        repository.claim_analysis_retry_sync(job.id, retry_count=0)
    assert stale.value.status_code == 409
    assert repository.get_processing_job_sync(job.id).retry_count == 1
