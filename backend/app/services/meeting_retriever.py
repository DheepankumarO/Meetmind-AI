import math
import os
import re
from collections.abc import Sequence
from dataclasses import dataclass

from fastapi import HTTPException
from ollama import Client
from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError

from backend.app.database import SessionLocal
from backend.app.models.meeting import (
    MeetingTranscriptChunk,
    MeetingTranscriptSegment,
)
from backend.app.schemas.meeting_question import MeetingChatTurn
from backend.app.services.meeting_analyzer import OLLAMA_HOST


EMBEDDING_MODEL = os.getenv(
    "OLLAMA_EMBEDDING_MODEL",
    "embeddinggemma",
)
MAX_CHUNK_SEGMENTS = 4
MAX_CHUNK_CHARACTERS = 900
CHUNK_OVERLAP_SEGMENTS = 1
MAX_RETRIEVED_CHUNKS = 4
MAX_CONTEXT_SEGMENTS = 12
SEMANTIC_WEIGHT = 0.85
KEYWORD_WEIGHT = 0.15

STOP_WORDS = {
    "a", "an", "and", "are", "at", "be", "did", "do", "does",
    "for", "from", "how", "i", "in", "is", "it", "of", "on",
    "or", "the", "this", "to", "was", "were", "what", "when",
    "where", "which", "who", "why", "with",
}


@dataclass(frozen=True)
class TranscriptChunk:
    chunk_index: int
    start_seconds: float
    end_seconds: float
    segment_indexes: list[int]
    text: str
    embedding: list[float]


def tokenize(text: str) -> set[str]:
    return {
        word
        for word in re.findall(r"[a-z0-9']+", text.lower())
        if word not in STOP_WORDS and len(word) > 1
    }


def build_transcript_chunks(
    segments: Sequence[MeetingTranscriptSegment],
) -> list[TranscriptChunk]:
    chunks: list[TranscriptChunk] = []
    start = 0

    while start < len(segments):
        selected: list[MeetingTranscriptSegment] = []
        character_count = 0
        cursor = start

        while cursor < len(segments):
            segment = segments[cursor]
            next_count = character_count + len(segment.text)

            if selected and (
                len(selected) >= MAX_CHUNK_SEGMENTS
                or next_count > MAX_CHUNK_CHARACTERS
            ):
                break

            selected.append(segment)
            character_count = next_count
            cursor += 1

        chunks.append(
            TranscriptChunk(
                chunk_index=len(chunks),
                start_seconds=selected[0].start_seconds,
                end_seconds=selected[-1].end_seconds,
                segment_indexes=[
                    segment.segment_index for segment in selected
                ],
                text=" ".join(segment.text for segment in selected),
                embedding=[],
            )
        )

        if cursor >= len(segments):
            break

        start = max(
            start + 1,
            cursor - CHUNK_OVERLAP_SEGMENTS,
        )

    return chunks


def create_embeddings(texts: list[str]) -> list[list[float]]:
    try:
        response = Client(host=OLLAMA_HOST).embed(
            model=EMBEDDING_MODEL,
            input=texts,
            keep_alive=0,
        )

        return [
            [float(value) for value in embedding]
            for embedding in response.embeddings
        ]

    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail=(
                "Semantic search is unavailable. Make sure Ollama "
                f"is running and run: ollama pull {EMBEDDING_MODEL}"
            ),
        ) from error


