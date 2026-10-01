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
  language: string;
  language_probability: number;
  duration_seconds: number;
  summary: string;
  key_topics: string[];
  decisions: string[];
  action_items: ActionItem[];
  created_at: string;
};