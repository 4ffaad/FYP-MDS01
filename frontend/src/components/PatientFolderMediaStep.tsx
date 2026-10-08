"use client";

import { Button } from "@/components/ui/button";
import { Icon } from "./Icon";
import {
  PatientDetailsSummary,
  type PatientDetailDraft,
} from "./PatientDetailsEditor";

interface PatientFolderMediaStepProps {
  eegCount: number;
  videoCount: number;
  showVideoInput?: boolean;
  showPatientDetails?: boolean;
  patientDetails: PatientDetailDraft[];
  reportTruncated: boolean;
  reportMessage: string | null;
  reportReading: boolean;
  canContinue: boolean;
  onContinue: () => void;
}

export function PatientFolderMediaStep({
  eegCount,
  videoCount,
  showVideoInput = true,
  showPatientDetails = true,
  patientDetails,
  reportTruncated,
  reportMessage,
  reportReading,
  canContinue,
  onContinue,
}: PatientFolderMediaStepProps) {
  return (
    <section className="mt-6 min-w-0 space-y-5" aria-label="Media and privacy">
      <div
        className={`grid min-w-0 items-stretch gap-5 ${showVideoInput ? "lg:grid-cols-2" : "lg:grid-cols-1"}`}
      >
        <section
          className="panel min-w-0 p-5 sm:p-6"
          aria-labelledby="privacy-settings-heading"
        >
          <div className="flex items-start gap-3">
            <Icon name="shield" className="mt-0.5 size-6 text-teal" />
            <div className="min-w-0 flex-1">
              <p className="eyebrow text-teal-dark">EEG privacy</p>
              <h2
                id="privacy-settings-heading"
                className="mt-1 text-lg font-bold text-ink"
              >
                Privacy settings
              </h2>
              <p className="mt-2 text-sm font-semibold text-ink">
                {eegCount} EEG {eegCount === 1 ? "recording" : "recordings"}{" "}
                included automatically and analyzed independently
              </p>
              <p className="mt-2 text-sm leading-6 text-ink-muted">
                Original recordings are encrypted and retained until you delete
                the case. Model analysis uses the reviewed EEG channels without
                signal obfuscation.
              </p>
            </div>
          </div>
        </section>

        {showVideoInput && (
          <section
            className="panel min-w-0 p-5 sm:p-6"
            aria-labelledby="video-input-heading"
          >
            <p className="eyebrow">Video input</p>
            <h2
              id="video-input-heading"
              className="mt-2 text-lg font-bold text-ink"
            >
              Video input
            </h2>
            <p className="mt-2 text-sm font-semibold text-ink">
              {videoCount} {videoCount === 1 ? "video clip" : "video clips"}{" "}
              included automatically
            </p>
            <p className="mt-2 text-sm leading-6 text-ink-muted">
              Video is retained for unblurred, owner-only reference playback.
              Viewing does not require pose detection or video model inference.
            </p>
            <p className="mt-3 border-t border-rule pt-3 text-xs leading-5 text-ink-muted">
              Video model output is research-only and is not a diagnosis.
            </p>
          </section>
        )}
      </div>

      {showPatientDetails && (
        <PatientDetailsSummary
          fields={patientDetails}
          truncated={reportTruncated}
          reportMessage={reportMessage}
          reportReading={reportReading}
        />
      )}

      <div className="flex justify-end border-t border-rule pt-5">
        <Button
          type="button"
          size="lg"
          disabled={!canContinue}
          onClick={onContinue}
        >
          Start processing
          <Icon name="arrow" className="size-4" />
        </Button>
      </div>
    </section>
  );
}
