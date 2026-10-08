from types import SimpleNamespace

from backend.app.schemas.meeting_question import MeetingChatTurn
from backend.app.services.meeting_retriever import (
    TranscriptChunk,
    build_retrieval_query,
    build_transcript_chunks,
    rank_chunks,
)


def make_segment(
    index: int,
    text: str,
) -> SimpleNamespace:
    return SimpleNamespace(
        segment_index=index,
        start_seconds=float(index * 5),
        end_seconds=float((index + 1) * 5),
        text=text,
    )


def test_chunking_preserves_indexes_and_overlap() -> None:
    segments = [
        make_segment(index, f"Segment {index}")
        for index in range(6)
    ]

    chunks = build_transcript_chunks(segments)

    assert chunks[0].segment_indexes == [0, 1, 2, 3]
    assert chunks[1].segment_indexes == [3, 4, 5]
    assert chunks[1].start_seconds == 15.0
    assert chunks[1].end_seconds == 30.0


def test_semantic_ranking_finds_a_paraphrased_answer() -> None:
    release_chunk = TranscriptChunk(
        chunk_index=0,
        start_seconds=0,
        end_seconds=10,
        segment_indexes=[0, 1],
        text="The team agreed to ship the product on Friday.",
        embedding=[1.0, 0.0],
    )
    budget_chunk = TranscriptChunk(
        chunk_index=1,
        start_seconds=10,
        end_seconds=20,
        segment_indexes=[2, 3],
        text="The budget review will happen next month.",
        embedding=[0.0, 1.0],
    )

    ranked = rank_chunks(
        question="When is the release?",
        question_embedding=[0.98, 0.02],
        chunks=[budget_chunk, release_chunk],
    )

    assert ranked[0] == release_chunk


def test_follow_up_query_includes_recent_context() -> None:
    query = build_retrieval_query(
        "Who owns that task?",
        [
            MeetingChatTurn(
                question="What action item was assigned?",
                answer="The testing task was assigned.",
            )
        ],
    )

    assert "testing task" in query
    assert "Who owns that task?" in query
