import asyncio
import subprocess
from pathlib import Path

from fastapi import HTTPException


AUDIO_DIRECTORY = (
    Path(__file__).resolve().parents[2] / "storage" / "audio"
)


async def extract_audio(input_path: Path) -> Path:
    AUDIO_DIRECTORY.mkdir(parents=True, exist_ok=True)

    output_path = AUDIO_DIRECTORY / f"{input_path.stem}.wav"

    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        str(output_path),
    ]

    try:
        result = await asyncio.to_thread(
            subprocess.run,
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )

    except FileNotFoundError as error:
        raise HTTPException(
            status_code=500,
            detail="FFmpeg is not installed or available in PATH.",
        ) from error

    if result.returncode != 0:
        output_path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=422,
            detail=(
                "FFmpeg could not process the recording: "
                f"{result.stderr[-500:]}"
            ),
        )

    return output_path