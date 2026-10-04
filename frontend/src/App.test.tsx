import { render, screen } from "@testing-library/react";
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
  getHealth,
  getMeetings,
  uploadMeeting,
} from "./services/api";
import type { MeetingRecord } from "./types/meeting";

vi.mock("./services/api", () => ({
  getHealth: vi.fn(),
  getMeetings: vi.fn(),
  uploadMeeting: vi.fn(),
}));

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
});