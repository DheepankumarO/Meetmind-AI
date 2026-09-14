from fastapi import APIRouter, File, UploadFile

from backend.app.services.file_storage import save_upload


router = APIRouter(
    prefix="/meetings",
    tags=["Meetings"],
)


@router.post("/upload")
async def upload_meeting(
    file: UploadFile = File(...),
) -> dict[str, str | int | None]:
    return await save_upload(file)