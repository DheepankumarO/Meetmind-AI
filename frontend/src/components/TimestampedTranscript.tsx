import {
  useEffect,
  useRef,
  useState,
  type FormEvent,
} from "react";

import {
  getMeetingAudioUrl,
  renameSpeaker,
} from "../services/api";
import type {
  MeetingRecord,
  TranscriptSegment,
} from "../types/meeting";

type PlaybackRequest = {
  seconds: number;
  requestId: number;
};

type TimestampedTranscriptProps = {
  meetingId: number;
  segments: TranscriptSegment[];
  fallbackTranscript: string;
  seekRequest: PlaybackRequest | null;
  onMeetingUpdated: (meeting: MeetingRecord) => void;
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

  const paddedMinutes = String(minutes).padStart(
    2,
    "0",
  );
  const paddedSeconds = String(
    remainingSeconds,
  ).padStart(2, "0");

  if (hours > 0) {
    return `${hours}:${paddedMinutes}:${paddedSeconds}`;
  }

  return `${paddedMinutes}:${paddedSeconds}`;
}


function TimestampedTranscript({
  meetingId,
  segments,
  fallbackTranscript,
  seekRequest,
  onMeetingUpdated,
}: TimestampedTranscriptProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const detailsRef = useRef<HTMLDetailsElement>(null);
  const [
    activeSegmentIndex,
    setActiveSegmentIndex,
  ] = useState<number | null>(null);

  const [
    audioUnavailable,
    setAudioUnavailable,
  ] = useState(false);
  const [speakerNames, setSpeakerNames] = useState<
    Record<string, string>
  >({});
  const [speakerError, setSpeakerError] = useState<
    string | null
  >(null);
  const [savingSpeaker, setSavingSpeaker] = useState<
    string | null
  >(null);

  const speakers = Array.from(
    new Set(segments.map((segment) => segment.speaker)),
  );


  async function handleSpeakerRename(
    event: FormEvent<HTMLFormElement>,
    currentName: string,
  ) {
    event.preventDefault();

    const newName = speakerNames[currentName]?.trim();

    if (!newName || newName === currentName) {
      return;
    }

    setSavingSpeaker(currentName);
    setSpeakerError(null);

    try {
      const updatedMeeting = await renameSpeaker(
        meetingId,
        currentName,
        newName,
      );

      setSpeakerNames({});
      onMeetingUpdated(updatedMeeting);
    } catch (requestError) {
      setSpeakerError(
        requestError instanceof Error
          ? requestError.message
          : "The speaker name could not be saved.",
      );
    } finally {
      setSavingSpeaker(null);
    }
  }


  async function playSegment(
    segment: TranscriptSegment,
  ) {
    const audio = audioRef.current;

    if (!audio || audioUnavailable) {
      return;
    }

    audio.currentTime = segment.start_seconds;
    setActiveSegmentIndex(segment.segment_index);

    try {
      await audio.play();
    } catch {
      setAudioUnavailable(true);
    }
  }


  function handleTimeUpdate() {
    const audio = audioRef.current;

    if (!audio) {
      return;
    }

    const activeSegment = segments.find(
      (segment) =>
        audio.currentTime >= segment.start_seconds &&
        audio.currentTime < segment.end_seconds,
    );

    setActiveSegmentIndex(
      activeSegment?.segment_index ?? null,
    );
  }
  useEffect(() => {
  const audio = audioRef.current;

  if (!audio || !seekRequest || audioUnavailable) {
    return;
  }

  if (detailsRef.current) {
    detailsRef.current.open = true;
  }

  audio.currentTime = seekRequest.seconds;

  const selectedSegment = segments.find(
    (segment) =>
      seekRequest.seconds >= segment.start_seconds &&
      seekRequest.seconds < segment.end_seconds,
  );

  setActiveSegmentIndex(
    selectedSegment?.segment_index ?? null,
  );

  void audio.play().catch(() => {
    setAudioUnavailable(true);
  });
  }, [
    seekRequest,
    segments,
    audioUnavailable,
  ]);

  return (
    <details
      ref={detailsRef}
      className="result-card transcript"
    >
      <summary>View timestamped transcript</summary>

      {!audioUnavailable ? (
        <audio
          ref={audioRef}
          aria-label="Meeting audio"
          className="meeting-audio"
          controls
          preload="metadata"
          src={getMeetingAudioUrl(meetingId)}
          onTimeUpdate={handleTimeUpdate}
          onEnded={() => setActiveSegmentIndex(null)}
          onError={() => setAudioUnavailable(true)}
        >
          Your browser does not support audio playback.
        </audio>
      ) : (
        <p className="audio-unavailable">
          Playback audio is unavailable for this meeting.
        </p>
      )}

      {speakers.length > 0 && (
        <div className="speaker-editor">
          <h4>Rename speakers</h4>

          {speakers.map((speaker) => (
            <form
              className="speaker-rename-form"
              key={speaker}
              onSubmit={(event) => {
                void handleSpeakerRename(event, speaker);
              }}
            >
              <strong>{speaker}</strong>

              <input
                aria-label={`Rename ${speaker}`}
                maxLength={50}
                placeholder="Enter speaker name"
                value={speakerNames[speaker] ?? ""}
                onChange={(event) => {
                  setSpeakerNames((currentNames) => ({
                    ...currentNames,
                    [speaker]: event.target.value,
                  }));
                }}
              />

              <button
                type="submit"
                disabled={
                  savingSpeaker !== null ||
                  !speakerNames[speaker]?.trim()
                }
              >
                {savingSpeaker === speaker ? "Saving…" : "Save"}
              </button>
            </form>
          ))}

          {speakerError && (
            <p className="speaker-error">{speakerError}</p>
          )}
        </div>
      )}

      {segments.length > 0 ? (
        <div className="transcript-segments">
          {segments.map((segment) => {
            const isActive =
              segment.segment_index === activeSegmentIndex;

            return (
              <button
                className={`transcript-segment ${
                  isActive ? "active" : ""
                }`}
                key={segment.segment_index}
                type="button"
                disabled={audioUnavailable}
                onClick={() => {
                  void playSegment(segment);
                }}
              >
                <span className="segment-meta">
                  <strong className="segment-speaker">
                    {segment.speaker}
                  </strong>
                  <span className="segment-time">
                    {formatTimestamp(
                      segment.start_seconds,
                    )}
                    {" – "}
                    {formatTimestamp(
                      segment.end_seconds,
                    )}
                  </span>
                </span>

                <p>{segment.text}</p>
              </button>
            );
          })}
        </div>
      ) : (
        <p>{fallbackTranscript}</p>
      )}
    </details>
  );
}


export default TimestampedTranscript;