def load_or_create_chunks(
    meeting_id: int,
    segments: Sequence[MeetingTranscriptSegment],
) -> list[TranscriptChunk]:
    blueprints = build_transcript_chunks(segments)

    if not blueprints:
        return []

    try:
        with SessionLocal() as session:
            statement = (
                select(MeetingTranscriptChunk)
                .where(
                    MeetingTranscriptChunk.meeting_id == meeting_id,
                    MeetingTranscriptChunk.embedding_model
                    == EMBEDDING_MODEL,
                )
                .order_by(MeetingTranscriptChunk.chunk_index)
            )
            stored = list(session.scalars(statement).all())

            stored_matches = (
                len(stored) == len(blueprints)
                and all(
                    saved.segment_indexes == planned.segment_indexes
                    and saved.text == planned.text
                    for saved, planned in zip(stored, blueprints)
                )
            )

            if not stored_matches:
                embeddings = create_embeddings(
                    [chunk.text for chunk in blueprints],
                )

                if len(embeddings) != len(blueprints):
                    raise HTTPException(
                        status_code=502,
                        detail="The embedding model returned invalid data.",
                    )

                session.execute(
                    delete(MeetingTranscriptChunk).where(
                        MeetingTranscriptChunk.meeting_id == meeting_id,
                        MeetingTranscriptChunk.embedding_model
                        == EMBEDDING_MODEL,
                    )
                )

                stored = []
                for blueprint, embedding in zip(
                    blueprints,
                    embeddings,
                ):
                    saved = MeetingTranscriptChunk(
                        meeting_id=meeting_id,
                        embedding_model=EMBEDDING_MODEL,
                        chunk_index=blueprint.chunk_index,
                        start_seconds=blueprint.start_seconds,
                        end_seconds=blueprint.end_seconds,
                        segment_indexes=blueprint.segment_indexes,
                        text=blueprint.text,
                        embedding=embedding,
                    )
                    session.add(saved)
                    stored.append(saved)

                session.commit()

            return [
                TranscriptChunk(
                    chunk_index=chunk.chunk_index,
                    start_seconds=chunk.start_seconds,
                    end_seconds=chunk.end_seconds,
                    segment_indexes=list(chunk.segment_indexes),
                    text=chunk.text,
                    embedding=list(chunk.embedding),
                )
                for chunk in stored
            ]

    except HTTPException:
        raise
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=500,
            detail="Meeting search data could not be saved.",
        ) from error


def cosine_similarity(
    first: Sequence[float],
    second: Sequence[float],
) -> float:
    if len(first) != len(second) or not first:
        return 0.0

    dot_product = sum(a * b for a, b in zip(first, second))
    first_length = math.sqrt(sum(value * value for value in first))
    second_length = math.sqrt(sum(value * value for value in second))

    if first_length == 0 or second_length == 0:
        return 0.0

    return dot_product / (first_length * second_length)


def rank_chunks(
    *,
    question: str,
    question_embedding: Sequence[float],
    chunks: Sequence[TranscriptChunk],
    top_k: int = MAX_RETRIEVED_CHUNKS,
) -> list[TranscriptChunk]:
    question_tokens = tokenize(question)

    def score(chunk: TranscriptChunk) -> float:
        semantic_score = cosine_similarity(
            question_embedding,
            chunk.embedding,
        )
        shared_words = len(
            question_tokens.intersection(tokenize(chunk.text)),
        )
        keyword_score = shared_words / max(1, len(question_tokens))

        return (
            SEMANTIC_WEIGHT * semantic_score
            + KEYWORD_WEIGHT * keyword_score
        )

    return sorted(chunks, key=score, reverse=True)[:top_k]


def build_retrieval_query(
    question: str,
    history: Sequence[MeetingChatTurn],
) -> str:
    recent_history = history[-2:]

    if not recent_history:
        return question

    context = " ".join(
        f"Previous question: {turn.question} "
        f"Previous answer: {turn.answer}"
        for turn in recent_history
    )
    return f"{context} Current question: {question}"


def retrieve_relevant_segments(
    *,
    meeting_id: int,
    question: str,
    history: Sequence[MeetingChatTurn],
    segments: Sequence[MeetingTranscriptSegment],
) -> list[MeetingTranscriptSegment]:
    chunks = load_or_create_chunks(meeting_id, segments)

    if not chunks:
        return []

    retrieval_query = build_retrieval_query(question, history)
    question_embedding = create_embeddings([retrieval_query])[0]
    ranked_chunks = rank_chunks(
        question=retrieval_query,
        question_embedding=question_embedding,
        chunks=chunks,
    )

    selected_indexes = {
        segment_index
        for chunk in ranked_chunks
        for segment_index in chunk.segment_indexes
    }

    return [
        segment
        for segment in segments
        if segment.segment_index in selected_indexes
    ][:MAX_CONTEXT_SEGMENTS]
