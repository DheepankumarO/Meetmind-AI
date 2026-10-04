export type ActionItem = {
  task: string;
  owner: string | null;
  deadline: string | null;
};

export type MeetingRecord = {
  status: "processed";
  id: number;
  original_filename: string;
  content_type: string | null;
  size_bytes: number;
  transcript: string;
  segments: TranscriptSegment[];
  language: string;
  language_probability: number;
  duration_seconds: number;
  summary: string;
  key_topics: string[];
  decisions: string[];
  action_items: ActionItem[];
  created_at: string;
};

export type TranscriptSegment = {
  segment_index: number;
  start_seconds: number;
  end_seconds: number;
  text: string;
};