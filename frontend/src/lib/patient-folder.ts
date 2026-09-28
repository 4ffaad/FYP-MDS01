import { Zip, ZipPassThrough } from "fflate";

export interface EegBundle {
  format: "nicolet-e" | "edf" | "nicolet-data";
  files: Array<{ file: File; archiveName: string }>;
}

export interface PatientFolderSelection {
  eeg: EegBundle | null;
  eegCandidates: EegBundle[];
  report: File | null;
  videos: File[];
  ignoredCount: number;
  errors: string[];
}

type FileParts = { directory: string; stem: string; extension: string };

const REPORT_EXTENSIONS = new Set(["doc", "docx"]);
const REPORT_DIRECTORY_NAMES = new Set(["report", "reports"]);
const VIDEO_EXTENSIONS = new Set(["avi", "mp4", "mov", "webm"]);
const MAX_ARCHIVE_BYTES = 2 * 1024 * 1024 * 1024 - 1024 * 1024;
const FIXED_ARCHIVE_TIME = new Date("2000-01-01T00:00:00.000Z");

function fileParts(file: File): FileParts {
  const relativePath = file.webkitRelativePath || file.name;
  const components = relativePath.replaceAll("\\", "/").split("/");
  const filename = (components.pop() ?? file.name).toLocaleLowerCase("en-US");
  const dot = filename.lastIndexOf(".");
  return {
    directory: components.join("/").toLocaleLowerCase("en-US"),
    stem: dot > 0 ? filename.slice(0, dot) : filename,
    extension: dot > 0 ? filename.slice(dot + 1) : "",
  };
}

function patientRootDirectory(report: File, partsByFile: Map<File, FileParts>) {
  const directories = (partsByFile.get(report)?.directory ?? "")
    .split("/")
    .filter(Boolean);
  const reportFolder = directories[directories.length - 1];
  const patientDirectories = REPORT_DIRECTORY_NAMES.has(reportFolder)
    ? directories.slice(0, -1)
    : directories;
  return patientDirectories.join("/");
}

function isWithinDirectory(directory: string, root: string): boolean {
  return directory === root || directory.startsWith(`${root}/`);
}

/** Classify one explicitly selected directory; filenames never establish modality pairing. */
export function classifyPatientFolder(files: File[]): PatientFolderSelection {
  const errors: string[] = [];
  const byExtension = new Map<string, File[]>();
  const partsByFile = new Map<File, FileParts>();
  for (const file of files) {
    const parts = fileParts(file);
    partsByFile.set(file, parts);
    const bucket = byExtension.get(parts.extension) ?? [];
    bucket.push(file);
    byExtension.set(parts.extension, bucket);
  }

  const reports = [...REPORT_EXTENSIONS].flatMap(
    (extension) => byExtension.get(extension) ?? [],
  );
  const videos = [...VIDEO_EXTENSIONS].flatMap(
    (extension) => byExtension.get(extension) ?? [],
  );
  if (reports.length !== 1) {
    errors.push(
      "Select exactly one supported report (.doc or .docx) in the patient folder.",
    );
  }

  const eegCandidates: EegBundle[] = [];
  for (const file of [
    ...(byExtension.get("e") ?? []),
    ...(byExtension.get("edf") ?? []),
    ...(byExtension.get("edf+") ?? []),
  ]) {
    const extension = partsByFile.get(file)?.extension;
    eegCandidates.push({
      format: extension === "e" ? "nicolet-e" : "edf",
      files: [
        {
          file,
          archiveName: extension === "e" ? "recording.e" : "recording.edf",
        },
      ],
    });
  }

  const headFiles = byExtension.get("head") ?? [];
  const dataFiles = byExtension.get("data") ?? [];
  for (const dataFile of dataFiles) {
    const dataParts = partsByFile.get(dataFile)!;
    const matchingHeaders = headFiles.filter((header) => {
      const headerParts = partsByFile.get(header)!;
      return (
        headerParts.directory === dataParts.directory &&
        headerParts.stem === dataParts.stem
      );
    });
    if (matchingHeaders.length !== 1) {
      errors.push(
        "Each Nicolet .data file needs exactly one same-directory, same-base-name .head sidecar.",
      );
      continue;
    }
    eegCandidates.push({
      format: "nicolet-data",
      files: [
        { file: dataFile, archiveName: "recording.data" },
        { file: matchingHeaders[0], archiveName: "recording.head" },
      ],
    });
  }
  const pairedHeaders = new Set(
    eegCandidates.flatMap((candidate) =>
      candidate.files
        .filter((entry) => entry.archiveName === "recording.head")
        .map((entry) => entry.file),
    ),
  );
  if (headFiles.some((header) => !pairedHeaders.has(header))) {
    errors.push(
      "A .head sidecar could not be paired by exact directory and base name.",
    );
  }
  if (reports.length === 1) {
    const patientRoot = patientRootDirectory(reports[0], partsByFile);
    const supportedFiles = [
      ...reports,
      ...videos,
      ...eegCandidates.flatMap((candidate) =>
        candidate.files.map((entry) => entry.file),
      ),
    ];
    if (
      supportedFiles.some(
        (file) =>
          !isWithinDirectory(
            partsByFile.get(file)?.directory ?? "",
            patientRoot,
          ),
      )
    ) {
      errors.push(
        "Supported files were found in more than one patient folder. Select one patient folder at a time.",
      );
    }
  }
  if (eegCandidates.length === 0) {
    errors.push(
      "Add one or more supported EEG recordings: .e, .edf/.edf+, or matched .data/.head pairs.",
    );
  }

  const recognized = new Set<File>([
    ...reports,
    ...videos,
    ...eegCandidates.flatMap((candidate) =>
      candidate.files.map((entry) => entry.file),
    ),
  ]);
  return {
    eeg: eegCandidates.length === 1 ? eegCandidates[0] : null,
    eegCandidates,
    report: reports.length === 1 ? reports[0] : null,
    videos,
    ignoredCount: files.filter((file) => !recognized.has(file)).length,
    errors,
  };
}

