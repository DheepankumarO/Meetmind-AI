import pytest
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
