export const runtime = "edge";

import { NextRequest, NextResponse } from "next/server";
import { v4 as uuidv4 } from "uuid";
import { createJob, updateJob } from "@/lib/jobs";
import { MAX_FILE_SIZE_BYTES, MAGIC_BYTES } from "@/lib/validators";
import type { ConversionType } from "@/lib/validators";
import { getOptionalRequestContext } from "@cloudflare/next-on-pages";

const CONVERTER_URL = process.env.CONVERTER_SERVICE_URL;
const CONVERTER_API_KEY = process.env.CONVERTER_API_KEY;

const ALLOWED_CONVERSION_TYPES: ConversionType[] = [
  "pdf-to-docx",
  "docx-to-pdf",
];

function validateMagicBytes(
  buffer: Uint8Array,
  conversionType: ConversionType
): boolean {
  const check = (sig: readonly number[]) =>
    sig.every((byte, i) => buffer[i] === byte);

  if (conversionType === "pdf-to-docx") {
    return check(MAGIC_BYTES.pdf);
  }
  return check(MAGIC_BYTES.docx) || check(MAGIC_BYTES.doc);
}

function getOutputFileName(
  originalName: string,
  conversionType: ConversionType
): string {
  const base = originalName.replace(/\.[^/.]+$/, "");
  return conversionType === "pdf-to-docx" ? `${base}.docx` : `${base}.pdf`;
}

async function convertViaExternalService(
  jobId: string,
  conversionType: ConversionType,
  bytes: Uint8Array,
  fileType: string,
  fileName: string
) {
  await updateJob(jobId, { status: "converting" });

  const converterForm = new FormData();
  converterForm.append("job_id", jobId);
  converterForm.append("conversion_type", conversionType);
  converterForm.append(
    "file",
    new Blob([bytes as BlobPart], { type: fileType }),
    fileName
  );

  let response: Response;
  try {
    // 120 second timeout — covers cold starts on Render free tier
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 120_000);
    response = await fetch(`${CONVERTER_URL}/convert`, {
      method: "POST",
      headers: { "X-API-Key": CONVERTER_API_KEY! },
      body: converterForm,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
  } catch {
    await updateJob(jobId, { status: "error", error: "conversionFailed" });
    return;
  }

  let result: { success?: boolean; error?: string; output_key?: string };
  try {
    result = await response.json();
  } catch {
    await updateJob(jobId, { status: "error", error: "conversionFailed" });
    return;
  }

  if (!response.ok || !result.success) {
    await updateJob(jobId, {
      status: "error",
      error: result.error ?? "conversionFailed",
    });
    return;
  }

  await updateJob(jobId, { status: "done", r2Key: result.output_key });
}

export async function POST(request: NextRequest) {
  if (!CONVERTER_URL || !CONVERTER_API_KEY) {
    return NextResponse.json(
      { error: "Converter service not configured" },
      { status: 500 }
    );
  }

  let formData: FormData;
  try {
    formData = await request.formData();
  } catch {
    return NextResponse.json({ error: "general" }, { status: 400 });
  }

  const file = formData.get("file") as File | null;
  const conversionType = formData.get("conversionType") as ConversionType | null;

  if (!file || !conversionType) {
    return NextResponse.json({ error: "general" }, { status: 400 });
  }

  if (!ALLOWED_CONVERSION_TYPES.includes(conversionType)) {
    return NextResponse.json({ error: "invalidFileType" }, { status: 400 });
  }

  if (file.size > MAX_FILE_SIZE_BYTES) {
    return NextResponse.json({ error: "fileTooLarge" }, { status: 413 });
  }

  if (file.size === 0) {
    return NextResponse.json({ error: "emptyFile" }, { status: 400 });
  }

  const arrayBuffer = await file.arrayBuffer();
  const bytes = new Uint8Array(arrayBuffer);

  if (!validateMagicBytes(bytes, conversionType)) {
    return NextResponse.json({ error: "invalidFileType" }, { status: 400 });
  }

  const jobId = uuidv4();
  const outputFileName = getOutputFileName(file.name, conversionType);

  try {
    await createJob(jobId, {
      conversionType,
      originalFileName: file.name,
      outputFileName,
    });
  } catch {
    return NextResponse.json({ error: "general" }, { status: 500 });
  }

  // Use ctx.waitUntil() so Cloudflare Workers keeps the worker alive
  // until conversion completes (fire-and-forget doesn't work in edge runtime)
  const cfContext = getOptionalRequestContext();
  if (cfContext?.ctx?.waitUntil) {
    cfContext.ctx.waitUntil(
      convertViaExternalService(jobId, conversionType, bytes, file.type, file.name)
    );
  } else {
    // Fallback for local dev (Node.js runtime)
    convertViaExternalService(jobId, conversionType, bytes, file.type, file.name);
  }

  return NextResponse.json({ jobId }, { status: 202 });
}
