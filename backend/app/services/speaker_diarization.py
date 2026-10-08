import asyncio
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from backend.app.schemas.transcription import TranscriptSegment


DIARIZATION_MODEL = (
    "pyannote/speaker-diarization-community-1"
)


@dataclass(frozen=True)
class SpeakerTurn:
    start_seconds: float
    end_seconds: float
    speaker: str


def _overlap_seconds(
    segment: TranscriptSegment,
    turn: SpeakerTurn,
) -> float:
    return max(
        0.0,
        min(segment.end_seconds, turn.end_seconds)
        - max(segment.start_seconds, turn.start_seconds),
    )


def assign_speakers(
    segments: list[TranscriptSegment],
    turns: list[SpeakerTurn],
) -> list[TranscriptSegment]:
    """Assign the speaker with the most overlap to each transcript segment."""
    raw_to_display_name: dict[str, str] = {}

    for turn in sorted(turns, key=lambda item: item.start_seconds):
        if turn.speaker not in raw_to_display_name:
            raw_to_display_name[turn.speaker] = (
                f"Speaker {len(raw_to_display_name) + 1}"
            )

    labeled_segments: list[TranscriptSegment] = []

    for segment in segments:
        matching_turn = max(
            turns,
            key=lambda turn: _overlap_seconds(segment, turn),
            default=None,
        )

        overlap = (
            _overlap_seconds(segment, matching_turn)
            if matching_turn is not None
            else 0.0
        )

        speaker = (
            raw_to_display_name[matching_turn.speaker]
            if matching_turn is not None and overlap > 0
            else "Speaker 1"
        )

        labeled_segments.append(
            segment.model_copy(update={"speaker": speaker})
        )

    return labeled_segments


def _get_huggingface_token() -> str | None:
    return os.getenv("HUGGINGFACE_TOKEN") or os.getenv(
        "HF_TOKEN"
    )


@lru_cache(maxsize=1)
def get_diarization_pipeline() -> Any:
    token = _get_huggingface_token()

    if not token:
        return None

    try:
        from pyannote.audio import Pipeline
    except ImportError:
        return None

    return Pipeline.from_pretrained(
        DIARIZATION_MODEL,
        token=token,
    )


def diarize_transcript_sync(
    audio_path: Path,
    segments: list[TranscriptSegment],
) -> list[TranscriptSegment]:
    pipeline = get_diarization_pipeline()

    if pipeline is None:
        return segments

    output = pipeline(str(audio_path))
    annotation = output.exclusive_speaker_diarization
    turns = [
        SpeakerTurn(
            start_seconds=float(turn.start),
            end_seconds=float(turn.end),
            speaker=str(speaker),
        )
        for turn, speaker in annotation
    ]

    return assign_speakers(segments, turns)


async def diarize_transcript(
    audio_path: Path,
    segments: list[TranscriptSegment],
) -> list[TranscriptSegment]:
    return await asyncio.to_thread(
        diarize_transcript_sync,
        audio_path,
        segments,
    )
