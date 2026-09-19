import asyncio

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from backend.app.database import SessionLocal
from backend.app.models.meeting import Meeting
from backend.app.schemas.meeting_analysis import MeetingAnalysis


def save_meeting_sync(
    *,
    original_filename: str,
    content_type: str | None,
    size_bytes: int,
    transcript: str,
    language: str,
    language_probability: float,
    duration_seconds: float,
    analysis: MeetingAnalysis,
) -> Meeting:
    with SessionLocal() as session:
        try:
            meeting = Meeting(
                original_filename=original_filename,
                content_type=content_type,
                size_bytes=size_bytes,
                transcript=transcript,
                language=language,
                language_probability=language_probability,
                duration_seconds=duration_seconds,
                summary=analysis.summary,
                key_topics=analysis.key_topics,
                decisions=analysis.decisions,
                action_items=[
                    action_item.model_dump()
                    for action_item in analysis.action_items
                ],
            )

            session.add(meeting)
            session.commit()
            session.refresh(meeting)

            return meeting

        except SQLAlchemyError as error:
            session.rollback()

            raise HTTPException(
                status_code=500,
                detail="The meeting could not be saved.",
            ) from error


async def save_meeting(
    *,
    original_filename: str,
    content_type: str | None,
    size_bytes: int,
    transcript: str,
    language: str,
    language_probability: float,
    duration_seconds: float,
    analysis: MeetingAnalysis,
) -> Meeting:
    return await asyncio.to_thread(
        save_meeting_sync,
        original_filename=original_filename,
        content_type=content_type,
        size_bytes=size_bytes,
        transcript=transcript,
        language=language,
        language_probability=language_probability,
        duration_seconds=duration_seconds,
        analysis=analysis,
    )


def list_meetings_sync() -> list[Meeting]:
    with SessionLocal() as session:
        try:
            statement = select(Meeting).order_by(
                Meeting.created_at.desc(),
            )

            return list(
                session.scalars(statement).all(),
            )

        except SQLAlchemyError as error:
            raise HTTPException(
                status_code=500,
                detail="Meeting history could not be loaded.",
            ) from error


async def list_saved_meetings() -> list[Meeting]:
    return await asyncio.to_thread(
        list_meetings_sync,
    )


def get_meeting_sync(meeting_id: int) -> Meeting:
    with SessionLocal() as session:
        try:
            meeting = session.get(Meeting, meeting_id)

        except SQLAlchemyError as error:
            raise HTTPException(
                status_code=500,
                detail="The meeting could not be loaded.",
            ) from error

        if meeting is None:
            raise HTTPException(
                status_code=404,
                detail="Meeting not found.",
            )

        return meeting


async def get_saved_meeting(
    meeting_id: int,
) -> Meeting:
    return await asyncio.to_thread(
        get_meeting_sync,
        meeting_id,
    )