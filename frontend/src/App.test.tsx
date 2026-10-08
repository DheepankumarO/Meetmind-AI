import {
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import App from "./App";
import {
  askMeeting,
  getHealth,
  getMeetings,
  renameSpeaker,
  uploadMeeting,
} from "./services/api";
import type { MeetingRecord } from "./types/meeting";

vi.mock("./services/api", () => ({
  askMeeting: vi.fn(),
  getHealth: vi.fn(),
  getMeetings: vi.fn(),
  renameSpeaker: vi.fn(),
  uploadMeeting: vi.fn(),
  getMeetingAudioUrl: vi.fn(
    (meetingId: number) =>
      `http://127.0.0.1:8000/meetings/${meetingId}/audio`,
  ),
}));

const playMock = vi.fn().mockResolvedValue(undefined);

const testMeeting = {
  status: "processed",
  id: 1,
  original_filename: "team-meeting.wav",
  content_type: "audio/wav",
  size_bytes: 1000,
  transcript: "The team discussed the MeetMind project.",
  segments: [
    {
      segment_index: 0,
      start_seconds: 0,
      end_seconds: 6.36,
      text: "The team discussed the MeetMind project.",
      speaker: "Speaker 1",
    },
    {
      segment_index: 1,
      start_seconds: 6.36,
      end_seconds: 12.5,
      text: "The team agreed to add automated tests.",
      speaker: "Speaker 2",
    },
  ],
  summary: "The team reviewed project progress.",
  key_topics: ["MeetMind", "Testing"],
  decisions: ["Add automated tests"],
  action_items: [
    {
      task: "Finish frontend tests",
      owner: "Dheepan",
      deadline: "Friday",
    },
  ],
  language: "en",
  language_probability: 0.99,
  duration_seconds: 42.5,
  created_at: "2026-09-30T20:00:00",
} as MeetingRecord;

describe("MeetMind application", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    Object.defineProperty(
      HTMLMediaElement.prototype,
      "play",
      {
        configurable: true,
        value: playMock,
      },
    );

    vi.mocked(getHealth).mockResolvedValue({
      status: "healthy",
    });

    vi.mocked(getMeetings).mockResolvedValue([]);
});

