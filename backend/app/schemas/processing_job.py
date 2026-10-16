from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class ProcessingJobRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: str

    status: Literal[
        "queued",
        "processing",
        "failed",
        "interrupted",
        "completed",
    ]

    stage: str
    error_message: str | None
    retry_count: int
    meeting_id: int | None
    created_at: datetime
    updated_at: datetime