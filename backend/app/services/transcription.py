import asyncio
import gc
from functools import lru_cache
from pathlib import Path

from faster_whisper import WhisperModel
from fastapi import HTTPException

from backend.app.schemas.transcription import (
    TranscriptSegment,
    TranscriptionResult,
)


MODEL_SIZE = "small.en"


@lru_cache(maxsize=1)
def get_whisper_model() -> WhisperModel:
    return WhisperModel(
        MODEL_SIZE,
        device="cpu",
        compute_type="int8",
    )


def transcribe_sync(
    audio_path: Path,
) -> TranscriptionResult:
    model = get_whisper_model()

    generated_segments, information = model.transcribe(
        str(audio_path),
        beam_size=5,
        vad_filter=True,
    )

    transcript_parts: list[str] = []
    transcript_segments: list[TranscriptSegment] = []

    for segment in generated_segments:
        text = segment.text.strip()

        if not text:
            continue

        transcript_parts.append(text)

        transcript_segments.append(
            TranscriptSegment(
                segment_index=len(transcript_segments),
                start_seconds=round(float(segment.start), 2),
                end_seconds=round(float(segment.end), 2),
                text=text,
            )
        )

    return TranscriptionResult(
        transcript=" ".join(transcript_parts),
        segments=transcript_segments,
        language=information.language,
        language_probability=round(
            information.language_probability,
            4,
        ),
        duration_seconds=round(
            information.duration,
            2,
        ),
    )


async def transcribe_audio(
    audio_path: Path,
) -> TranscriptionResult:
    try:
        return await asyncio.to_thread(
            transcribe_sync,
            audio_path,
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Local transcription failed.",
        ) from error

    finally:
        get_whisper_model.cache_clear()
        gc.collect()