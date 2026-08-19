type AttentionHeatmapProps = { timeSeries: number[]; attentionWeights: number[] };

/** Render a bounded inline waveform with a relative attention band. */
export function AttentionHeatmap({ timeSeries, attentionWeights }: AttentionHeatmapProps) {
  const count = Math.min(timeSeries.length, attentionWeights.length);
  const width = 1000;
  const height = 300;
  const chartTop = 28;
  const chartHeight = 172;
  const bandTop = 222;
  const step = count > 1 ? width / (count - 1) : width;
  const points = timeSeries.slice(0, count).map((value, index) => `${(index * step).toFixed(2)},${(chartTop + chartHeight / 2 - value * 92).toFixed(2)}`).join(" ");

  return <div className="overflow-hidden rounded-md border border-rule bg-surface-soft" role="img" aria-label="EEG waveform with attention weighting shown as a cyan-to-amber interval band"><svg className="block h-auto w-full" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none"><title>EEG time window and attention weighting</title><desc>Teal waveform over a band where warmer colors represent higher relative attention.</desc><line x1="0" y1={chartTop + chartHeight / 2} x2={width} y2={chartTop + chartHeight / 2} stroke="var(--color-rule)" strokeWidth="1" /><line x1="0" y1={bandTop - 10} x2={width} y2={bandTop - 10} stroke="var(--color-rule)" strokeWidth="1" />{attentionWeights.slice(0, count).map((weight, index) => <rect key={index} x={index * step} y={bandTop} width={Math.max(step + 0.8, 1)} height="34" fill={`hsl(${185 - weight * 145} 70% ${88 - weight * 22}%)`} />)}<polyline points={points} fill="none" stroke="var(--color-teal-dark)" strokeWidth="2.2" vectorEffect="non-scaling-stroke" /></svg><div className="flex justify-between border-t border-rule px-3 py-2 font-mono text-[10px] text-ink-faint"><span>0:00</span><span>0:05</span><span>0:10</span></div></div>;
}
