"use client";

import { useId, useMemo, useState } from "react";
import type { PrivacyMethod } from "@/lib/types";
import { PRIVACY_SIGNAL_CHANNELS } from "@/lib/api";
import { Slider } from "@/components/ui/slider";
import { Icon } from "./Icon";

const ROW_HEIGHT = 29;
const CHART_HEIGHT = ROW_HEIGHT * PRIVACY_SIGNAL_CHANNELS.length;
const SAMPLE_COUNT = 180;

function syntheticTrace(channelIndex: number, obfuscated: boolean): string {
  const row = channelIndex * ROW_HEIGHT + ROW_HEIGHT / 2;
  const points = Array.from({ length: SAMPLE_COUNT }, (_, index) => {
    const progress = index / (SAMPLE_COUNT - 1);
    const base =
      Math.sin(progress * 34 + channelIndex * 0.43) * 4.5 +
      Math.sin(progress * 79 + channelIndex * 0.17) * 1.7 +
      Math.sin(progress * 151 + channelIndex) * 0.8;
    const value = obfuscated ? Math.round((base * 0.68) / 1.5) * 1.5 : base;
    return `${(17 + progress * 82).toFixed(2)},${(row - value).toFixed(2)}`;
  });
  return `M ${points.join(" L ")}`;
}

