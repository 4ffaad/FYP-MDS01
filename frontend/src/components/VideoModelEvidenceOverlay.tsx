"use client";

import { useEffect, useRef, type RefObject } from "react";
import type { DetectionResult } from "@/lib/video-detection";

type ModelEvidence = NonNullable<
  DetectionResult["predictions"][number]["model_evidence"]
>;

export type VideoPoseSample = NonNullable<
  ModelEvidence["pose_samples"]
>[number];
export type GradCamSample = NonNullable<
  ModelEvidence["gradcam_samples"]
>[number];

function nearestSample<T extends { timestamp: number }>(
  samples: T[] | undefined,
  timeSeconds: number,
  sampleFps: number,
): T | null {
  if (!Number.isFinite(timeSeconds) || !samples?.length) return null;
  const nearest = samples.reduce((closest, sample) =>
    Math.abs(sample.timestamp - timeSeconds) <
    Math.abs(closest.timestamp - timeSeconds)
      ? sample
      : closest,
  );
  return Math.abs(nearest.timestamp - timeSeconds) <= 1 / Math.max(sampleFps, 1)
    ? nearest
    : null;
}

export function poseSampleForVideoTime(
  prediction: DetectionResult["predictions"][number] | undefined,
  timeSeconds: number,
  sampleFps: number,
): VideoPoseSample | null {
  return nearestSample(
    prediction?.model_evidence?.pose_samples,
    timeSeconds,
    sampleFps,
  );
}

export function gradCamSampleForVideoTime(
  prediction: DetectionResult["predictions"][number] | undefined,
  timeSeconds: number,
  sampleFps: number,
): GradCamSample | null {
  return nearestSample(
    prediction?.model_evidence?.gradcam_samples,
    timeSeconds,
    sampleFps,
  );
}

/** Blur the same 128×128 source regions that VSViG downsamples into patches. */
export function VideoModelPatchBlurOverlay({
  videoRef,
  poseSample,
  strengthPercent,
  enabled,
}: {
  videoRef: RefObject<HTMLVideoElement | null>;
  poseSample: VideoPoseSample | null;
  strengthPercent: number;
  enabled: boolean;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const settingsRef = useRef({ poseSample, strengthPercent, enabled });
  const drawRef = useRef<() => void>(() => {});

  useEffect(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    if (!video || !canvas || !context) return;

    let animationFrame = 0;
    const draw = () => {
      const width = video.videoWidth;
      const height = video.videoHeight;
      if (!width || !height) return;
      if (canvas.width !== width || canvas.height !== height) {
        canvas.width = width;
        canvas.height = height;
      }
      context.clearRect(0, 0, width, height);
      const settings = settingsRef.current;
      if (
        !settings.enabled ||
        !settings.poseSample ||
        video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA
      )
        return;

      const blurPixels = 12 + ((settings.strengthPercent - 50) / 50) * 16;
      for (const point of settings.poseSample.points) {
        if (point.confidence <= 0) continue;
        const halfWidth = (64 * width) / 1920;
        const halfHeight = (64 * height) / 1080;
        const left = Math.max(0, point.x * width - halfWidth);
        const top = Math.max(0, point.y * height - halfHeight);
        const right = Math.min(width, point.x * width + halfWidth);
        const bottom = Math.min(height, point.y * height + halfHeight);
        const padding = blurPixels * 2;
        const sourceLeft = Math.max(0, left - padding);
        const sourceTop = Math.max(0, top - padding);
        const sourceRight = Math.min(width, right + padding);
        const sourceBottom = Math.min(height, bottom + padding);
        context.save();
        context.beginPath();
        context.rect(left, top, right - left, bottom - top);
        context.clip();
        context.filter = `blur(${blurPixels}px)`;
        context.drawImage(
          video,
          sourceLeft,
          sourceTop,
          sourceRight - sourceLeft,
          sourceBottom - sourceTop,
          sourceLeft,
          sourceTop,
          sourceRight - sourceLeft,
          sourceBottom - sourceTop,
        );
        context.restore();
      }
    };
    drawRef.current = draw;
    const schedule = () => {
      if (animationFrame || video.paused || video.ended) return;
      animationFrame = window.requestAnimationFrame(tick);
    };
    const tick = () => {
      animationFrame = 0;
      draw();
      schedule();
    };
    const stop = () => {
      window.cancelAnimationFrame(animationFrame);
      animationFrame = 0;
      draw();
    };
    const play = () => schedule();
    const repaint = () => {
      if (video.paused) draw();
    };

    video.addEventListener("play", play);
    video.addEventListener("pause", stop);
    video.addEventListener("seeked", repaint);
    video.addEventListener("timeupdate", repaint);
    video.addEventListener("loadeddata", repaint);
    draw();
    schedule();
    return () => {
      window.cancelAnimationFrame(animationFrame);
      video.removeEventListener("play", play);
      video.removeEventListener("pause", stop);
      video.removeEventListener("seeked", repaint);
      video.removeEventListener("timeupdate", repaint);
      video.removeEventListener("loadeddata", repaint);
    };
  }, [videoRef]);

  useEffect(() => {
    settingsRef.current = { poseSample, strengthPercent, enabled };
    if (videoRef.current?.paused) drawRef.current();
  }, [enabled, poseSample, strengthPercent, videoRef]);

  return (
    <canvas
      ref={canvasRef}
      className="pointer-events-none absolute inset-0 size-full"
      aria-hidden="true"
      data-testid="video-model-patch-blur"
    />
  );
}

/** Show graph-CAM relevance as colored bounds on the exact analyzed patches. */
export function VideoGradCamOverlay({
  poseSample,
  gradCamSample,
}: {
  poseSample: VideoPoseSample | null;
  gradCamSample: GradCamSample | null;
}) {
  if (!poseSample || !gradCamSample) return null;
  const relevanceByPatch = new Map(
    gradCamSample.patches.map((patch) => [patch.patch_index, patch.relevance]),
  );
  const regions = poseSample.points.flatMap((point) => {
    const relevance = relevanceByPatch.get(point.patch_index) ?? 0;
    return point.confidence > 0 ? [{ point, relevance }] : [];
  });
  if (!regions.length) return null;

  return (
    <svg
      className="pointer-events-none absolute inset-0 size-full"
      viewBox="0 0 1920 1080"
      preserveAspectRatio="none"
      aria-hidden="true"
      data-testid="video-vsvig-gradcam"
    >
      {regions.map(({ point, relevance }) => {
        const centerX = point.x * 1920;
        const centerY = point.y * 1080;
        const x = Math.max(0, Math.min(1920, centerX - 64));
        const y = Math.max(0, Math.min(1080, centerY - 64));
        const width = Math.max(0, Math.min(1920, centerX + 64) - x);
        const height = Math.max(0, Math.min(1080, centerY + 64) - y);
        const hue = Math.round(58 * (1 - relevance));
        return (
          <rect
            key={point.patch_index}
            x={x}
            y={y}
            width={width}
            height={height}
            fill={`hsl(${hue} 95% 52%)`}
            fillOpacity={0.06 + relevance * 0.38}
            stroke={`hsl(${hue} 100% 58%)`}
            strokeOpacity={0.45 + relevance * 0.45}
            strokeWidth="3"
          />
        );
      })}
    </svg>
  );
}
