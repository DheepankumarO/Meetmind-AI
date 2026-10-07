import type {
  MeetingAnswer,
  MeetingChatTurn,
  MeetingRecord,
} from "../types/meeting";


const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ??
  "http://127.0.0.1:8000";


type HealthResponse = {
  status: string;
};


async function request<T>(
  endpoint: string,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch(
    `${API_BASE_URL}${endpoint}`,
    options,
  );

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;

    try {
      const errorBody = await response.json();

      if (typeof errorBody.detail === "string") {
        message = errorBody.detail;
      }
    } catch {
      // The server did not provide a JSON error response.
    }

    throw new Error(message);
  }

  return response.json() as Promise<T>;
}


export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}


export function uploadMeeting(
  file: File,
): Promise<MeetingRecord> {
  const formData = new FormData();

  formData.append("file", file);

  return request<MeetingRecord>(
    "/meetings/upload",
    {
      method: "POST",
      body: formData,
    },
  );
}

export function getMeetings(): Promise<MeetingRecord[]> {
  return request<MeetingRecord[]>("/meetings");
}


export function getMeeting(
  meetingId: number,
): Promise<MeetingRecord> {
  return request<MeetingRecord>(
    `/meetings/${meetingId}`,
  );
}

export function getMeetingAudioUrl(
  meetingId: number,
): string {
  return `${API_BASE_URL}/meetings/${meetingId}/audio`;
}

export function askMeeting(
  meetingId: number,
  question: string,
  history: MeetingChatTurn[] = [],
): Promise<MeetingAnswer> {
  return request<MeetingAnswer>(
    `/meetings/${meetingId}/ask`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        question,
        history,
      }),
    },
  );
}
