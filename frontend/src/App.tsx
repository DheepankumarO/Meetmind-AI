import {
  useEffect,
  useState,
  type DragEvent,
  type FormEvent,
} from "react";

import {
  getHealth,
  uploadMeeting,
} from "./services/api";
import type { MeetingRecord } from "./types/meeting";

import "./App.css";
import MeetingHistory from "./components/MeetingHistory";
import TimestampedTranscript from "./components/TimestampedTranscript";
import AskMeeting from "./components/AskMeeting";
type ConnectionStatus =
  | "checking"
  | "connected"
  | "disconnected";


const ALLOWED_EXTENSIONS = [
  ".mp3",
  ".wav",
  ".m4a",
  ".mp4",
  ".mov",
  ".webm",
];

const MAX_FILE_SIZE = 500 * 1024 * 1024;
type PlaybackRequest = {
  seconds: number;
  requestId: number;
};

function App() {
  const [connectionStatus, setConnectionStatus] =
    useState<ConnectionStatus>("checking");

  const [selectedFile, setSelectedFile] =
    useState<File | null>(null);

  const [meeting, setMeeting] =
    useState<MeetingRecord | null>(null);
  const [historyRefreshKey, setHistoryRefreshKey] =
    useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [playbackRequest, setPlaybackRequest] =
  useState<PlaybackRequest | null>(null);

  useEffect(() => {
    getHealth()
      .then(() => setConnectionStatus("connected"))
      .catch(() => setConnectionStatus("disconnected"));
  }, []);


  function selectFile(file: File) {
    const filename = file.name.toLowerCase();

    const isSupported = ALLOWED_EXTENSIONS.some(
      (extension) => filename.endsWith(extension),
    );

    if (!isSupported) {
      setSelectedFile(null);
      setError("Select a supported audio or video file.");
      return;
    }

    if (file.size > MAX_FILE_SIZE) {
      setSelectedFile(null);
      setError("The file must be smaller than 500 MB.");
      return;
    }

    setSelectedFile(file);
    setMeeting(null);
    setError(null);
  }


  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(false);

    const file = event.dataTransfer.files[0];

    if (file) {
      selectFile(file);
    }
  }


  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    if (!selectedFile) {
      setError("Choose a meeting recording first.");
      return;
    }

    setIsProcessing(true);
    setError(null);
    setMeeting(null);

    try {
      const result = await uploadMeeting(selectedFile);
      setMeeting(result);
      setPlaybackRequest(null);
        setHistoryRefreshKey((currentKey) => currentKey + 1);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "The meeting could not be processed.",
      );
    } finally {
      setIsProcessing(false);
    }
  }


  return (
    <main className="app">
      <header className="header">
        <div>
          <p className="eyebrow">
            LOCAL MEETING INTELLIGENCE
          </p>

          <h1>MeetMind AI</h1>

          <p className="description">
            Upload a recording and receive a transcript,
            summary, decisions, and actionable next steps.
          </p>
        </div>

        <div className={`status ${connectionStatus}`}>
          <span className="status-dot" />

          {connectionStatus === "checking" &&
            "Checking backend"}

          {connectionStatus === "connected" &&
            "Backend connected"}

          {connectionStatus === "disconnected" &&
            "Backend unavailable"}
        </div>
      </header>

      <section className="workspace">
        <form className="upload-card" onSubmit={handleSubmit}>
          <div
            className={`drop-zone ${
              isDragging ? "dragging" : ""
            }`}
            onDragEnter={(event) => {
              event.preventDefault();
              setIsDragging(true);
            }}
            onDragOver={(event) => event.preventDefault()}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
          >
            <div className="upload-icon">↑</div>

            <h2>Upload a meeting</h2>

            <p>
              Drag and drop an audio or video recording,
              or choose one from your computer.
            </p>

            <label className="file-button">
              Choose file

              <input
                type="file"
                accept=".mp3,.wav,.m4a,.mp4,.mov,.webm"
                onChange={(event) => {
                  const file = event.target.files?.[0];

                  if (file) {
                    selectFile(file);
                  }
                }}
              />
            </label>
          </div>

          {selectedFile && (
            <div className="selected-file">
              <div>
                <strong>{selectedFile.name}</strong>

                <span>
                  {(selectedFile.size / 1024 / 1024).toFixed(1)}
                  {" MB"}
                </span>
              </div>

              <button
                type="button"
                className="remove-button"
                onClick={() => setSelectedFile(null)}
                disabled={isProcessing}
              >
                Remove
              </button>
            </div>
          )}

          {error && <p className="error-message">{error}</p>}

          <button
            className="process-button"
            type="submit"
            disabled={
              !selectedFile ||
              isProcessing ||
              connectionStatus !== "connected"
            }
          >
            {isProcessing
              ? "Transcribing and analyzing…"
              : "Process meeting"}
          </button>

          {isProcessing && (
            <p className="processing-note">
              Local processing can take several minutes.
              Keep this page open.
            </p>
          )}
        </form>

        <section className="results">
          {!meeting && !isProcessing && (
            <div className="empty-results">
              <span>✦</span>
              <h2>Your meeting intelligence appears here</h2>
              <p>
                Results will include the transcript, summary,
                decisions, topics, and action items.
              </p>
            </div>
          )}

          {meeting && (
            <>
              <div className="result-heading">
                <div>
                  <p className="result-label">
                    MEETING #{meeting.id}
                  </p>

                  <h2>{meeting.original_filename}</h2>
                </div>

                <span>
                  {meeting.duration_seconds.toFixed(1)} seconds
                </span>
              </div>

              <article className="result-card">
                <h3>Summary</h3>
                <p>{meeting.summary}</p>
              </article>

              <article className="result-card">
                <h3>Key topics</h3>

                {meeting.key_topics.length > 0 ? (
                  <div className="topic-list">
                    {meeting.key_topics.map((topic) => (
                      <span key={topic}>{topic}</span>
                    ))}
                  </div>
                ) : (
                  <p>No key topics were identified.</p>
                )}
              </article>

              <article className="result-card">
                <h3>Decisions</h3>

                {meeting.decisions.length > 0 ? (
                  <ul>
                    {meeting.decisions.map((decision) => (
                      <li key={decision}>{decision}</li>
                    ))}
                  </ul>
                ) : (
                  <p>No decisions were identified.</p>
                )}
              </article>

              <article className="result-card">
                <h3>Action items</h3>

                {meeting.action_items.length > 0 ? (
                  <div className="action-list">
                    {meeting.action_items.map(
                      (actionItem, index) => (
                        <div
                          className="action-item"
                          key={`${actionItem.task}-${index}`}
                        >
                          <strong>{actionItem.task}</strong>

                          <span>
                            Owner:{" "}
                            {actionItem.owner ?? "Unassigned"}
                          </span>

                          <span>
                            Deadline:{" "}
                            {actionItem.deadline ?? "Not specified"}
                          </span>
                        </div>
                      ),
                    )}
                  </div>
                ) : (
                  <p>No action items were identified.</p>
                )}
              </article>

              <AskMeeting
                key={`ask-${meeting.id}`}
                meetingId={meeting.id}
                onSourceSelect={(seconds) => {
                  setPlaybackRequest((currentRequest) => ({
                    seconds,
                    requestId:
                      (currentRequest?.requestId ?? 0) + 1,
                  }));
                }}
              />

              <TimestampedTranscript
                key={meeting.id}
                meetingId={meeting.id}
                segments={meeting.segments}
                fallbackTranscript={meeting.transcript}
                seekRequest={playbackRequest}
                onMeetingUpdated={(updatedMeeting) => {
                  setMeeting(updatedMeeting);
                  setHistoryRefreshKey(
                    (currentKey) => currentKey + 1,
                  );
                }}
              />
            </>
          )}
        </section>
      </section>
      <MeetingHistory
        refreshKey={historyRefreshKey}
        onSelect={(savedMeeting) => {
          setMeeting(savedMeeting);
          setPlaybackRequest(null);

          window.scrollTo({
            top: 0,
            behavior: "smooth",
          });
        }}
      />
    </main>
  );
}


export default App;
