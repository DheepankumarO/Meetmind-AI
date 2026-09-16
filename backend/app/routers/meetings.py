from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.app.services.audio_extractor import extract_audio
from backend.app.services.file_storage import (
    UPLOAD_DIRECTORY,
    save_upload,
)


router = APIRouter(
    prefix="/meetings",
    tags=["Meetings"],
)


@router.post("/upload")
async def upload_meeting(
    file: UploadFile = File(...),
) -> dict[str, str | int | None]:
    upload_result = await save_upload(file)

    stored_filename = upload_result["stored_filename"]

    if not isinstance(stored_filename, str):
        raise HTTPException(
            status_code=500,
            detail="The stored filename is invalid.",
        )

    uploaded_path = UPLOAD_DIRECTORY / stored_filename
    audio_path = await extract_audio(uploaded_path)

    upload_result["audio_filename"] = audio_path.name

    return upload_result