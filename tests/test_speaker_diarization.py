from backend.app.schemas.transcription import TranscriptSegment
from backend.app.services.speaker_diarization import (
    SpeakerTurn,
    assign_speakers,
)


def test_assigns_speaker_with_largest_overlap() -> None:
    segments = [
        TranscriptSegment(
            segment_index=0,
            start_seconds=0,
            end_seconds=4,
            text="First speaker talks.",
        ),
        TranscriptSegment(
            segment_index=1,
            start_seconds=4,
            end_seconds=8,
            text="Second speaker talks.",
        ),
    ]
    turns = [
        SpeakerTurn(0, 3.5, "SPEAKER_02"),
        SpeakerTurn(3.5, 8, "SPEAKER_07"),
    ]

    result = assign_speakers(segments, turns)

    assert [segment.speaker for segment in result] == [
        "Speaker 1",
        "Speaker 2",
    ]


def test_defaults_to_speaker_one_without_turns() -> None:
    segment = TranscriptSegment(
        segment_index=0,
        start_seconds=0,
        end_seconds=2,
        text="A short sentence.",
    )

    result = assign_speakers([segment], [])

    assert result[0].speaker == "Speaker 1"
