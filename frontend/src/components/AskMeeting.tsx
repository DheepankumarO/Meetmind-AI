import {
  useState,
  type FormEvent,
} from "react";

import { askMeeting } from "../services/api";
import type { MeetingAnswer } from "../types/meeting";


type AskMeetingProps = {
  meetingId: number;
  onSourceSelect: (seconds: number) => void;
};


function formatTimestamp(seconds: number): string {
  const totalSeconds = Math.max(
    0,
    Math.floor(seconds),
  );

  const minutes = Math.floor(totalSeconds / 60);
  const remainingSeconds = totalSeconds % 60;

  return [
    String(minutes).padStart(2, "0"),
    String(remainingSeconds).padStart(2, "0"),
  ].join(":");
}


function AskMeeting({
  meetingId,
  onSourceSelect,
}: AskMeetingProps) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] =
    useState<MeetingAnswer | null>(null);
  const [isAsking, setIsAsking] = useState(false);
  const [error, setError] = useState<string | null>(
    null,
  );


  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    const trimmedQuestion = question.trim();

    if (trimmedQuestion.length < 2) {
      setError(
        "Enter a question containing at least two characters.",
      );
      return;
    }

    setIsAsking(true);
    setAnswer(null);
    setError(null);

    try {
      const result = await askMeeting(
        meetingId,
        trimmedQuestion,
      );

      setAnswer(result);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Ask MeetMind could not answer the question.",
      );
    } finally {
      setIsAsking(false);
    }
  }


  return (
    <article className="result-card ask-meeting">
      <div className="ask-heading">
        <div>
          <p className="ask-label">LOCAL AI Q&A</p>
          <h3>Ask MeetMind</h3>
        </div>

        <span>Grounded in this meeting</span>
      </div>

      <p className="ask-description">
        Ask a question about the selected meeting. Answers
        use only its transcript.
      </p>

      <form
        className="ask-form"
        onSubmit={handleSubmit}
      >
        <label htmlFor={`meeting-question-${meetingId}`}>
          Question
        </label>

        <div className="ask-input-row">
          <input
            id={`meeting-question-${meetingId}`}
            type="text"
            value={question}
            maxLength={500}
            placeholder="What decisions were made?"
            disabled={isAsking}
            onChange={(event) => {
              setQuestion(event.target.value);
              setError(null);
            }}
          />

          <button
            type="submit"
            disabled={
              isAsking || question.trim().length < 2
            }
          >
            {isAsking ? "Thinking…" : "Ask"}
          </button>
        </div>
      </form>

      {isAsking && (
        <p className="ask-status">
          Searching the transcript and generating a grounded
          answer locally…
        </p>
      )}

      {error && (
        <p className="ask-error">{error}</p>
      )}

      {answer && (
        <div
          className={`meeting-answer ${
            answer.answer_found
              ? "answer-found"
              : "answer-missing"
          }`}
        >
          <span className="answer-status">
            {answer.answer_found
              ? "Answer found"
              : "Not found in meeting"}
          </span>

          <p>{answer.answer}</p>

          {answer.sources.length > 0 && (
            <div className="answer-sources">
              <strong>Sources</strong>

              {answer.sources.map((source) => (
                <button
                    type="button"
                    key={source.segment_index}
                    aria-label={
                        `Play source at ${
                        formatTimestamp(source.start_seconds)
                        }: ${source.text}`
                    }
                    onClick={() => {
                        onSourceSelect(
                        source.start_seconds,
                        );
                    }}
                >
                  <span>
                    {formatTimestamp(
                      source.start_seconds,
                    )}
                  </span>

                  {source.text}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </article>
  );
}


export default AskMeeting;