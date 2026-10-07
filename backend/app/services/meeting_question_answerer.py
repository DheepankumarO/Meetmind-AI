import asyncio
from collections.abc import Sequence

from fastapi import HTTPException
from ollama import Client
from pydantic import ValidationError

from backend.app.models.meeting import (
    MeetingTranscriptSegment,
)
from backend.app.schemas.meeting_question import (
    AnswerSource,
    GeneratedMeetingAnswer,
    MeetingAnswer,
    MeetingChatTurn,
)
from backend.app.services.meeting_analyzer import (
    MODEL_NAME,
    OLLAMA_HOST,
)
from backend.app.services.meeting_retriever import (
    retrieve_relevant_segments,
)

SYSTEM_PROMPT = """
You are Ask MeetMind, a grounded meeting assistant.

Answer the user's question using only the supplied transcript
segments.

Rules:
- Never use outside knowledge.
- Never invent facts, names, decisions, deadlines, or tasks.
- If the context does not contain the answer, say:
  "I couldn't find that in this meeting."
- Set answer_found to false when the answer is not present.
- Set answer_found to true only when the context supports the answer.
- Cite only segment indexes included in the supplied context.
- Cite every segment that directly supports the answer.
- Keep the answer clear and concise.
"""


def build_context(
    segments: Sequence[MeetingTranscriptSegment],
) -> str:
    return "\n\n".join(
        (
            f"[Segment {segment.segment_index} | "
            f"{segment.start_seconds:.2f}-"
            f"{segment.end_seconds:.2f} seconds]\n"
            f"{segment.text}"
        )
        for segment in segments
    )


def answer_meeting_question_sync(
    *,
    meeting_id: int,
    question: str,
    history: Sequence[MeetingChatTurn],
    segments: Sequence[MeetingTranscriptSegment],
) -> MeetingAnswer:
    selected_segments = retrieve_relevant_segments(
        meeting_id=meeting_id,
        question=question,
        history=history,
        segments=segments,
    )

    if not selected_segments:
        return MeetingAnswer(
            meeting_id=meeting_id,
            question=question,
            answer="I couldn't find that in this meeting.",
            answer_found=False,
        )

    context = build_context(selected_segments)
    client = Client(host=OLLAMA_HOST)

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
    ]

    for turn in history[-3:]:
        messages.extend(
            [
                {
                    "role": "user",
                    "content": turn.question,
                },
                {
                    "role": "assistant",
                    "content": turn.answer,
                },
            ]
        )

    messages.append(
        {
            "role": "user",
            "content": (
                f"Meeting context:\n\n{context}\n\n"
                f"Current question:\n{question}"
            ),
        }
    )

    try:
        response = client.chat(
            model=MODEL_NAME,
            messages=messages,
            format=(
                GeneratedMeetingAnswer.model_json_schema()
            ),
            options={
                "temperature": 0,
            },
            stream=False,
            think=False,
            keep_alive=0,
        )

        generated_answer = (
            GeneratedMeetingAnswer.model_validate_json(
                response.message.content,
            )
        )

    except ValidationError as error:
        raise HTTPException(
            status_code=502,
            detail=(
                "The local model returned an invalid "
                "meeting answer."
            ),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail=(
                "Ask MeetMind is unavailable. "
                "Make sure Ollama is running."
            ),
        ) from error

    selected_by_index = {
        segment.segment_index: segment
        for segment in selected_segments
    }

    valid_citation_indexes = dict.fromkeys(
        index
        for index in generated_answer.cited_segment_indexes
        if index in selected_by_index
    )

    sources = [
        AnswerSource(
            segment_index=segment.segment_index,
            start_seconds=segment.start_seconds,
            end_seconds=segment.end_seconds,
            text=segment.text,
        )
        for index in valid_citation_indexes
        for segment in [selected_by_index[index]]
    ]

    answer_found = (
        generated_answer.answer_found and bool(sources)
    )

    if not answer_found:
        sources = []

    return MeetingAnswer(
        meeting_id=meeting_id,
        question=question,
        answer=(
            generated_answer.answer
            if answer_found
            else "I couldn't find that in this meeting."
        ),
        answer_found=answer_found,
        sources=sources,
    )


async def answer_meeting_question(
    *,
    meeting_id: int,
    question: str,
    history: Sequence[MeetingChatTurn],
    segments: Sequence[MeetingTranscriptSegment],
) -> MeetingAnswer:
    return await asyncio.to_thread(
        answer_meeting_question_sync,
        meeting_id=meeting_id,
        question=question,
        history=history,
        segments=segments,
    )
