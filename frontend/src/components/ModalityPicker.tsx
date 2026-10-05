import { useState, type ChangeEvent, type RefObject } from "react";
import { Icon } from "./Icon";

type ModalityPickerProps = {
  id: string;
  headingLevel?: "h2" | "h3";
  title: string;
  eyebrow: "Required" | "Optional";
  description: string;
  accept: string;
  icon: "activity" | "video";
  busy: boolean;
  selected: boolean;
  selectedLabel: string;
  inputRef?: RefObject<HTMLInputElement | null>;
  onChange: (event: ChangeEvent<HTMLInputElement>) => void;
  onFile: (file: File) => void | Promise<void>;
};

export function ModalityPicker({
  id,
  headingLevel = "h2",
  title,
  eyebrow,
  description,
  accept,
  icon,
  busy,
  selected,
  selectedLabel,
  inputRef,
  onChange,
  onFile,
}: ModalityPickerProps) {
  const [dragging, setDragging] = useState(false);
  const Heading = headingLevel;

  return (
    <section
      className={`upload-lane glass-panel rounded-2xl border p-5 transition-all sm:p-6 ${selected ? "is-selected border-teal bg-teal-soft/35" : "border-rule bg-surface/80 hover:-translate-y-0.5 hover:border-teal/40"}`}
      aria-labelledby={`${id}-heading`}
    >
      <div className="flex items-start justify-between gap-4">
        <span className="grid size-12 shrink-0 place-items-center rounded-2xl bg-teal-soft text-teal-dark shadow-hard-sm">
          <Icon name={icon} className="size-6" />
        </span>
        <span className={`upload-badge ${selected ? "is-selected" : ""}`}>
          {selected ? "Ready" : eyebrow}
        </span>
      </div>
      <div className="mt-5 min-w-0">
        <Heading
          id={`${id}-heading`}
          className="text-lg font-bold tracking-tight"
        >
          {title}
        </Heading>
        <p id={`${id}-help`} className="mt-2 text-sm leading-6 text-ink-muted">
          {description}
        </p>
      </div>
      <label
        className={`upload-dropzone mt-6 flex min-h-36 cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed px-5 py-6 text-center outline-none transition-all focus-within:border-teal focus-within:ring-4 focus-within:ring-teal/20 ${dragging ? "is-dragging border-teal bg-teal-soft/60" : "border-rule-strong bg-surface-soft hover:border-teal hover:bg-teal-soft/35"}`}
        htmlFor={id}
        onDragEnter={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          const file = event.dataTransfer.files[0];
          if (file) void onFile(file);
        }}
      >
        <Icon
          name={busy ? "spinner" : selected ? "check" : "upload"}
          className={`size-7 text-teal ${busy ? "animate-spin" : selected ? "upload-check-pop" : ""}`}
          weight="bold"
        />
        <span className="mt-3 text-sm font-bold text-ink">
          {selected ? selectedLabel : "Drop here or browse"}
        </span>
        <span className="mt-1 text-xs text-ink-muted">
          {selected
            ? "Ready for the next step"
            : "Your local filename is not shown in the workspace"}
        </span>
        <input
          ref={inputRef}
          className="sr-only"
          id={id}
          aria-label={title}
          aria-describedby={`${id}-help`}
          type="file"
          accept={accept}
          onChange={onChange}
          disabled={busy}
        />
      </label>
    </section>
  );
}