/** Build an EEG-only ZIP with neutral entry names and fixed timestamps. */
export async function buildEegArchive(
  bundle: EegBundle | EegBundle[],
  onProgress: (percent: number) => void = () => {},
): Promise<File> {
  const bundles = Array.isArray(bundle) ? bundle : [bundle];
  const entries = bundles.flatMap((source, index) =>
    source.files.map((entry) => {
      const extension = entry.archiveName.slice(
        entry.archiveName.lastIndexOf("."),
      );
      const name =
        bundles.length === 1
          ? `recording${extension}`
          : `recording-${String(index + 1).padStart(2, "0")}${extension}`;
      return { ...entry, archiveName: name };
    }),
  );
  if (bundles.length === 0 || entries.length === 0) {
    throw new Error("Select at least one EEG recording.");
  }
  const totalSize = entries.reduce(
    (total, entry) => total + entry.file.size,
    0,
  );
  if (totalSize <= 0 || totalSize > MAX_ARCHIVE_BYTES) {
    throw new Error("The selected EEG source exceeds the local archive limit.");
  }

  const output: BlobPart[] = [];
  let rejectArchive: ((reason?: unknown) => void) | undefined;
  let resolveArchive: ((archive: File) => void) | undefined;
  let settled = false;
  const completed = new Promise<File>((resolve, reject) => {
    resolveArchive = resolve;
    rejectArchive = reject;
  });
  const zip = new Zip((error, chunk, final) => {
    if (error) {
      if (!settled) {
        settled = true;
        rejectArchive?.(error);
      }
      return;
    }
    if (chunk) output.push(chunk);
    if (final && !settled) {
      settled = true;
      resolveArchive?.(
        new File(output, "eeg-source.zip", { type: "application/zip" }),
      );
    }
  });

  let bytesRead = 0;
  try {
    for (const entry of entries) {
      if (!entry.file.size)
        throw new Error("The selected EEG source is empty.");
      const zipEntry = new ZipPassThrough(entry.archiveName);
      zipEntry.mtime = FIXED_ARCHIVE_TIME;
      zip.add(zipEntry);
      const reader = entry.file.stream().getReader();
      try {
        for (;;) {
          const { done, value } = await reader.read();
          if (done) break;
          zipEntry.push(value);
          bytesRead += value.byteLength;
          onProgress(Math.min(99, Math.floor((bytesRead / totalSize) * 100)));
        }
        zipEntry.push(new Uint8Array(0), true);
      } finally {
        reader.releaseLock();
      }
    }
    zip.end();
    const archive = await completed;
    if (archive.size > MAX_ARCHIVE_BYTES) {
      throw new Error(
        "The generated EEG archive exceeds the local upload limit.",
      );
    }
    onProgress(100);
    return archive;
  } catch (error) {
    zip.terminate();
    if (!settled) {
      settled = true;
      rejectArchive?.(error);
    }
    throw error;
  }
}
