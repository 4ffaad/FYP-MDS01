import type { PredictionWindow } from "@/lib/types";

const CHART_WIDTH = 920;
const CHART_HEIGHT = 190;
const PADDING = { top: 18, right: 18, bottom: 34, left: 42 };

/** Render window scores, the alert threshold, and flagged intervals without waveform data. */
export function PredictionTimeline({ predictions, durationSeconds, threshold = 0.5 }: { predictions: PredictionWindow[]; durationSeconds: number; threshold?: number }) {
  const plotWidth = CHART_WIDTH - PADDING.left - PADDING.right;
  const plotHeight = CHART_HEIGHT - PADDING.top - PADDING.bottom;
  const duration = Math.max(durationSeconds, predictions.at(-1)?.endSeconds ?? 1, 1);
  const x = (seconds: number) => PADDING.left + (Math.max(0, seconds) / duration) * plotWidth;
  const y = (score: number) => PADDING.top + (1 - Math.max(0, Math.min(1, score))) * plotHeight;

  if (predictions.length === 0) {
    return <p className="rounded-md border border-rule bg-surface-soft px-4 py-4 text-sm text-ink-muted">No prediction windows were stored for this recording.</p>;
  }

  return (
    <div aria-label="Prediction score timeline" role="img">
      <div className="overflow-x-auto rounded-lg border border-rule bg-surface-soft p-2 sm:p-3">
        <svg className="h-auto min-w-[620px] w-full" viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`} aria-hidden="true">
          <line x1={PADDING.left} y1={y(threshold)} x2={CHART_WIDTH - PADDING.right} y2={y(threshold)} stroke="currentColor" strokeDasharray="5 5" className="text-amber" />
          <text x={PADDING.left - 8} y={y(threshold) + 4} textAnchor="end" className="fill-amber text-[11px]">{threshold.toFixed(1)}</text>
          <line x1={PADDING.left} y1={PADDING.top + plotHeight} x2={CHART_WIDTH - PADDING.right} y2={PADDING.top + plotHeight} stroke="currentColor" className="text-rule-strong" />
          <text x={PADDING.left - 8} y={PADDING.top + 4} textAnchor="end" className="fill-ink-faint text-[11px]">1.0</text>
          <text x={PADDING.left - 8} y={PADDING.top + plotHeight + 4} textAnchor="end" className="fill-ink-faint text-[11px]">0.0</text>
          {predictions.map((prediction) => {
            const left = x(prediction.startSeconds);
            const right = Math.max(left + 1, x(prediction.endSeconds));
            const scoreY = y(prediction.probability);
            return (
              <g key={`${prediction.startSeconds}-${prediction.endSeconds}`}>
                {prediction.seizureDetected && <rect x={left} y={PADDING.top} width={Math.max(1, right - left)} height={plotHeight} className="fill-red-soft/80" />}
                <line x1={left} y1={PADDING.top + plotHeight} x2={left} y2={scoreY} stroke="currentColor" strokeWidth="3" className={prediction.seizureDetected ? "text-red" : "text-teal"} />
                <circle cx={left} cy={scoreY} r="3.5" className={prediction.seizureDetected ? "fill-red" : "fill-teal"} />
              </g>
            );
          })}
          <text x={PADDING.left} y={CHART_HEIGHT - 8} className="fill-ink-faint text-[11px]">0:00</text>
          <text x={CHART_WIDTH - PADDING.right} y={CHART_HEIGHT - 8} textAnchor="end" className="fill-ink-faint text-[11px]">{formatSeconds(duration)}</text>
        </svg>
      </div>
      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-2 text-xs text-ink-muted" aria-label="Prediction timeline legend">
        <span className="inline-flex items-center gap-2"><span className="size-2 rounded-full bg-teal" aria-hidden="true" />Window score</span>
        <span className="inline-flex items-center gap-2"><span className="size-2 rounded-full bg-red" aria-hidden="true" />Model alert window</span>
        <span className="inline-flex items-center gap-2"><span className="w-4 border-t border-dashed border-amber" aria-hidden="true" />Threshold {threshold.toFixed(1)}</span>
      </div>
    </div>
  );
}

/** Format seconds as a compact timeline label. */
function formatSeconds(seconds: number): string {
  const whole = Math.max(0, Math.round(seconds));
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, "0")}`;
}
