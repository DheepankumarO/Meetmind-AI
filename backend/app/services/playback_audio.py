import asyncio
import subprocess
from pathlib import Path

from fastapi import HTTPException


PLAYBACK_DIRECTORY = (
    Path(__file__).resolve().parents[2]
    / "storage"
    / "playback"
)


def get_playback_path(meeting_id: int) -> Path:
    return PLAYBACK_DIRECTORY / f"{meeting_id}.mp3"


async def create_playback_audio(
    input_path: Path,
    temporary_name: str,
) -> Path:
    PLAYBACK_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        PLAYBACK_DIRECTORY / f"{temporary_name}.mp3"
    )

    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-codec:a",
        "libmp3lame",
        "-b:a",
        "64k",
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
                "Playback audio could not be created: "
                f"{result.stderr[-500:]}"
            ),
        )

    return output_path