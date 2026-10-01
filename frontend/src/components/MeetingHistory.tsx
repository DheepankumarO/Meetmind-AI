import { useEffect, useState } from "react";

import { getMeetings } from "../services/api";
import type { MeetingRecord } from "../types/meeting";


type MeetingHistoryProps = {
  refreshKey: number;
  onSelect: (meeting: MeetingRecord) => void;
};


function MeetingHistory({
  refreshKey,
  onSelect,
}: MeetingHistoryProps) {
  const [meetings, setMeetings] =
    useState<MeetingRecord[]>([]);

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);


    useEffect(() => {
    let cancelled = false;

    getMeetings()
        .then((savedMeetings) => {
        if (!cancelled) {
            setMeetings(savedMeetings);
            setError(null);
        }
        })
        .catch((requestError) => {
        if (!cancelled) {
            setError(
            requestError instanceof Error
                ? requestError.message
                : "Meeting history could not be loaded.",
            );
        }
        })
        .finally(() => {
        if (!cancelled) {
            setIsLoading(false);
        }
        });

    return () => {
        cancelled = true;
    };
    }, [refreshKey]);


  return (
    <section className="history-section">
      <div className="history-heading">
        <div>
          <p className="result-label">SAVED MEETINGS</p>
          <h2>Meeting history</h2>
        </div>

        <span>
          {meetings.length}{" "}
          {meetings.length === 1 ? "meeting" : "meetings"}
        </span>
      </div>

      {isLoading && (
        <p className="history-message">
          Loading meeting history…
        </p>
      )}

      {error && (
        <p className="error-message">{error}</p>
      )}

      {!isLoading && !error && meetings.length === 0 && (
        <p className="history-message">
          No meetings have been processed yet.
        </p>
      )}

      {!isLoading && meetings.length > 0 && (
        <div className="history-grid">
          {meetings.map((meeting) => (
            <button
              className="history-card"
              type="button"
              key={meeting.id}
              onClick={() => onSelect(meeting)}
            >
              <div className="history-card-top">
                <span>Meeting #{meeting.id}</span>

                <time dateTime={meeting.created_at}>
                  {new Date(
                    meeting.created_at,
                  ).toLocaleDateString()}
                </time>
              </div>

              <h3>{meeting.original_filename}</h3>

              <p>{meeting.summary}</p>

              <div className="history-meta">
                <span>
                  {meeting.duration_seconds.toFixed(1)} seconds
                </span>

                <span>
                  {meeting.action_items.length} action items
                </span>
              </div>
            </button>
          ))}
        </div>
      )}
    </section>
  );
}


export default MeetingHistory;