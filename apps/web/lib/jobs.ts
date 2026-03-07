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

const JOB_TTL_SECONDS = 3600;
const JOB_PREFIX = "job:";

// ---------- Upstash Redis via raw REST fetch (no cache option issue) ----------

async function redisCommand(command: unknown[]): Promise<unknown> {
  const url = process.env.UPSTASH_REDIS_REST_URL;
  const token = process.env.UPSTASH_REDIS_REST_TOKEN;

  if (!url || !token) {
    throw new Error("Missing UPSTASH_REDIS_REST_URL or UPSTASH_REDIS_REST_TOKEN");
  }

  const res = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(command),
  });

  if (!res.ok) {
    throw new Error(`Redis error: ${res.status} ${await res.text()}`);
  }

  const data = await res.json() as { result: unknown };
  return data.result;
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
  await redisCommand(["SETEX", `${JOB_PREFIX}${id}`, JOB_TTL_SECONDS, JSON.stringify(job)]);
  return job;
}

export async function getJob(id: string): Promise<Job | null> {
  const raw = await redisCommand(["GET", `${JOB_PREFIX}${id}`]) as string | null;
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

  await redisCommand(["SETEX", `${JOB_PREFIX}${id}`, JOB_TTL_SECONDS, JSON.stringify(updated)]);
  return updated;
}