/** Show a deterministic synthetic comparison without requesting uploaded VEEG. */
export function PrivacyPreview({
  method,
  compact = false,
}: {
  method: PrivacyMethod;
  compact?: boolean;
}) {
  const [afterReveal, setAfterReveal] = useState(50);
  const clipId = useId().replace(/:/g, "");
  const dividerPosition = 100 - afterReveal;
  const beforePaths = useMemo(
    () =>
      PRIVACY_SIGNAL_CHANNELS.map((_, index) => syntheticTrace(index, false)),
    [],
  );
  const afterPaths = useMemo(
    () =>
      PRIVACY_SIGNAL_CHANNELS.map((_, index) =>
        syntheticTrace(index, method.id === "signal-obfuscation"),
      ),
    [method.id],
  );
  const obfuscated = method.id === "signal-obfuscation";

  return (
    <section
      className="panel overflow-hidden"
      aria-labelledby="preview-heading"
    >
      <div
        className={`${compact ? "px-4 py-4" : "px-5 py-5 sm:px-7"} border-b border-rule`}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2
              id="preview-heading"
              className={`${compact ? "text-sm" : "text-base"} font-bold`}
            >
              {compact
                ? "Privacy representation preview"
                : (method.previewTitle ?? method.label)}
            </h2>
            <p className="mt-1 text-sm leading-6 text-ink-muted">
              Illustrative preview — synthetic data, not your uploaded VEEG.
            </p>
          </div>
          <span className="grid size-9 shrink-0 place-items-center rounded-md bg-teal-soft text-teal">
            <Icon name="activity" className="size-5" />
          </span>
        </div>
      </div>

      <div className={compact ? "px-4 py-4" : "px-5 py-6 sm:px-7"}>
        <div className="rounded-lg border border-rule bg-[#fbfcfe] p-4">
          <div className="flex flex-wrap items-center justify-between gap-2 text-[0.68rem] font-semibold text-ink-faint">
            <span>18 model channels</span>
            <span>4-second window · 256 Hz</span>
          </div>

          <div className="mt-4 grid grid-cols-2 text-xs font-semibold">
            <span className="border-b-2 border-[#6b7b99] pb-2 text-[#52627e]">
              Before · staged
            </span>
            <span className="border-b-2 border-teal bg-teal-soft px-2 pb-2 text-right text-teal-dark">
              After · {obfuscated ? "obfuscated" : "metadata scrubbed"}
            </span>
          </div>

          <div className="mt-3 overflow-x-auto">
            <div
              className={`relative ${compact ? "min-w-[30rem]" : "min-w-[34rem]"}`}
              style={{ height: `${CHART_HEIGHT}px` }}
            >
              <svg
                className="absolute inset-0 h-full w-full"
                viewBox={`0 0 100 ${CHART_HEIGHT}`}
                role="img"
                aria-label={`Synthetic 18-channel VEEG preview for ${method.label}`}
                preserveAspectRatio="none"
              >
                <defs>
                  <clipPath id={`${clipId}-before`} data-layer-clip="before">
                    <rect
                      x="0"
                      y="0"
                      width={dividerPosition}
                      height={CHART_HEIGHT}
                    />
                  </clipPath>
                  <clipPath id={`${clipId}-after`} data-layer-clip="after">
                    <rect
                      x={dividerPosition}
                      y="0"
                      width={afterReveal}
                      height={CHART_HEIGHT}
                    />
                  </clipPath>
                </defs>
                {PRIVACY_SIGNAL_CHANNELS.map((label, index) => {
                  const baseline = index * ROW_HEIGHT + ROW_HEIGHT / 2;
                  return (
                    <line
                      key={label}
                      x1="17"
                      x2="100"
                      y1={baseline}
                      y2={baseline}
                      stroke="#e5e7eb"
                      strokeWidth="0.35"
                      vectorEffect="non-scaling-stroke"
                    />
                  );
                })}
                <g
                  clipPath={`url(#${clipId}-before)`}
                  data-waveform-layer="before"
                >
                  {beforePaths.map((path, index) => (
                    <path
                      key={PRIVACY_SIGNAL_CHANNELS[index]}
                      d={path}
                      fill="none"
                      stroke="#6b7b99"
                      strokeWidth="0.75"
                      vectorEffect="non-scaling-stroke"
                    />
                  ))}
                </g>
                <g
                  clipPath={`url(#${clipId}-after)`}
                  data-waveform-layer="after"
                >
                  <rect
                    x={dividerPosition}
                    y="0"
                    width={afterReveal}
                    height={CHART_HEIGHT}
                    fill="#e6f5f2"
                    opacity="0.7"
                  />
                  {afterPaths.map((path, index) => (
                    <path
                      key={PRIVACY_SIGNAL_CHANNELS[index]}
                      d={path}
                      fill="none"
                      stroke="#087f75"
                      strokeWidth="0.9"
                      vectorEffect="non-scaling-stroke"
                    />
                  ))}
                </g>
                {afterReveal > 0 && afterReveal < 100 && (
                  <line
                    x1={dividerPosition}
                    x2={dividerPosition}
                    y1="0"
                    y2={CHART_HEIGHT}
                    stroke="#087f75"
                    strokeWidth="1.35"
                    vectorEffect="non-scaling-stroke"
                  />
                )}
              </svg>
              <div className="pointer-events-none absolute inset-y-0 left-0 flex w-[17%] flex-col justify-around bg-[#fbfcfe] pr-2 font-mono text-[10px] font-semibold text-ink-muted">
                {PRIVACY_SIGNAL_CHANNELS.map((label) => (
                  <span key={label}>{label}</span>
                ))}
              </div>
            </div>
          </div>

          <div className="mt-5 rounded-lg border border-rule bg-surface px-3.5 py-3">
            <div className="flex items-center justify-between gap-3 text-xs font-semibold text-ink">
              <span>Compare the representation</span>
              <span className="font-mono tabular-nums text-teal-dark">
                {100 - afterReveal}% before · {afterReveal}% after
              </span>
            </div>
            <Slider
              className="mt-4 [&_[data-slot=slider-track]]:bg-surface-muted [&_[data-slot=slider-range]]:bg-teal [&_[data-slot=slider-thumb]]:size-4 [&_[data-slot=slider-thumb]]:border-teal [&_[data-slot=slider-thumb]]:bg-white"
              min={0}
              max={100}
              step={1}
              value={[afterReveal]}
              onValueChange={([value]) => setAfterReveal(value ?? 50)}
              aria-label="Before and after preview divider"
              aria-valuetext={`${100 - afterReveal}% before · ${afterReveal}% after`}
            />
            <div className="mt-2 flex justify-between text-[0.68rem] text-ink-faint">
              <span>100% before</span>
              <span>50 / 50</span>
              <span>100% after</span>
            </div>
          </div>
        </div>

        <p className="mt-5 text-sm leading-6 text-ink-muted">
          {method.previewDescription}
        </p>
        <p className="mt-4 rounded-md bg-surface-soft px-3 py-2 text-xs font-mono leading-5 text-ink-muted">
          18 channels · 256 Hz · 4-second windows · (N, 1024, 18) float32
        </p>
      </div>
      <div className="border-t border-rule bg-amber-soft px-5 py-4 text-xs leading-5 text-amber">
        <span className="font-bold">Research boundary.</span> This is a
        synthetic illustration. Signal obfuscation reduces detail
        experimentally; it is not a formal anonymity guarantee.
      </div>
    </section>
  );
}
