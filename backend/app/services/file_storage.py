from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile


UPLOAD_DIRECTORY = (
    Path(__file__).resolve().parents[2] / "storage" / "uploads"
)

ALLOWED_EXTENSIONS = {
    ".mp3",
    ".wav",
    ".m4a",
    ".mp4",
    ".mov",
    ".webm",
}

MAX_FILE_SIZE = 500 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024


async def save_upload(file: UploadFile) -> dict[str, str | int | None]:
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file must have a filename.",
        )

    extension = Path(file.filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {extension}",
        )

    UPLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)

    stored_filename = f"{uuid4()}{extension}"
    saved_path = UPLOAD_DIRECTORY / stored_filename
    total_size = 0

    try:
        with saved_path.open("wb") as output_file:
            while chunk := await file.read(CHUNK_SIZE):
                total_size += len(chunk)

                if total_size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail="The file exceeds the 500 MB limit.",
                    )

                output_file.write(chunk)

        if total_size == 0:
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is empty.",
            )

    except Exception:
        saved_path.unlink(missing_ok=True)
        raise

    finally:
        await file.close()

    return {
        "status": "uploaded",
        "original_filename": file.filename,
        "stored_filename": stored_filename,
        "content_type": file.content_type,
        "size_bytes": total_size,
    }