import { expect, test } from "@playwright/test";
import { classifyPatientFolder } from "@/lib/patient-folder";

function folderFile(path: string): File {
  const filename = path.split("/").pop() ?? path;
  const file = new File(["synthetic-fixture"], filename);
  Object.defineProperty(file, "webkitRelativePath", { value: path });
  return file;
}

test("keeps media folders with a report in a dedicated reports directory", () => {
  const result = classifyPatientFolder([
    folderFile("study/site/cohort/patient-a/reports/final.docx"),
    folderFile("study/site/cohort/patient-a/eeg/recording.e"),
    folderFile("study/site/cohort/patient-a/video/clip.avi"),
  ]);

  expect(result.errors).toEqual([]);
  expect(result.eegCandidates).toHaveLength(1);
  expect(result.videos).toHaveLength(1);
});
