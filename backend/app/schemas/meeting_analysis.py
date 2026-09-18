from pydantic import BaseModel, Field


class ActionItem(BaseModel):
    task: str = Field(
        description="The specific work that must be completed.",
    )
    owner: str | None = Field(
        default=None,
        description="The person responsible, if explicitly mentioned.",
    )
    deadline: str | None = Field(
        default=None,
        description="The deadline, if explicitly mentioned.",
    )


class MeetingAnalysis(BaseModel):
    summary: str = Field(
        description="A concise summary of the meeting.",
    )
    key_topics: list[str] = Field(
        default_factory=list,
        description="The main subjects discussed.",
    )
    decisions: list[str] = Field(
        default_factory=list,
        description="Decisions explicitly made during the meeting.",
    )
    action_items: list[ActionItem] = Field(
        default_factory=list,
        description="Tasks assigned during the meeting.",
    )