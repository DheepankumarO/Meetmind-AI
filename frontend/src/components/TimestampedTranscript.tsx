import type { TranscriptSegment } from "../types/meeting";


type TimestampedTranscriptProps = {
  segments: TranscriptSegment[];
  fallbackTranscript: string;
};


function formatTimestamp(seconds: number): string {
  const totalSeconds = Math.max(
    0,
    Math.floor(seconds),
  );

  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor(
    (totalSeconds % 3600) / 60,
  );
  const remainingSeconds = totalSeconds % 60;

  const paddedMinutes = String(minutes).padStart(2, "0");
  const paddedSeconds = String(
    remainingSeconds,
  ).padStart(2, "0");

  if (hours > 0) {
    return `${hours}:${paddedMinutes}:${paddedSeconds}`;
  }

  return `${paddedMinutes}:${paddedSeconds}`;
}


function TimestampedTranscript({
  segments,
  fallbackTranscript,
}: TimestampedTranscriptProps) {
  return (
    <details className="result-card transcript">
      <summary>View timestamped transcript</summary>

      {segments.length > 0 ? (
        <div className="transcript-segments">
          {segments.map((segment) => (
            <div
              className="transcript-segment"
              key={segment.segment_index}
            >
              <span className="segment-time">
                {formatTimestamp(segment.start_seconds)}
                {" – "}
                {formatTimestamp(segment.end_seconds)}
              </span>

              <p>{segment.text}</p>
            </div>
          ))}
        </div>
      ) : (
        <p>{fallbackTranscript}</p>
      )}
    </details>
  );
}


export default TimestampedTranscript;