it("shows that the backend is connected", async () => {
  render(<App />);

  expect(
    await screen.findByText("Backend connected"),
  ).toBeInTheDocument();

  expect(
    await screen.findByText(
      "No meetings have been processed yet.",
    ),
  ).toBeInTheDocument();
});

    it("rejects an unsupported file", async () => {
    const user = userEvent.setup({
        applyAccept: false,
    });

  render(<App />);

  const file = new File(
        ["not audio"],
        "meeting.txt",
        {
        type: "text/plain",
        },
    );

    await user.upload(
        screen.getByLabelText(/choose file/i),
        file,
    );

    expect(
        screen.getByText(
        "Select a supported audio or video file.",
        ),
    ).toBeInTheDocument();
    });

  it("uploads and displays a processed meeting", async () => {
    const user = userEvent.setup();

    vi.mocked(uploadMeeting).mockResolvedValue(
      testMeeting,
    );

    render(<App />);

    const file = new File(
      ["audio"],
      "team-meeting.wav",
      {
        type: "audio/wav",
      },
    );

    await user.upload(
      screen.getByLabelText(/choose file/i),
        file,
    );

    await user.click(
      await screen.findByRole("button", {
        name: "Process meeting",
      }),
    );

    expect(uploadMeeting).toHaveBeenCalledWith(file);

    expect(
      await screen.findByText(
        "The team reviewed project progress.",
      ),
    ).toBeInTheDocument();

    expect(
      screen.getByText("Finish frontend tests"),
    ).toBeInTheDocument();

    expect(
      screen.getByText("00:00 – 00:06"),
    ).toBeInTheDocument();

    expect(
      screen.getByText("Speaker 2"),
    ).toBeInTheDocument();
  });

  it("loads a saved meeting from history", async () => {
  const user = userEvent.setup();

  vi.mocked(getMeetings).mockResolvedValue([
    testMeeting,
  ]);

  render(<App />);

  const historyCard =
    await screen.findByRole("button", {
      name: /team-meeting\.wav/i,
    });

  await user.click(historyCard);

  expect(
    await screen.findByRole("heading", {
      name: "Summary",
    }),
  ).toBeInTheDocument();

  expect(
    screen.getAllByText(
      "The team reviewed project progress.",
    ),
  ).toHaveLength(2);

  expect(window.scrollTo).toHaveBeenCalled();
  });

  it("renames a speaker and updates the transcript", async () => {
    const user = userEvent.setup();
    const renamedMeeting: MeetingRecord = {
      ...testMeeting,
      segments: testMeeting.segments.map((segment) => ({
        ...segment,
        speaker:
          segment.speaker === "Speaker 1"
            ? "Dheepan"
            : segment.speaker,
      })),
    };

    vi.mocked(uploadMeeting).mockResolvedValue(testMeeting);
    vi.mocked(renameSpeaker).mockResolvedValue(
      renamedMeeting,
    );

    render(<App />);

    await user.upload(
      screen.getByLabelText(/choose file/i),
      new File(["audio"], "team-meeting.wav", {
        type: "audio/wav",
      }),
    );
    await user.click(
      await screen.findByRole("button", {
        name: "Process meeting",
      }),
    );
    await user.click(
      screen.getByText("View timestamped transcript"),
    );

    await user.type(
      screen.getByLabelText("Rename Speaker 1"),
      "Dheepan",
    );
    await user.click(
      screen.getAllByRole("button", { name: "Save" })[0],
    );

    expect(renameSpeaker).toHaveBeenCalledWith(
      1,
      "Speaker 1",
      "Dheepan",
    );
    expect(
      await screen.findByLabelText("Rename Dheepan"),
    ).toBeInTheDocument();
  });

  it("plays audio from the selected transcript timestamp", async () => {
  const user = userEvent.setup();

  vi.mocked(uploadMeeting).mockResolvedValue(
    testMeeting,
  );

  render(<App />);

  const file = new File(
    ["audio"],
    "team-meeting.wav",
    {
      type: "audio/wav",
    },
  );

  await user.upload(
    screen.getByLabelText(/choose file/i),
    file,
  );

  await user.click(
    await screen.findByRole("button", {
      name: "Process meeting",
    }),
  );

  await user.click(
      await screen.findByText(
        "View timestamped transcript",
      ),
    );

    const audio = screen.getByLabelText(
      "Meeting audio",
    ) as HTMLAudioElement;

    expect(audio).toHaveAttribute(
      "src",
      "http://127.0.0.1:8000/meetings/1/audio",
    );

    const secondSegment = screen.getByRole(
      "button",
      {
        name: /00:06.*00:12/i,
      },
    );

    await user.click(secondSegment);

    expect(audio.currentTime).toBeCloseTo(6.36);
    expect(playMock).toHaveBeenCalledTimes(1);
    expect(secondSegment).toHaveClass("active");
  });
  it("answers a meeting question and plays its source", async () => {
  const user = userEvent.setup();

  vi.mocked(uploadMeeting).mockResolvedValue(
    testMeeting,
  );

  vi.mocked(askMeeting).mockResolvedValue({
    meeting_id: 1,
    question: "What was decided?",
    answer: "The team decided to add automated tests.",
    answer_found: true,
    sources: [
      {
        segment_index: 1,
        start_seconds: 6.36,
        end_seconds: 12.5,
        text: (
          "The team agreed to add automated tests."
        ),
      },
    ],
  });

  render(<App />);

  const file = new File(
    ["audio"],
    "team-meeting.wav",
    {
      type: "audio/wav",
    },
  );

  await user.upload(
    screen.getByLabelText(/choose file/i),
    file,
  );

  await user.click(
    await screen.findByRole("button", {
      name: "Process meeting",
    }),
  );

  await user.type(
    screen.getByLabelText("Question"),
    "What was decided?",
  );

  await user.click(
    screen.getByRole("button", {
      name: "Ask",
    }),
  );

  expect(askMeeting).toHaveBeenCalledWith(
    1,
    "What was decided?",
    [],
  );

  expect(
    await screen.findByText(
      "The team decided to add automated tests.",
    ),
  ).toBeInTheDocument();

  expect(
    screen.getByText("Answer found"),
  ).toBeInTheDocument();

  const sourceButton = screen.getByRole(
    "button",
    {
      name: /play source at 00:06.*automated tests/i,
    },
  );

  await user.click(sourceButton);

  const audio = screen.getByLabelText(
    "Meeting audio",
  ) as HTMLAudioElement;

  await waitFor(() => {
    expect(audio.currentTime).toBeCloseTo(6.36);
  });

  expect(playMock).toHaveBeenCalled();
});
it("shows when an answer is absent from the meeting", async () => {
  const user = userEvent.setup();

  vi.mocked(uploadMeeting).mockResolvedValue(
    testMeeting,
  );

  vi.mocked(askMeeting).mockResolvedValue({
    meeting_id: 1,
    question: "What was the weather?",
    answer: "I couldn't find that in this meeting.",
    answer_found: false,
    sources: [],
  });

  render(<App />);

  const file = new File(
    ["audio"],
    "team-meeting.wav",
    {
      type: "audio/wav",
    },
  );

  await user.upload(
    screen.getByLabelText(/choose file/i),
    file,
  );

  await user.click(
    await screen.findByRole("button", {
      name: "Process meeting",
    }),
  );

  await user.type(
    screen.getByLabelText("Question"),
    "What was the weather?",
  );

  await user.click(
    screen.getByRole("button", {
      name: "Ask",
    }),
  );

  expect(
    await screen.findByText(
      "I couldn't find that in this meeting.",
    ),
  ).toBeInTheDocument();

  expect(
    screen.getByText("Not found in meeting"),
  ).toBeInTheDocument();
});

it("sends earlier answers with a follow-up question", async () => {
  const user = userEvent.setup();

  vi.mocked(uploadMeeting).mockResolvedValue(testMeeting);
  vi.mocked(askMeeting)
    .mockResolvedValueOnce({
      meeting_id: 1,
      question: "What task was assigned?",
      answer: "Automated testing was assigned.",
      answer_found: true,
      sources: [],
    })
    .mockResolvedValueOnce({
      meeting_id: 1,
      question: "Who owns that task?",
      answer: "Dheepan owns the testing task.",
      answer_found: true,
      sources: [],
    });

  render(<App />);

  await user.upload(
    screen.getByLabelText(/choose file/i),
    new File(["audio"], "team-meeting.wav", {
      type: "audio/wav",
    }),
  );
  await user.click(
    await screen.findByRole("button", {
      name: "Process meeting",
    }),
  );

  const questionInput = screen.getByLabelText("Question");
  await user.type(questionInput, "What task was assigned?");
  await user.click(screen.getByRole("button", { name: "Ask" }));
  await screen.findByText("Automated testing was assigned.");

  await user.type(questionInput, "Who owns that task?");
  await user.click(screen.getByRole("button", { name: "Ask" }));

  expect(askMeeting).toHaveBeenNthCalledWith(
    2,
    1,
    "Who owns that task?",
    [
      {
        question: "What task was assigned?",
        answer: "Automated testing was assigned.",
      },
    ],
  );

  expect(
    await screen.findByText("Dheepan owns the testing task."),
  ).toBeInTheDocument();
});
});
