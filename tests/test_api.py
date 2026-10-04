import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


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