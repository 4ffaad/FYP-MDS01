"use client";

import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { API_STUB_ENABLED } from "@/lib/api";
import {
  CLINICAL_OBSERVATION_TYPES,
  createClinicalAnnotation,
  listClinicalAnnotations,
  type ClinicalAnnotation,
  type ClinicalObservationType,
} from "@/lib/clinical-annotations";
import { formatRelativeTime } from "@/lib/format";

const LABELS: Record<ClinicalObservationType, string> = {
  left_arm_movement: "Left arm movement",
  right_arm_movement: "Right arm movement",
  left_leg_movement: "Left leg movement",
  right_leg_movement: "Right leg movement",
  bilateral_movement: "Bilateral movement",
  head_or_eye_deviation: "Head or eye deviation",
  other_observed_behavior: "Other observed behavior",
  uncertain_or_unobservable: "Uncertain / unobservable",
};

export function ClinicalObservationPanel({
  recordId,
  durationSeconds,
  selectedEegTime,
  onEegTimeSelect,
  onAnnotationsChange,
}: {
  recordId: string;
  durationSeconds: number;
  selectedEegTime: number | null;
  onEegTimeSelect: (seconds: number) => void;
  onAnnotationsChange: (annotations: ClinicalAnnotation[]) => void;
}) {
  const [annotations, setAnnotations] = useState<ClinicalAnnotation[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [startSeconds, setStartSeconds] = useState(
    String(Math.max(0, selectedEegTime ?? 0).toFixed(1)),
  );
  const [endSeconds, setEndSeconds] = useState(
    String(
      Math.min(durationSeconds, Math.max(0, selectedEegTime ?? 0) + 2).toFixed(
        1,
      ),
    ),
  );
  const [observations, setObservations] = useState<ClinicalObservationType[]>(
    [],
  );
  const [description, setDescription] = useState("");

  useEffect(() => {
    if (API_STUB_ENABLED) return;
    const controller = new AbortController();
    void listClinicalAnnotations(recordId, controller.signal)
      .then((items) => {
        if (!controller.signal.aborted) {
          setAnnotations(items);
          onAnnotationsChange(items);
          setLoadError(null);
        }
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setLoadError(
          error instanceof Error
            ? error.message
            : "Clinical observations could not be loaded.",
        );
      });
    return () => controller.abort();
  }, [onAnnotationsChange, recordId]);

  const sortedAnnotations = useMemo(
    () => [...annotations].sort((a, b) => a.start_seconds - b.start_seconds),
    [annotations],
  );

  const toggleObservation = (value: ClinicalObservationType) => {
    setObservations((current) =>
      current.includes(value)
        ? current.filter((item) => item !== value)
        : [...current, value],
    );
  };

  const usePlayheadAsStart = () => {
    const start = Math.min(
      Math.max(0, durationSeconds),
      Math.max(0, selectedEegTime ?? 0),
    );
    setStartSeconds(start.toFixed(1));
    setEndSeconds(Math.min(durationSeconds, start + 2).toFixed(1));
  };

  const save = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setSaveError(null);
    try {
      const created = await createClinicalAnnotation(recordId, {
        start_seconds: Number(startSeconds),
        end_seconds: Number(endSeconds),
        observations,
        description,
      });
      const nextAnnotations = [...annotations, created];
      setAnnotations(nextAnnotations);
      onAnnotationsChange(nextAnnotations);
      setObservations([]);
      setDescription("");
    } catch (error: unknown) {
      setSaveError(
        error instanceof Error
          ? error.message
          : "Clinical observation could not be saved.",
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <section
      className="border-t border-rule px-4 py-4 sm:px-6"
      aria-labelledby="clinical-observations-heading"
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 id="clinical-observations-heading" className="text-sm font-bold">
          Clinical observations
        </h3>
        <p className="text-xs text-ink-muted">
          Time-linked observations only · no automatic diagnosis or brain-side
          inference
        </p>
      </div>

      {API_STUB_ENABLED ? (
        <p className="mt-3 text-sm text-ink-muted" role="status">
          Persistent observations require the authenticated backend; they are
          unavailable in the browser API stub.
        </p>
      ) : (
        <form className="mt-4 space-y-3" onSubmit={save}>
          <div className="flex flex-wrap items-end gap-3">
            <label className="grid gap-1 text-xs font-semibold text-ink-muted">
              Start (recording time, seconds)
              <input
                className="min-h-10 w-40 rounded-md border border-rule bg-surface px-3 font-mono text-sm text-ink"
                type="number"
                min="0"
                max={durationSeconds}
                step="0.1"
                required
                value={startSeconds}
                onChange={(event) => setStartSeconds(event.target.value)}
              />
            </label>
            <label className="grid gap-1 text-xs font-semibold text-ink-muted">
              End (recording time, seconds)
              <input
                className="min-h-10 w-40 rounded-md border border-rule bg-surface px-3 font-mono text-sm text-ink"
                type="number"
                min="0"
                max={durationSeconds}
                step="0.1"
                required
                value={endSeconds}
                onChange={(event) => setEndSeconds(event.target.value)}
              />
            </label>
            <button
              className="min-h-10 rounded-md border border-rule px-3 text-sm font-semibold text-teal-dark hover:bg-surface-soft"
              type="button"
              onClick={usePlayheadAsStart}
            >
              Use current EEG time
            </button>
          </div>

          <fieldset>
            <legend className="mb-2 text-xs font-semibold text-ink-muted">
              Observed behavior
            </legend>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
              {CLINICAL_OBSERVATION_TYPES.map((item) => (
                <label
                  className="flex min-h-9 items-center gap-2 text-sm"
                  key={item}
                >
                  <input
                    type="checkbox"
                    checked={observations.includes(item)}
                    onChange={() => toggleObservation(item)}
                  />
                  {LABELS[item]}
                </label>
              ))}
            </div>
          </fieldset>

          <label className="grid gap-1 text-xs font-semibold text-ink-muted">
            Notes
            <textarea
              className="min-h-20 rounded-md border border-rule bg-surface px-3 py-2 text-sm font-normal text-ink"
              maxLength={4000}
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="Describe what is visible, including uncertainty."
            />
          </label>
          <p className="text-xs leading-5 text-ink-muted">
            These are observations by the authenticated owner account. Movement
            side does not by itself identify seizure onset. The observation text
            is encrypted at rest.
          </p>
          <div className="flex items-center gap-3">
            <button
              className="min-h-10 rounded-md bg-teal-dark px-4 text-sm font-semibold text-white disabled:opacity-60"
              type="submit"
              disabled={saving}
            >
              {saving ? "Saving…" : "Save observation"}
            </button>
            {saveError && (
              <p className="text-sm text-red" role="alert">
                {saveError}
              </p>
            )}
          </div>
        </form>
      )}

      {loadError && (
        <p className="mt-3 text-sm text-red" role="alert">
          {loadError}
        </p>
      )}
      <div className="mt-4 space-y-2">
        {sortedAnnotations.length === 0 ? (
          <p className="text-sm text-ink-muted">
            No clinician observations are saved for this recording.
          </p>
        ) : (
          sortedAnnotations.map((item) => (
            <button
              className="block w-full rounded-md border border-rule px-3 py-2 text-left hover:bg-surface-soft"
              key={item.annotation_id}
              type="button"
              onClick={() => onEegTimeSelect(item.start_seconds)}
              aria-label={`Jump to clinician observation at ${formatRelativeTime(item.start_seconds)}`}
            >
              <span className="font-mono text-xs font-semibold tabular-nums">
                {formatRelativeTime(item.start_seconds)}–
                {formatRelativeTime(item.end_seconds)}
              </span>
              <span className="ml-2 text-xs font-semibold text-teal-dark">
                Clinician observation · owner account
              </span>
              <span className="mt-1 block text-sm">
                {item.observations.map((value) => LABELS[value]).join(" · ")}
              </span>
              {item.description && (
                <span className="mt-1 block whitespace-pre-wrap text-sm text-ink-muted">
                  {item.description}
                </span>
              )}
            </button>
          ))
        )}
      </div>
    </section>
  );
}
