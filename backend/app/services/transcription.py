import asyncio
import gc
from fastapi import HTTPException
from functools import lru_cache
from pathlib import Path

from faster_whisper import WhisperModel


MODEL_SIZE = "small.en"


@lru_cache(maxsize=1)
def get_whisper_model() -> WhisperModel:
    return WhisperModel(
        MODEL_SIZE,
        device="cpu",
        compute_type="int8",
    )


def transcribe_sync(audio_path: Path) -> dict[str, str | float]:
    model = get_whisper_model()

    segments, information = model.transcribe(
        str(audio_path),
        beam_size=5,
        vad_filter=True,
    )

    transcript_parts = [
        segment.text.strip()
        for segment in segments
        if segment.text.strip()
    ]

    transcript = " ".join(transcript_parts)

    return {
        "transcript": transcript,
        "language": information.language,
        "language_probability": round(
            information.language_probability,
            4,
        ),
        "duration_seconds": round(
            information.duration,
            2,
        ),
    }


async def transcribe_audio(
    audio_path: Path,
) -> dict[str, str | float]:
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