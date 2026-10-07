from pydantic import BaseModel, Field


class MeetingChatTurn(BaseModel):
    question: str = Field(min_length=2, max_length=500)
    answer: str = Field(min_length=1, max_length=4000)


class MeetingQuestion(BaseModel):
    question: str = Field(
        min_length=2,
        max_length=500,
        description="A question about the selected meeting.",
    )
    history: list[MeetingChatTurn] = Field(
        default_factory=list,
        max_length=6,
        description="Recent questions and answers for follow-up context.",
    )


class GeneratedMeetingAnswer(BaseModel):
    answer: str = Field(
        description="The answer based only on the supplied context.",
    )
    answer_found: bool = Field(
        description=(
            "Whether the supplied meeting context contains "
            "enough information to answer the question."
        ),
    )
    cited_segment_indexes: list[int] = Field(
        default_factory=list,
        description=(
            "Transcript segment indexes supporting the answer."
        ),
    )


class AnswerSource(BaseModel):
    segment_index: int
    start_seconds: float
    end_seconds: float
    text: str


class MeetingAnswer(BaseModel):
    meeting_id: int
    question: str
    answer: str
    answer_found: bool
    sources: list[AnswerSource] = Field(
        default_factory=list,
    )
