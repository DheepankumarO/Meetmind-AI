import json
from dataclasses import replace
from pathlib import Path

from backend.app.schemas.transcription import TranscriptSegment
from backend.app.services.meeting_retriever import (
    build_transcript_chunks,
    create_embeddings,
    rank_chunks,
)


CASES_PATH = Path(__file__).with_name("retrieval_cases.json")


def main() -> None:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    segments = [
        TranscriptSegment.model_validate(segment)
        for segment in cases["segments"]
    ]
    chunks = build_transcript_chunks(segments)
    chunk_embeddings = create_embeddings(
        [chunk.text for chunk in chunks],
    )
    indexed_chunks = [
        replace(chunk, embedding=embedding)
        for chunk, embedding in zip(chunks, chunk_embeddings)
    ]
    questions = cases["questions"]
    question_embeddings = create_embeddings(
        [case["question"] for case in questions],
    )

    hits = 0
    for case, embedding in zip(questions, question_embeddings):
        ranked = rank_chunks(
            question=case["question"],
            question_embedding=embedding,
            chunks=indexed_chunks,
            top_k=1,
        )
        retrieved = {
            index
            for chunk in ranked
            for index in chunk.segment_indexes
        }
        expected = set(case["expected_segment_indexes"])
        found = bool(expected.intersection(retrieved))
        hits += int(found)
        print(
            f"{'PASS' if found else 'FAIL'}: "
            f"{case['question']} -> {sorted(retrieved)}"
        )

    print(f"Recall@1: {hits}/{len(questions)}")


if __name__ == "__main__":
    main()
