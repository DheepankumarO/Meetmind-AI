from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.app.schemas.meeting_analysis import MeetingRecord
from backend.app.services.audio_extractor import extract_audio
from backend.app.services.file_storage import (
    UPLOAD_DIRECTORY,
    save_upload,
)
from backend.app.services.meeting_analyzer import analyze_transcript
from backend.app.services.meeting_repository import (
    get_saved_meeting,
    list_saved_meetings,
    save_meeting,
)
from backend.app.services.transcription import transcribe_audio


router = APIRouter(
    prefix="/meetings",
    tags=["Meetings"],
)


@router.post(
    "/upload",
    response_model=MeetingRecord,
)
async def upload_meeting(
    file: UploadFile = File(...),
) -> MeetingRecord:
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

        saved_meeting = await save_meeting(
            original_filename=str(
                upload_result["original_filename"],
            ),
            content_type=(
                str(upload_result["content_type"])
                if upload_result["content_type"] is not None
                else None
            ),
            size_bytes=int(upload_result["size_bytes"]),
            transcript=transcript,
            language=str(transcription_result["language"]),
            language_probability=float(
                transcription_result["language_probability"],
            ),
            duration_seconds=float(
                transcription_result["duration_seconds"],
            ),
            analysis=meeting_analysis,
        )

        return MeetingRecord.model_validate(saved_meeting)

    finally:
        uploaded_path.unlink(missing_ok=True)

        if audio_path is not None:
            audio_path.unlink(missing_ok=True)


@router.get(
    "",
    response_model=list[MeetingRecord],
)
async def get_meeting_history() -> list[MeetingRecord]:
    meetings = await list_saved_meetings()

    return [
        MeetingRecord.model_validate(meeting)
        for meeting in meetings
    ]


@router.get(
    "/{meeting_id}",
    response_model=MeetingRecord,
)
async def get_meeting(
    meeting_id: int,
) -> MeetingRecord:
    meeting = await get_saved_meeting(meeting_id)

    return MeetingRecord.model_validate(meeting)