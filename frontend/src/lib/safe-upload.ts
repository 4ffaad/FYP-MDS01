const SUPPORTED_VIDEO_EXTENSIONS = new Set(["avi", "mp4", "mov", "webm"]);

/** Preserve video bytes while replacing patient-provided names before upload. */
export function prepareVideoUploadFile(file: File): File {
  const extension = file.name.split(".").pop()?.toLocaleLowerCase("en-US");
  const safeExtension = SUPPORTED_VIDEO_EXTENSIONS.has(extension ?? "")
    ? extension!
    : "avi";

  return new File([file], `video-source.${safeExtension}`, {
    type: file.type || "application/octet-stream",
    lastModified: 0,
  });
}
