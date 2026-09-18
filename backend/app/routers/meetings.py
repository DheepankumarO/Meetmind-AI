from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.app.services.audio_extractor import extract_audio
from backend.app.services.file_storage import (
    UPLOAD_DIRECTORY,
    save_upload,
)
from backend.app.services.meeting_analyzer import analyze_transcript
from backend.app.services.transcription import transcribe_audio


router = APIRouter(
    prefix="/meetings",
    tags=["Meetings"],
)


@router.post("/upload")
async def upload_meeting(
    file: UploadFile = File(...),
) -> dict[str, object]:
    upload_result = await save_upload(file)

    stored_filename = upload_result["stored_filename"]

    if not isinstance(stored_filename, str):
        raise HTTPException(
            status_code=500,
            detail="The stored filename is invalid.",
        )

    uploaded_path = UPLOAD_DIRECTORY / stored_filename
    audio_path: Path | None = None

    try:
        audio_path = await extract_audio(uploaded_path)
        transcription_result = await transcribe_audio(audio_path)

        transcript = transcription_result["transcript"]

        if not isinstance(transcript, str):
            raise HTTPException(
                status_code=500,
                detail="The generated transcript is invalid.",
            )

        meeting_analysis = await analyze_transcript(transcript)

        return {
            "status": "processed",
            "original_filename": upload_result["original_filename"],
            "content_type": upload_result["content_type"],
            "size_bytes": upload_result["size_bytes"],
            **transcription_result,
            "analysis": meeting_analysis.model_dump(),
        }

    finally:
        uploaded_path.unlink(missing_ok=True)

        if audio_path is not None:
            audio_path.unlink(missing_ok=True)