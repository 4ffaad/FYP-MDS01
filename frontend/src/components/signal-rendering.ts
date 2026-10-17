import type {
  SignalPreviewChannel,
  SignalPreviewRepresentation,
} from "@/lib/types";

export type SignalChannelGroup =
  | "left"
  | "right"
  | "midline"
  | "other"
  | "auxiliary";

export interface OrderedSignalChannel {
  channel: SignalPreviewChannel;
  group: SignalChannelGroup;
}

const CLINICAL_MONTAGE = [
  ["Fp2-F8", "FP2", "F8"],
  ["F8-T4", "F8", "T8"],
  ["T4-T6", "T8", "P8"],
  ["T6-O2", "P8", "O2"],
  ["Fp1-F7", "FP1", "F7"],
  ["F7-T3", "F7", "T7"],
  ["T3-T5", "T7", "P7"],
  ["T5-O1", "P7", "O1"],
  ["Fp2-F4", "FP2", "F4"],
  ["F4-C4", "F4", "C4"],
  ["C4-P4", "C4", "P4"],
  ["P4-O2", "P4", "O2"],
  ["Fp1-F3", "FP1", "F3"],
  ["F3-C3", "F3", "C3"],
  ["C3-P3", "C3", "P3"],
  ["P3-O1", "P3", "O1"],
  ["Fz-Cz", "FZ", "CZ"],
  ["Cz-Pz", "CZ", "PZ"],
] as const;

const MONTAGE_ORDER = new Map<string, number>();
CLINICAL_MONTAGE.forEach(([label], index) => {
  MONTAGE_ORDER.set(normalizeChannelLabel(label), index);
});

const GROUP_ORDER: Record<SignalChannelGroup, number> = {
  right: 0,
  left: 1,
  midline: 2,
  other: 3,
  auxiliary: 4,
};

/** Orders clinical derivations as shown by the HUKM longitudinal montage. */
export function orderSignalChannels(
  channels: SignalPreviewChannel[],
): OrderedSignalChannel[] {
  return channels
    .map((channel, index) => ({
      channel,
      index,
      group: channelGroup(channel.label),
      montageIndex: montageIndex(channel.label),
      auxiliaryIndex: auxiliaryIndex(channel.label),
    }))
    .sort((left, right) => {
      const leftMontage = left.montageIndex < CLINICAL_MONTAGE.length;
      const rightMontage = right.montageIndex < CLINICAL_MONTAGE.length;
      if (leftMontage && rightMontage)
        return left.montageIndex - right.montageIndex;
      if (leftMontage !== rightMontage) return leftMontage ? -1 : 1;
      const groupDifference =
        GROUP_ORDER[left.group] - GROUP_ORDER[right.group];
      if (groupDifference !== 0) return groupDifference;
      if (left.group === "auxiliary" && right.group === "auxiliary")
        return left.auxiliaryIndex - right.auxiliaryIndex;
      if (left.montageIndex !== right.montageIndex)
        return left.montageIndex - right.montageIndex;
      return left.index - right.index;
    })
    .map(({ channel, group }) => ({ channel, group }));
}

/** Converts calibrated SI volts to microvolts; transformed values stay relative. */
export function displaySignalValue(
  sample: number,
  representation: SignalPreviewRepresentation,
): number {
  return representation === "metadata-scrubbed" ||
    representation === "original-source"
    ? sample * 1_000_000
    : sample;
}

/**
 * Derives available clinical bipolar channels without substituting electrodes.
 * Source pairs must have unique labels and sample-aligned timestamps.
 */
export function deriveClinicalLongitudinalMontage(
  channels: SignalPreviewChannel[],
  samplingRate: number,
  sharedTimes?: number[],
): SignalPreviewChannel[] | null {
  if (!Number.isFinite(samplingRate) || samplingRate <= 0) return null;
  const timedChannels = sharedTimes
    ? channels.map((channel) =>
        channel.timeSeconds
          ? channel
          : { ...channel, timeSeconds: sharedTimes },
      )
    : channels;
  const sourceElectrodes = new Map<string, SignalPreviewChannel | null>();
  const recordedDerivations = new Map<string, SignalPreviewChannel | null>();

  for (const channel of timedChannels) {
    const electrode = parseElectrodeLabel(channel.label);
    if (electrode) {
      sourceElectrodes.set(
        electrode,
        sourceElectrodes.has(electrode) ? null : channel,
      );
    } else {
      const normalized = normalizeChannelLabel(channel.label);
      if (MONTAGE_ORDER.has(normalized)) {
        recordedDerivations.set(
          normalized,
          recordedDerivations.has(normalized) ? null : channel,
        );
      }
    }
  }

  const derived: SignalPreviewChannel[] = [];
  for (const [label, leftName, rightName] of CLINICAL_MONTAGE) {
    const recorded = recordedDerivations.get(normalizeChannelLabel(label));
    if (recorded) {
      derived.push({ ...recorded, label });
      continue;
    }
    const left = sourceElectrodes.get(leftName);
    const right = sourceElectrodes.get(rightName);
    if (!left || !right || !timestampsAlign(left, right, samplingRate))
      continue;
    derived.push({
      label,
      samples: left.samples.map(
        (sample, index) => sample - right.samples[index],
      ),
      timeSeconds: left.timeSeconds,
    });
  }

  const auxiliaries = deriveChinPair(timedChannels, samplingRate);
  for (const channel of timedChannels) {
    if (isAuxiliary(channel.label) && !isChinSource(channel.label))
      auxiliaries.push(channel);
  }
  const ordered = orderSignalChannels([...derived, ...auxiliaries]).map(
    ({ channel }) => channel,
  );
  return ordered.length > 0 ? ordered : null;
}

