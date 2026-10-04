from pathlib import Path

from fastapi import (
    APIRouter,
    File,
    HTTPException,
    UploadFile,
)
from fastapi.responses import FileResponse

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
from backend.app.services.playback_audio import (
    create_playback_audio,
    get_playback_path,
)

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
    temporary_playback_path: Path | None = None
    playback_was_saved = False

    try:
        audio_path = await extract_audio(uploaded_path)
        transcription_result = await transcribe_audio(audio_path)

        transcript = transcription_result.transcript

        meeting_analysis = await analyze_transcript(transcript)

        temporary_playback_path = await create_playback_audio(
            audio_path,
            uploaded_path.stem,
        )
        
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
            language=transcription_result.language,
            language_probability=(
                transcription_result.language_probability
            ),
            duration_seconds=transcription_result.duration_seconds,
            segments=transcription_result.segments,
            analysis=meeting_analysis,
        )

        final_playback_path = get_playback_path(
            saved_meeting.id,
        )

        temporary_playback_path.replace(
            final_playback_path,
        )

        playback_was_saved = True
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
    "/{meeting_id}/audio",
    response_class=FileResponse,
)
async def get_meeting_audio(
    meeting_id: int,
) -> FileResponse:
    await get_saved_meeting(meeting_id)

    playback_path = get_playback_path(meeting_id)

    if not playback_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Playback audio is not available for this meeting.",
        )

    return FileResponse(
    path=playback_path,
    media_type="audio/mpeg",
)
    
@router.get(
    "/{meeting_id}",
    response_model=MeetingRecord,
)
async def get_meeting(
    meeting_id: int,
) -> MeetingRecord:
    meeting = await get_saved_meeting(meeting_id)

    return MeetingRecord.model_validate(meeting)