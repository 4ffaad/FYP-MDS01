"use client";

import Image from "next/image";

interface VideoBlurStrengthControlProps {
  value: number;
  onChange: (value: number) => void;
  disabled?: boolean;
}

export function VideoBlurStrengthControl({
  value,
  onChange,
  disabled = false,
}: VideoBlurStrengthControlProps) {
  return (
    <div className="mt-4 border-t border-rule pt-4">
      <div className="flex items-center justify-between gap-3">
        <label
          htmlFor="video-model-blur-strength"
          className="text-sm font-semibold text-ink"
        >
          VSViG input patch blur
        </label>
        <output
          htmlFor="video-model-blur-strength"
          className="font-mono text-sm tabular-nums text-ink"
        >
          {value}%
        </output>
      </div>
      <input
        id="video-model-blur-strength"
        type="range"
        min={50}
        max={100}
        step={5}
        value={value}
        disabled={disabled}
        aria-label="VSViG patch blur strength"
        aria-describedby="video-model-blur-help"
        className="mt-3 w-full accent-teal disabled:opacity-50"
        onChange={(event) => onChange(Number(event.currentTarget.value))}
      />
      <p
        id="video-model-blur-help"
        className="mt-2 text-xs leading-5 text-ink-muted"
      >
        Blurs only the 15 keypoint patches sent to VSViG. The review video
        separately blurs the face, with full-frame fallback if tracking is
        uncertain.
      </p>
      <details className="mt-3 rounded-xl border border-rule bg-surface-soft px-3 py-2">
        <summary className="min-h-9 cursor-pointer py-2 text-xs font-semibold text-ink">
          Preview face blur
        </summary>
        <figure className="pb-2">
          <Image
            src="/examples/vsvig-face-blur-example.webp"
            alt="VSViG example video frame with the face blurred and body pose overlaid"
            width={560}
            height={720}
            className="max-h-72 w-full rounded-lg object-contain object-left"
          />
          <figcaption className="mt-2 text-xs text-ink-muted">
            Public VSViG example · face blurred, body visible.
          </figcaption>
        </figure>
      </details>
    </div>
  );
}