/** True when every HUKM clinical bipolar derivation is present exactly once. */
export function hasRecordedLongitudinalBipolarMontage(
  channels: SignalPreviewChannel[],
): boolean {
  const counts = new Map<string, number>();
  channels.forEach(({ label }) => {
    const normalized = normalizeChannelLabel(label);
    if (MONTAGE_ORDER.has(normalized))
      counts.set(normalized, (counts.get(normalized) ?? 0) + 1);
  });
  return CLINICAL_MONTAGE.every(
    ([label]) => counts.get(normalizeChannelLabel(label)) === 1,
  );
}

export function clinicalMontageChannelCount(
  channels: SignalPreviewChannel[],
): number {
  const present = new Set(
    channels
      .map(({ label }) => normalizeChannelLabel(label))
      .filter((label) => MONTAGE_ORDER.has(label)),
  );
  return present.size;
}

export function channelGroupLabel(group: SignalChannelGroup): string {
  switch (group) {
    case "left":
      return "L";
    case "right":
      return "R";
    case "midline":
      return "M";
    case "auxiliary":
      return "Aux";
    default:
      return "Other";
  }
}

function deriveChinPair(
  channels: SignalPreviewChannel[],
  samplingRate: number,
): SignalPreviewChannel[] {
  const chin1 = uniqueChannel(channels, "CHIN1");
  const chin2 = uniqueChannel(channels, "CHIN2");
  if (!chin1 || !chin2 || !timestampsAlign(chin1, chin2, samplingRate))
    return [];
  return [
    {
      label: "Chin 1-Chin 2",
      samples: chin1.samples.map(
        (sample, index) => sample - chin2.samples[index],
      ),
      timeSeconds: chin1.timeSeconds,
    },
  ];
}

function uniqueChannel(
  channels: SignalPreviewChannel[],
  label: string,
): SignalPreviewChannel | null {
  const found = channels.filter(
    (channel) => normalizeChannelLabel(channel.label) === label,
  );
  return found.length === 1 ? found[0] : null;
}

function timestampsAlign(
  left: SignalPreviewChannel,
  right: SignalPreviewChannel,
  samplingRate: number,
): boolean {
  const leftTimes = left.timeSeconds;
  const rightTimes = right.timeSeconds;
  if (
    !leftTimes ||
    !rightTimes ||
    left.samples.length !== right.samples.length ||
    leftTimes.length !== rightTimes.length ||
    leftTimes.length !== left.samples.length
  )
    return false;
  for (let index = 0; index < leftTimes.length; index += 1) {
    if (
      !Number.isFinite(leftTimes[index]) ||
      !Number.isFinite(rightTimes[index]) ||
      Math.abs(leftTimes[index] - rightTimes[index]) > 0.5 / samplingRate
    )
      return false;
  }
  return true;
}

function montageIndex(label: string): number {
  return (
    MONTAGE_ORDER.get(normalizeChannelLabel(label)) ?? Number.MAX_SAFE_INTEGER
  );
}

function auxiliaryIndex(label: string): number {
  const normalized = normalizeChannelLabel(label);
  if (/^(?:ECG|EKG)/.test(normalized)) return 0;
  if (/EOG.*LEFT/.test(normalized)) return 1;
  if (/EOG.*RIGHT/.test(normalized)) return 2;
  if (/CHIN/.test(normalized)) return 3;
  if (/PHOTIC/.test(normalized)) return 4;
  return 5;
}

function channelGroup(label: string): SignalChannelGroup {
  const normalized = normalizeChannelLabel(label);
  if (isAuxiliary(normalized)) return "auxiliary";
  const index = MONTAGE_ORDER.get(normalized);
  if (index !== undefined) {
    if (index < 4 || (index >= 8 && index < 12)) return "right";
    if ((index >= 4 && index < 8) || (index >= 12 && index < 16)) return "left";
    return "midline";
  }
  const electrode = parseElectrodeLabel(label);
  if (electrode && /^(?:FP|F|C|P|O|T)[13579]$/.test(electrode)) return "left";
  if (electrode && /^(?:FP|F|C|P|O|T)[2468]$/.test(electrode)) return "right";
  if (electrode && /^(?:FZ|CZ|PZ)$/.test(electrode)) return "midline";
  return "other";
}

function isAuxiliary(label: string): boolean {
  return /^(?:ECG|EKG|EOG|EMG|CHIN|PHOTIC|AUX|TRIGGER)/.test(
    normalizeChannelLabel(label),
  );
}

function isChinSource(label: string): boolean {
  return /^CHIN[12]$/.test(normalizeChannelLabel(label));
}

function normalizeChannelLabel(label: string): string {
  return label
    .trim()
    .replace(/^EEG\s*/i, "")
    .replace(/(?:-?REF|-?LE|-?RE)$/i, "")
    .toUpperCase()
    .replace(/\bT3\b/g, "T7")
    .replace(/\bT4\b/g, "T8")
    .replace(/\bT5\b/g, "P7")
    .replace(/\bT6\b/g, "P8")
    .replace(/\s+/g, "");
}

function parseElectrodeLabel(label: string): string | null {
  const normalized = normalizeChannelLabel(label);
  if (/^(?:FP|F|C|P|O|T)[1-8]$|^(?:FZ|CZ|PZ)$/.test(normalized))
    return normalized;
  return null;
}
