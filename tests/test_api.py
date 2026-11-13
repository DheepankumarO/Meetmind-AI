import pytest
from fastapi import HTTPException
from httpx import ReadTimeout

from backend.app.schemas.processing_job import ProcessingJobRecord
from fastapi.testclient import TestClient

from backend.app.main import app

from types import SimpleNamespace

from backend.app.routers import meetings as meetings_router
from backend.app.schemas.meeting_question import (
    MeetingAnswer,
)
from backend.app.schemas.meeting_analysis import MeetingRecord
from backend.app.schemas.transcription import TranscriptSegment


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def test_health_endpoint(
    client: TestClient,
) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
    }


def test_meeting_history_returns_list(
    client: TestClient,
) -> None:
    response = client.get("/meetings")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_missing_meeting_returns_404(
    client: TestClient,
) -> None:
    response = client.get(
        "/meetings/2147483647",
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Meeting not found.",
    }


def test_upload_rejects_unsupported_file(
    client: TestClient,
) -> None:
    response = client.post(
        "/meetings/upload",
        files={
            "file": (
                "meeting-notes.txt",
                b"This is not an audio recording.",
                "text/plain",
            ),
        },
    )

    assert response.status_code == 415
    assert response.json() == {
        "detail": "Unsupported file type: .txt",
    }

def test_missing_meeting_audio_returns_404(
    client: TestClient,
) -> None:
    response = client.get(
        "/meetings/2147483647/audio",
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Meeting not found.",
    }

