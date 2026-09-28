import { spawnSync } from "node:child_process";
import { NextResponse } from "next/server";
import { extractPatientReportDraft } from "@/lib/report-extraction";

export const runtime = "nodejs";
const MAX_REPORT_BYTES = 5 * 1024 * 1024;
const MAX_REQUEST_BYTES = MAX_REPORT_BYTES + 64 * 1024;
const LOOPBACK_HOSTS = new Set(["localhost", "127.0.0.1", "::1"]);

function error(message: string, status: number) {
  return NextResponse.json(
    { detail: message },
    { status, headers: { "Cache-Control": "no-store" } },
  );
}

function isLocalSameOrigin(request: Request): boolean {
  try {
    const origin = request.headers.get("origin");
    const host = request.headers.get("host");
    if (!origin || !host) return false;
    const originUrl = new URL(origin);
    return (
      LOOPBACK_HOSTS.has(originUrl.hostname) &&
      originUrl.host === host &&
      originUrl.protocol === "http:"
    );
  } catch {
    return false;
  }
}

export async function POST(request: Request) {
  if (process.env.NODE_ENV !== "development" || !isLocalSameOrigin(request)) {
    return error(
      "Local report extraction is available only from the loopback research/demo UI.",
      403,
    );
  }
  if (process.platform !== "darwin") {
    return error(
      "Legacy Word extraction requires local macOS textutil. Convert the report locally or enter the approved fields manually.",
      501,
    );
  }

  const contentLength = Number(request.headers.get("content-length"));
  if (Number.isFinite(contentLength) && contentLength > MAX_REQUEST_BYTES) {
    return error("The report exceeds the local extraction size limit.", 413);
  }

  let form: FormData;
  try {
    const reader = request.body?.getReader();
    if (!reader) return error("Choose one readable .doc or .docx report.", 400);
    const chunks: Uint8Array[] = [];
    let totalBytes = 0;
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      totalBytes += value.byteLength;
      if (totalBytes > MAX_REQUEST_BYTES) {
        await reader.cancel();
        return error(
          "The report exceeds the local extraction size limit.",
          413,
        );
      }
      chunks.push(value);
    }
    const body = Buffer.concat(chunks.map((chunk) => Buffer.from(chunk)));
    const boundedRequest = new Request(request.url, {
      method: "POST",
      headers: request.headers,
      body: new Uint8Array(body),
    });
    form = await boundedRequest.formData();
  } catch {
    return error("Choose one readable .doc or .docx report.", 400);
  }
  const report = form.get("report");
  if (!(report instanceof File))
    return error("Choose one readable .doc or .docx report.", 400);
  const extension = report.name.toLocaleLowerCase("en-US").split(".").pop();
  if (extension !== "doc" && extension !== "docx") {
    return error(
      "Only .doc and .docx reports are supported for local draft extraction.",
      415,
    );
  }
  if (report.size <= 0 || report.size > MAX_REPORT_BYTES) {
    return error("The report must be non-empty and no larger than 5 MiB.", 413);
  }

  const result = spawnSync(
    "/usr/bin/textutil",
    ["-convert", "txt", "-stdout", "-stdin", "-strip"],
    {
      input: Buffer.from(await report.arrayBuffer()),
      encoding: "utf8",
      maxBuffer: 2 * 1024 * 1024,
      timeout: 15_000,
      env: {
        PATH: "/usr/bin:/bin",
        LANG: "en_US.UTF-8",
        NODE_ENV: "development",
      },
    },
  );
  if (
    result.error ||
    result.status !== 0 ||
    typeof result.stdout !== "string"
  ) {
    return error(
      "The report could not be read locally. Review the source and enter only the approved profile fields manually.",
      422,
    );
  }

  const draft = extractPatientReportDraft(result.stdout);
  return NextResponse.json(
    { draft, requiresHumanReview: true, stored: false },
    { headers: { "Cache-Control": "no-store", Pragma: "no-cache" } },
  );
}
