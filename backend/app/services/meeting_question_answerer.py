import asyncio
import re
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
)
from backend.app.services.meeting_analyzer import (
    MODEL_NAME,
    OLLAMA_HOST,
)

MAX_CONTEXT_SEGMENTS = 10

STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "at",
    "be",
    "did",
    "do",
    "does",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "this",
    "to",
    "was",
    "were",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "with",
}

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


def tokenize(text: str) -> set[str]:
    words = re.findall(
        r"[a-z0-9']+",
        text.lower(),
    )

    return {
        word
        for word in words
        if word not in STOP_WORDS and len(word) > 1
    }


def select_relevant_segments(
    question: str,
    segments: Sequence[MeetingTranscriptSegment],
) -> list[MeetingTranscriptSegment]:
    question_tokens = tokenize(question)

    scored_segments: list[
        tuple[int, MeetingTranscriptSegment]
    ] = []

    for segment in segments:
        segment_tokens = tokenize(segment.text)

        overlap_score = len(
            question_tokens.intersection(segment_tokens),
        )

        scored_segments.append(
            (overlap_score, segment),
        )

    matching_segments = [
        item
        for item in scored_segments
        if item[0] > 0
    ]

    if matching_segments:
        matching_segments.sort(
            key=lambda item: (
                -item[0],
                item[1].segment_index,
            ),
        )

        selected = [
            segment
            for _, segment in matching_segments[
                :MAX_CONTEXT_SEGMENTS
            ]
        ]
    else:
        selected = list(
            segments[:MAX_CONTEXT_SEGMENTS],
        )

    return sorted(
        selected,
        key=lambda segment: segment.segment_index,
    )


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
    segments: Sequence[MeetingTranscriptSegment],
) -> MeetingAnswer:
    selected_segments = select_relevant_segments(
        question,
        segments,
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

    try:
        response = client.chat(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": (
                        f"Meeting context:\n\n{context}\n\n"
                        f"Question:\n{question}"
                    ),
                },
            ],
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

    if not generated_answer.answer_found:
        sources = []

    return MeetingAnswer(
        meeting_id=meeting_id,
        question=question,
        answer=generated_answer.answer,
        answer_found=generated_answer.answer_found,
        sources=sources,
    )


async def answer_meeting_question(
    *,
    meeting_id: int,
    question: str,
    segments: Sequence[MeetingTranscriptSegment],
) -> MeetingAnswer:
    return await asyncio.to_thread(
        answer_meeting_question_sync,
        meeting_id=meeting_id,
        question=question,
        segments=segments,
    )