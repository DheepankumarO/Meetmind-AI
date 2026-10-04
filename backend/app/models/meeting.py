from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    content_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    size_bytes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    transcript: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    segments: Mapped[
        list["MeetingTranscriptSegment"]
    ] = relationship(
        back_populates="meeting",
        cascade="all, delete-orphan",
        order_by=lambda: (
            MeetingTranscriptSegment.segment_index
        ),
        lazy="selectin",
    )

    language: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    language_probability: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    duration_seconds: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    key_topics: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    decisions: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    action_items: Mapped[list[dict[str, str | None]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    
    
class MeetingTranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    __table_args__ = (
        UniqueConstraint(
            "meeting_id",
            "segment_index",
            name="uq_meeting_segment_index",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    meeting_id: Mapped[int] = mapped_column(
        ForeignKey(
            "meetings.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    segment_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    start_seconds: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    end_seconds: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    meeting: Mapped["Meeting"] = relationship(
        back_populates="segments",
    )