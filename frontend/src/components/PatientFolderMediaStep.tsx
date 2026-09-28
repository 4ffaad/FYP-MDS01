"use client";

import { Button } from "@/components/ui/button";
import { Icon } from "./Icon";

interface PatientFolderMediaStepProps {
  eegCount: number;
  videoCount: number;
  signalObfuscation: boolean;
  signalDescription: string;
  canContinue: boolean;
  onSignalObfuscationChange: (checked: boolean) => void;
  onContinue: () => void;
}

export function PatientFolderMediaStep({
  eegCount,
  videoCount,
  signalObfuscation,
  signalDescription,
  canContinue,
  onSignalObfuscationChange,
  onContinue,
}: PatientFolderMediaStepProps) {
  return (
    <section className="mt-6 space-y-5" aria-label="Media and privacy">
      <div className="grid items-stretch gap-5 lg:grid-cols-2">
        <section
          className="panel p-5 sm:p-6"
          aria-labelledby="eeg-recordings-heading"
          role="region"
        >
          <p className="eyebrow">EEG input</p>
          <h2
            id="eeg-recordings-heading"
            className="mt-2 text-lg font-bold text-ink"
          >
            {eegCount} {eegCount === 1 ? "EEG recording" : "EEG recordings"}
          </h2>
          <p className="mt-2 text-sm leading-6 text-ink-muted">
            Every supported EEG recording in this folder is included
            automatically and analyzed independently.
          </p>
        </section>

        <section
          className="panel p-5 sm:p-6"
          aria-labelledby="video-processing-heading"
          role="region"
        >
          <p className="eyebrow">Video input</p>
          <h2
            id="video-processing-heading"
            className="mt-2 text-lg font-bold text-ink"
          >
            Video processing
          </h2>
          <p className="mt-2 text-sm font-semibold text-ink">
            {videoCount} video clips included automatically
          </p>
          <p className="mt-2 text-sm leading-6 text-ink-muted">
            Full-frame blur runs before VSViG analysis. Audio is not analyzed.
            Original video and protected model-input files are deleted after
            processing; only encrypted prediction artifacts are retained.
          </p>
          <p className="mt-3 border-t border-rule pt-3 text-xs leading-5 text-ink-muted">
            Model output is research-only and is not a diagnosis.
          </p>
        </section>
      </div>

      <section
        className="panel border-l-4 border-l-teal border-teal/60 bg-teal-soft/40 p-5 sm:p-6"
        aria-labelledby="privacy-settings-heading"
        role="region"
      >
        <div className="flex items-start gap-3">
          <Icon name="shield" className="mt-0.5 size-6 text-teal" />
          <div className="min-w-0 flex-1">
            <p className="eyebrow text-teal-dark">Privacy first</p>
            <h2
              id="privacy-settings-heading"
              className="mt-1 text-lg font-bold text-ink"
            >
              Privacy settings
            </h2>
            <p className="mt-2 text-sm leading-6 text-ink-muted">
              Required metadata scrubbing is always applied. Video is fully
              blurred before analysis; signal obfuscation is the only optional
              privacy setting.
            </p>
            <label className="mt-4 flex cursor-pointer items-start gap-3 border-t border-teal/20 pt-4 text-sm text-ink">
              <input
                className="mt-1 size-4 accent-teal"
                type="checkbox"
                checked={signalObfuscation}
                onChange={(event) =>
                  onSignalObfuscationChange(event.target.checked)
                }
              />
              <span>
                <strong className="block">Signal obfuscation</strong>
                <span className="text-xs leading-5 text-ink-muted">
                  {signalDescription}
                </span>
              </span>
            </label>
          </div>
        </div>
      </section>

      <div className="flex justify-end border-t border-rule pt-5">
        <Button
          type="button"
          size="lg"
          disabled={!canContinue}
          onClick={onContinue}
        >
          Continue to patient details
          <Icon name="arrow" className="size-4" />
        </Button>
      </div>
    </section>
  );
}
