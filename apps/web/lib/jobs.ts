export type JobStatus =
  | "pending"
  | "uploading"
  | "converting"
  | "done"
  | "error";

export interface Job {
  id: string;
  status: JobStatus;
  conversionType: "pdf-to-docx" | "docx-to-pdf";
  originalFileName: string;
  outputFileName?: string;
  r2Key?: string;
  error?: string;
  createdAt: number;
  updatedAt: number;
}

const JOB_TTL_SECONDS = 3600; // 1 hour
const JOB_PREFIX = "job:";

// ---------- Redis (Upstash) ----------

async function getRedis() {
  if (
    !process.env.UPSTASH_REDIS_REST_URL ||
    !process.env.UPSTASH_REDIS_REST_TOKEN
  ) {
    throw new Error(
      "Missing UPSTASH_REDIS_REST_URL or UPSTASH_REDIS_REST_TOKEN"
    );
  }
  const { Redis } = await import("@upstash/redis");
  return new Redis({
    url: process.env.UPSTASH_REDIS_REST_URL,
    token: process.env.UPSTASH_REDIS_REST_TOKEN,
  });
}

// ---------- Public API ----------

export async function createJob(
  id: string,
  data: Omit<Job, "id" | "status" | "createdAt" | "updatedAt">
): Promise<Job> {
  const now = Date.now();
  const job: Job = {
    id,
    status: "pending",
    createdAt: now,
    updatedAt: now,
    ...data,
  };

  const redis = await getRedis();
  await redis.setex(`${JOB_PREFIX}${id}`, JOB_TTL_SECONDS, JSON.stringify(job));

  return job;
}

export async function getJob(id: string): Promise<Job | null> {
  const redis = await getRedis();
  const raw = await redis.get<string>(`${JOB_PREFIX}${id}`);
  if (!raw) return null;
  return typeof raw === "string" ? JSON.parse(raw) : raw;
}

export async function updateJob(
  id: string,
  updates: Partial<Omit<Job, "id" | "createdAt">>
): Promise<Job | null> {
  const existing = await getJob(id);
  if (!existing) return null;

  const updated: Job = {
    ...existing,
    ...updates,
    updatedAt: Date.now(),
  };

  const redis = await getRedis();
  await redis.setex(
    `${JOB_PREFIX}${id}`,
    JOB_TTL_SECONDS,
    JSON.stringify(updated)
  );

  return updated;
}
