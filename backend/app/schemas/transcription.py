from pydantic import BaseModel, ConfigDict, Field


class TranscriptSegment(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    segment_index: int = Field(ge=0)
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(ge=0)
    text: str
    speaker: str = "Speaker 1"


class TranscriptionResult(BaseModel):
    transcript: str
    segments: list[TranscriptSegment] = Field(
        default_factory=list,
    )
    language: str
    language_probability: float
    duration_seconds: float
