import { expect, test } from "@playwright/test";
import {
  deriveClinicalLongitudinalMontage,
  displaySignalValue,
  hasRecordedLongitudinalBipolarMontage,
  orderSignalChannels,
} from "../../src/components/signal-rendering";

test("orders the HUKM bipolar montage and auxiliary channels", () => {
  const ordered = orderSignalChannels(
    [
      "EOG Right-Ref",
      "Fp2-F8",
      "Fp2-F4",
      "Fz-Cz",
      "Fp1-F7",
      "ECG",
      "F8-T4",
      "F7-T3",
    ].map((label) => ({ label, samples: [] })),
  );

  expect(ordered.map(({ channel }) => channel.label)).toEqual([
    "Fp2-F8",
    "F8-T4",
    "Fp1-F7",
    "F7-T3",
    "Fp2-F4",
    "Fz-Cz",
    "ECG",
    "EOG Right-Ref",
  ]);
  expect(ordered.map(({ group }) => group)).toEqual([
    "right",
    "right",
    "left",
    "left",
    "right",
    "midline",
    "auxiliary",
    "auxiliary",
  ]);
});

test("converts calibrated volts to microvolts and leaves transformed values relative", () => {
  expect(displaySignalValue(25e-6, "original-source")).toBeCloseTo(25);
  expect(displaySignalValue(-10e-6, "metadata-scrubbed")).toBeCloseTo(-10);
  expect(displaySignalValue(0.75, "signal-obfuscated")).toBe(0.75);
  expect(displaySignalValue(2.5, "normalized-units")).toBe(2.5);
});

test("derives exact HUKM first-minus-second montage from aligned source electrodes", () => {
  const values = new Map([
    ["FP2", 30],
    ["F8", 10],
    ["FP1", 5],
    ["F7", -5],
  ]);
  const channels = [
    "Fp1",
    "F7",
    "T3",
    "T5",
    "O1",
    "F3",
    "C3",
    "P3",
    "Fp2",
    "F8",
    "T4",
    "T6",
    "O2",
    "F4",
    "C4",
    "P4",
    "Fz",
    "Cz",
    "Pz",
    "EOG Left-Ref",
    "EOG Right-Ref",
    "ECG",
    "Chin 1",
    "Chin 2",
    "Photic",
  ].map((label) => ({
    label,
    samples: [values.get(label.toUpperCase()) ?? 0, 1],
    timeSeconds: [7200, 7200.002],
  }));

  const montage = deriveClinicalLongitudinalMontage(channels, 500);
  expect(montage).not.toBeNull();
  expect(montage).toHaveLength(23);
  expect(montage?.slice(0, 8).map(({ label }) => label)).toEqual([
    "Fp2-F8",
    "F8-T4",
    "T4-T6",
    "T6-O2",
    "Fp1-F7",
    "F7-T3",
    "T3-T5",
    "T5-O1",
  ]);
  expect(montage?.[0].samples[0]).toBe(20);
  expect(montage?.[4].samples[0]).toBe(10);
  expect(montage?.at(-1)?.label).toBe("Photic");
  expect(hasRecordedLongitudinalBipolarMontage(montage ?? [])).toBe(true);
});

test("does not derive a bipolar channel when source timestamps are misaligned", () => {
  const source = [
    { label: "Fp2", samples: [30, 10], timeSeconds: [0, 0.002] },
    { label: "F8", samples: [10, 4], timeSeconds: [0, 0.004] },
    { label: "Fp1", samples: [0, 0], timeSeconds: [0, 0.002] },
    { label: "F7", samples: [0, 0], timeSeconds: [0, 0.002] },
  ];
  const partial = deriveClinicalLongitudinalMontage(source, 500);
  expect(partial?.some(({ label }) => label === "Fp2-F8")).toBe(false);
  expect(partial?.some(({ label }) => label === "Fp1-F7")).toBe(true);
});

test("derives the montage from a shared timestamp array when channel times are omitted", () => {
  const sharedTimes = [7200, 7200.002];
  const source = [
    { label: "Fp2", samples: [30, 10] },
    { label: "F8", samples: [10, 4] },
  ];

  const montage = deriveClinicalLongitudinalMontage(source, 500, sharedTimes);

  expect(montage?.find(({ label }) => label === "Fp2-F8")).toEqual({
    label: "Fp2-F8",
    samples: [20, 6],
    timeSeconds: sharedTimes,
  });
});
