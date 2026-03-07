export const runtime = "edge";

import { NextRequest, NextResponse } from "next/server";
import { listOldObjects, deleteFromR2 } from "@/lib/r2";

const CRON_SECRET = process.env.CRON_SECRET;

export async function GET(request: NextRequest) {
  // Always require auth — deny by default if secret not configured
  const authHeader = request.headers.get("authorization");
  if (!CRON_SECRET || authHeader !== `Bearer ${CRON_SECRET}`) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const ONE_HOUR_MS = 60 * 60 * 1000;

  try {
    const oldKeys = await listOldObjects(ONE_HOUR_MS);

    let deleted = 0;
    for (const key of oldKeys) {
      await deleteFromR2(key);
      deleted++;
    }

    return NextResponse.json({
      success: true,
      deleted,
      timestamp: new Date().toISOString(),
    });
  } catch (err) {
    console.error("Cleanup cron failed:", err);
    return NextResponse.json({ error: "cleanup_failed" }, { status: 500 });
  }
}
