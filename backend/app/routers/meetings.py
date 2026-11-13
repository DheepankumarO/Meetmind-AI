import logging
from pathlib import Path

from fastapi import (
    APIRouter,
    File,
    HTTPException,
    Response,
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
    rename_saved_speaker,
    save_meeting,
)
from backend.app.schemas.speaker import SpeakerRename
from backend.app.services.transcription import transcribe_audio
from backend.app.services.speaker_diarization import (
    diarize_transcript,
)
from backend.app.services.playback_audio import (
    create_playback_audio,
    get_playback_path,
)

from backend.app.schemas.meeting_question import (
    MeetingAnswer,
    MeetingQuestion,
)

from backend.app.services.meeting_question_answerer import (
    answer_meeting_question,
)

from backend.app.schemas.processing_job import ProcessingJobRecord
from backend.app.services.processing_job_repository import (
    create_processing_job,
    get_processing_job,
    update_processing_job,
)

from backend.app.services.meeting_processor import (
    process_meeting_job,
    remove_processing_file,
    retry_meeting_analysis,
)

router = APIRouter(
    prefix="/meetings",
    tags=["Meetings"],
)

logger = logging.getLogger(__name__)


def remove_processing_file(path: Path | None) -> None:
    if path is None:
        return

    try:
        path.unlink(missing_ok=True)
    except OSError:
        logger.warning(
            "Could not remove processing file %s",
            path,
            exc_info=True,
        )

@router.post(
    "/upload",
    response_model=MeetingRecord,
)
async def upload_meeting(
    response: Response,
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

    original_filename = str(upload_result["original_filename"])
    content_type = (
        str(upload_result["content_type"])
        if upload_result["content_type"] is not None
        else None
    )
    size_bytes = int(upload_result["size_bytes"])

    try:
        job = await create_processing_job(
            original_filename=original_filename,
            stored_filename=stored_filename,
            content_type=content_type,
            size_bytes=size_bytes,
        )
    except Exception:
        remove_processing_file(uploaded_path)
        raise

    result = await process_meeting_job(job.id)

    response.headers["X-Processing-Job-ID"] = str(job.id)

    return result

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
    "/jobs/{job_id}",
    response_model=ProcessingJobRecord,
)
async def get_meeting_processing_job(
    job_id: int,
) -> ProcessingJobRecord:
    job = await get_processing_job(job_id)

    return ProcessingJobRecord.model_validate(job)


@router.post(
    "/jobs/{job_id}/retry",
    response_model=MeetingRecord,
)
async def retry_meeting_processing_job(
    job_id: int,
    response: Response,
) -> MeetingRecord:
    meeting = await retry_meeting_analysis(job_id)
    response.headers["X-Processing-Job-ID"] = str(job_id)
    return meeting


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
            detail=(
                "Playback audio is not available "
                "for this meeting."
            ),
        )

    return FileResponse(
        path=playback_path,
        media_type="audio/mpeg",
    )

@router.post(
    "/{meeting_id}/ask",
    response_model=MeetingAnswer,
)
async def ask_meeting_question(
    meeting_id: int,
    request: MeetingQuestion,
) -> MeetingAnswer:
    meeting = await get_saved_meeting(meeting_id)

    return await answer_meeting_question(
        meeting_id=meeting.id,
        question=request.question,
        history=request.history,
        segments=meeting.segments,
    )


@router.patch(
    "/{meeting_id}/speakers",
    response_model=MeetingRecord,
)
async def rename_meeting_speaker(
    meeting_id: int,
    request: SpeakerRename,
) -> MeetingRecord:
    meeting = await rename_saved_speaker(
        meeting_id,
        request.current_name,
        request.new_name,
    )

    return MeetingRecord.model_validate(meeting)

@router.get(
    "/{meeting_id}",
    response_model=MeetingRecord,
)
async def get_meeting(
    meeting_id: int,
) -> MeetingRecord:
    meeting = await get_saved_meeting(meeting_id)

    return MeetingRecord.model_validate(meeting)
