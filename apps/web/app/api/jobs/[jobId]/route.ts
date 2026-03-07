export const runtime = "edge";

import { NextRequest, NextResponse } from "next/server";
import { getJob } from "@/lib/jobs";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ jobId: string }> }
) {
  const { jobId } = await params;
  const job = await getJob(jobId);

  if (!job) {
    return NextResponse.json({ error: "jobNotFound" }, { status: 404 });
  }

  return NextResponse.json({
    id: job.id,
    status: job.status,
    conversionType: job.conversionType,
    originalFileName: job.originalFileName,
    outputFileName: job.outputFileName,
    error: job.error,
    createdAt: job.createdAt,
  });
}
