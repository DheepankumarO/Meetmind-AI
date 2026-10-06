import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

from types import SimpleNamespace

from backend.app.routers import meetings as meetings_router
from backend.app.schemas.meeting_question import (
    MeetingAnswer,
)

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
        segments: list[object],
    ) -> MeetingAnswer:
        assert meeting_id == 7
        assert question == "What was decided?"
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