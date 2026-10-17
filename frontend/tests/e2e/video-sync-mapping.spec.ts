import { expect, test } from "@playwright/test";
import {
  eegTimeForVideoTime,
  videoTimeForEegTime,
  type VideoEegSync,
} from "../../src/lib/video-detection";

const segments: VideoEegSync["mapped_segments"] = [
  {
    video_start_seconds: 0,
    video_end_seconds: 2,
    eeg_source_start_seconds: 40,
  },
  {
    video_start_seconds: 4,
    video_end_seconds: 6,
    eeg_source_start_seconds: 44,
  },
];

test("source-clock mapping switches on exact boundaries and preserves gaps", () => {
  expect(videoTimeForEegTime(segments, 40)).toBe(0);
  expect(videoTimeForEegTime(segments, 42)).toBeNull();
  expect(videoTimeForEegTime(segments, 43)).toBeNull();
  expect(videoTimeForEegTime(segments, 44)).toBe(4);

  expect(eegTimeForVideoTime(segments, 0)).toBe(40);
  expect(eegTimeForVideoTime(segments, 2)).toBeNull();
  expect(eegTimeForVideoTime(segments, 3)).toBeNull();
  expect(eegTimeForVideoTime(segments, 4)).toBe(44);

  const adjacent: VideoEegSync["mapped_segments"] = [
    {
      video_start_seconds: 0,
      video_end_seconds: 2,
      eeg_source_start_seconds: 40,
    },
    {
      video_start_seconds: 0,
      video_end_seconds: 3,
      eeg_source_start_seconds: 42,
    },
  ];
  expect(videoTimeForEegTime(adjacent, 42)).toBe(0);
});

test("a verified video clock remains available through an EEG signal gap", () => {
  const verifiedClip: VideoEegSync["mapped_segments"] = [
    {
      video_start_seconds: 0,
      video_end_seconds: 102,
      eeg_source_start_seconds: 99,
    },
  ];

  expect(videoTimeForEegTime(verifiedClip, 150)).toBe(51);
  expect(eegTimeForVideoTime(verifiedClip, 51)).toBe(150);
});