def test_ask_meeting_returns_grounded_answer(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_get_saved_meeting(
        meeting_id: int,
    ) -> SimpleNamespace:
        return SimpleNamespace(
            id=meeting_id,
            segments=[],
        )

    async def fake_answer_meeting_question(
        *,
        meeting_id: int,
        question: str,
        history: list[object],
        segments: list[object],
    ) -> MeetingAnswer:
        assert meeting_id == 7
        assert question == "What was decided?"
        assert history == []
        assert segments == []

        return MeetingAnswer(
            meeting_id=meeting_id,
            question=question,
            answer="The team decided to add automated tests.",
            answer_found=True,
            sources=[],
        )

    monkeypatch.setattr(
        meetings_router,
        "get_saved_meeting",
        fake_get_saved_meeting,
    )

    monkeypatch.setattr(
        meetings_router,
        "answer_meeting_question",
        fake_answer_meeting_question,
    )

    response = client.post(
        "/meetings/7/ask",
        json={
            "question": "What was decided?",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "meeting_id": 7,
        "question": "What was decided?",
        "answer": (
            "The team decided to add automated tests."
        ),
        "answer_found": True,
        "sources": [],
    }


def test_ask_meeting_rejects_empty_question(
    client: TestClient,
) -> None:
    response = client.post(
        "/meetings/7/ask",
        json={
            "question": "",
        },
    )

    assert response.status_code == 422


def test_rename_speaker_returns_updated_meeting(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_rename_saved_speaker(
        meeting_id: int,
        current_name: str,
        new_name: str,
    ) -> MeetingRecord:
        assert meeting_id == 7
        assert current_name == "Speaker 1"
        assert new_name == "Dheepan"

        return MeetingRecord(
            id=meeting_id,
            original_filename="meeting.wav",
            content_type="audio/wav",
            size_bytes=100,
            transcript="Hello.",
            segments=[
                TranscriptSegment(
                    segment_index=0,
                    start_seconds=0,
                    end_seconds=1,
                    text="Hello.",
                    speaker=new_name,
                )
            ],
            language="en",
            language_probability=1,
            duration_seconds=1,
            summary="A greeting.",
            key_topics=[],
            decisions=[],
            action_items=[],
            created_at="2026-10-08T00:00:00Z",
        )

    monkeypatch.setattr(
        meetings_router,
        "rename_saved_speaker",
        fake_rename_saved_speaker,
    )

    response = client.patch(
        "/meetings/7/speakers",
        json={
            "current_name": "Speaker 1",
            "new_name": "Dheepan",
        },
    )

    assert response.status_code == 200
    assert response.json()["segments"][0]["speaker"] == "Dheepan"


def test_rename_speaker_rejects_empty_name(
    client: TestClient,
) -> None:
    response = client.patch(
        "/meetings/7/speakers",
        json={
            "current_name": "Speaker 1",
            "new_name": "   ",
        },
    )

    assert response.status_code == 422

def test_processing_job_status_is_available(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_get_processing_job(
        job_id: int,
    ) -> SimpleNamespace:
        assert job_id == 12

        return SimpleNamespace(
            id=job_id,
            original_filename="meeting.wav",
            status="failed",
            stage="analyzing",
            error_message="The analysis service is unavailable.",
            retry_count=0,
            meeting_id=None,
            created_at="2026-10-13T00:00:00Z",
            updated_at="2026-10-13T00:05:00Z",
            checkpoint={"transcription": {"transcript": "Hello."}},
            stored_filename="internal-recording.wav",
        )

    monkeypatch.setattr(
        meetings_router,
        "get_processing_job",
        fake_get_processing_job,
    )

    response = client.get("/meetings/jobs/12")

    assert response.status_code == 200

    result = response.json()

    # Validate the public response, including its timestamps.
    ProcessingJobRecord.model_validate(result)

    assert result["id"] == 12
    assert result["status"] == "failed"
    assert result["stage"] == "analyzing"
    assert result["error_message"] == (
        "The analysis service is unavailable."
    )

    # Internal processing data should stay out of this response.
    assert "checkpoint" not in result
    assert "stored_filename" not in result


def test_missing_processing_job_returns_404(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_get_processing_job(
        job_id: int,
    ) -> None:
        raise HTTPException(
            status_code=404,
            detail="Processing job not found.",
        )

    monkeypatch.setattr(
        meetings_router,
        "get_processing_job",
        fake_get_processing_job,
    )

    response = client.get("/meetings/jobs/999")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Processing job not found.",
    }


@pytest.mark.parametrize(
    ("ollama_error", "status_code", "error_message"),
    [
        (
            ConnectionError("Ollama is unavailable."),
            503,
            "The local meeting-analysis service is unavailable. "
            "Make sure Ollama is running.",
        ),
        (
            ReadTimeout("Ollama stopped responding."),
            504,
            "The local meeting-analysis service timed out.",
        ),
    ],
    ids=["unavailable", "timeout"],
)
def test_failed_upload_preserves_recording_and_checkpoints(
    client,
    monkeypatch,
    tmp_path,
    ollama_error,
    status_code,
    error_message,
):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, Mock

    from backend.app.schemas.transcription import (
        TranscriptSegment,
        TranscriptionResult,
    )
    from backend.app.services import (
        file_storage,
        meeting_analyzer,
        meeting_processor,
    )

    upload_directory = tmp_path / "uploads"
    audio_path = tmp_path / "extracted.wav"
    audio_path.write_bytes(b"temporary audio")

    transcription = TranscriptionResult(
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
    )

    async def fake_get_processing_job(job_id):
        recording = next(upload_directory.iterdir())

        return SimpleNamespace(
            id=job_id,
            stored_filename=recording.name,
            original_filename="meeting.wav",
            content_type="audio/wav",
            size_bytes=len(b"recording"),
        )

    monkeypatch.setattr(
        file_storage,
        "UPLOAD_DIRECTORY",
        upload_directory,
    )
    monkeypatch.setattr(
        meetings_router,
        "UPLOAD_DIRECTORY",
        upload_directory,
    )
    monkeypatch.setattr(
        meeting_processor,
        "UPLOAD_DIRECTORY",
        upload_directory,
    )

    # Job creation happens in the router.
    monkeypatch.setattr(
        meetings_router,
        "create_processing_job",
        AsyncMock(return_value=SimpleNamespace(id=12)),
    )

    update_job = AsyncMock()
    ollama_client = Mock()
    ollama_client.chat.side_effect = ollama_error
    create_ollama_client = Mock(return_value=ollama_client)
    monkeypatch.setattr(meeting_analyzer, "Client", create_ollama_client)

    # Job lookup and processing now happen in the service.
    replacements = {
        "get_processing_job": fake_get_processing_job,
        "update_processing_job": update_job,
        "extract_audio": AsyncMock(return_value=audio_path),
        "transcribe_audio": AsyncMock(return_value=transcription),
        "diarize_transcript": AsyncMock(
            return_value=transcription.segments,
        ),
    }

    for name, replacement in replacements.items():
        monkeypatch.setattr(
            meeting_processor,
            name,
            replacement,
        )

    assert meeting_processor.update_processing_job is update_job

    response = client.post(
        "/meetings/upload",
        files={
            "file": ("meeting.wav", b"recording", "audio/wav"),
        },
    )

    assert response.status_code == status_code, response.text
    assert response.json() == {"detail": error_message}
    assert response.headers["X-Processing-Job-ID"] == "12"
    assert create_ollama_client.call_args.kwargs["timeout"] > 0

    assert update_job.await_args.kwargs == {
        "status": "failed",
        "stage": "analyzing",
        "error_message": error_message,
    }

    assert any(
        call.kwargs.get("checkpoint", {}).get("transcription")
        == transcription.model_dump(mode="json")
        for call in update_job.await_args_list
    )

    recordings = list(upload_directory.iterdir())
    assert len(recordings) == 1
    assert recordings[0].read_bytes() == b"recording"
    assert not audio_path.exists()
