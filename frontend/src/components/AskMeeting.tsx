import {
  useState,
  type FormEvent,
} from "react";

import { askMeeting } from "../services/api";
import type {
  MeetingAnswer,
  MeetingChatTurn,
} from "../types/meeting";


type AskMeetingProps = {
  meetingId: number;
  onSourceSelect: (seconds: number) => void;
};

const SUGGESTED_QUESTIONS = [
  "What decisions were made?",
  "What are the action items?",
  "Were any deadlines mentioned?",
];


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
  const [messages, setMessages] =
    useState<MeetingAnswer[]>([]);
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
    setError(null);

    try {
      const history: MeetingChatTurn[] = messages.slice(-6).map(
        (message) => ({
          question: message.question,
          answer: message.answer,
        }),
      );

      const result = await askMeeting(
        meetingId,
        trimmedQuestion,
        history,
      );

      setMessages((current) => [...current, result]);
      setQuestion("");
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
        Ask follow-up questions about this meeting. Semantic
        search finds relevant transcript passages by meaning.
      </p>

      <div className="suggested-questions">
        {SUGGESTED_QUESTIONS.map((suggestion) => (
          <button
            type="button"
            key={suggestion}
            disabled={isAsking}
            onClick={() => {
              setQuestion(suggestion);
              setError(null);
            }}
          >
            {suggestion}
          </button>
        ))}
      </div>

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

      {messages.length > 0 && (
        <div className="ask-conversation">
          {messages.map((answer, messageIndex) => (
            <div
              className="ask-exchange"
              key={`${answer.question}-${messageIndex}`}
            >
              <div className="user-question">
                <strong>You</strong>
                <p>{answer.question}</p>
              </div>

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
                            formatTimestamp(
                              source.start_seconds,
                            )
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
            </div>
          ))}

          <button
            type="button"
            className="clear-chat-button"
            onClick={() => setMessages([])}
          >
            Clear conversation
          </button>
        </div>
      )}
    </article>
  );
}


export default AskMeeting;
