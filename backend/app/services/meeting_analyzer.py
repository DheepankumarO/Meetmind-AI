import asyncio

from fastapi import HTTPException
from ollama import Client
from pydantic import ValidationError

from backend.app.schemas.meeting_analysis import MeetingAnalysis


OLLAMA_HOST = "http://localhost:11434"
MODEL_NAME = "qwen3:1.7b"

SYSTEM_PROMPT = """
You are a precise meeting-analysis assistant.

Analyze the supplied transcript and return structured meeting information.

Rules:
- Use only information explicitly present in the transcript.
- Never invent names, decisions, tasks, owners, or deadlines.
- Write a concise factual summary in one to three sentences.
- When meaningful speech exists, extract one to five key topics.
- Write key topics as short phrases, not full sentences.
- Include a decision only when the speaker explicitly selects,
  approves, rejects, or agrees on something.
- Include an action item only when work must be completed.
- If no decisions exist, return an empty decisions list.
- If no action items exist, return an empty action_items list.
- If an action item's owner is not stated, use null.
- If an action item's deadline is not stated, use null.
"""


def analyze_transcript_sync(
    transcript: str,
) -> MeetingAnalysis:
    if not transcript.strip():
        return MeetingAnalysis(
            summary="No spoken content was detected.",
        )

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
                        "Analyze this meeting transcript:\n\n"
                        f"{transcript}"
                    ),
                },
            ],
            format=MeetingAnalysis.model_json_schema(),
            options={
                "temperature": 0,
            },
            stream=False,
            think=False,
            keep_alive=0,
        )

        return MeetingAnalysis.model_validate_json(
            response.message.content,
        )

    except ValidationError as error:
        raise HTTPException(
            status_code=502,
            detail="The local model returned an invalid analysis.",
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail=(
                "The local meeting-analysis service is unavailable. "
                "Make sure Ollama is running."
            ),
        ) from error


async def analyze_transcript(
    transcript: str,
) -> MeetingAnalysis:
    return await asyncio.to_thread(
        analyze_transcript_sync,
        transcript,
    )