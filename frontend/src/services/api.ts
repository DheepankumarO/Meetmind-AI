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

type ProcessingJob = {
  status: string;
  stage: string;
};

export class ApiError extends Error {
  readonly status: number;
  readonly jobId: number | null;

  constructor(
    message: string,
    status: number,
    jobId: number | null,
  ) {
    super(message);
    this.status = status;
    this.jobId = jobId;
  }
}

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

    const jobId = Number(response.headers.get("X-Processing-Job-ID"));
    throw new ApiError(
      message,
      response.status,
      Number.isSafeInteger(jobId) && jobId > 0 ? jobId : null,
    );
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

export function getProcessingJob(jobId: number): Promise<ProcessingJob> {
  return request<ProcessingJob>(`/meetings/jobs/${jobId}`);
}

export function retryMeetingAnalysis(jobId: number): Promise<MeetingRecord> {
  return request<MeetingRecord>(`/meetings/jobs/${jobId}/retry`, {
    method: "POST",
  });
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


export function renameSpeaker(
  meetingId: number,
  currentName: string,
  newName: string,
): Promise<MeetingRecord> {
  return request<MeetingRecord>(
    `/meetings/${meetingId}/speakers`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        current_name: currentName,
        new_name: newName,
      }),
    },
  );
}
