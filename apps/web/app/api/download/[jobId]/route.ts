export const runtime = "edge";

import { NextRequest, NextResponse } from "next/server";
import { getJob } from "@/lib/jobs";
import { generatePresignedDownloadUrl } from "@/lib/r2";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ jobId: string }> }
) {
  const { jobId } = await params;
  const job = await getJob(jobId);

  if (!job) {
    return NextResponse.json({ error: "jobNotFound" }, { status: 404 });
  }

  if (job.status !== "done" || !job.r2Key) {
    return NextResponse.json({ error: "conversionFailed" }, { status: 400 });
  }

  const url = await generatePresignedDownloadUrl(job.r2Key, 3600);

  return NextResponse.json({
    url,
    fileName: job.outputFileName,
    expiresIn: 3600,
  });
}
