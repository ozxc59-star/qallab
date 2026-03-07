// ---------- R2 (production) ----------

async function getR2Client() {
  const { S3Client } = await import("@aws-sdk/client-s3");
  return new S3Client({
    region: "auto",
    endpoint: `https://${process.env.R2_ACCOUNT_ID}.r2.cloudflarestorage.com`,
    credentials: {
      accessKeyId: process.env.R2_ACCESS_KEY_ID!,
      secretAccessKey: process.env.R2_SECRET_ACCESS_KEY!,
    },
  });
}

function getBucketName(): string {
  return process.env.R2_BUCKET_NAME!;
}

// ---------- Public API ----------

export async function uploadToR2(
  key: string,
  body: Buffer | Uint8Array,
  contentType: string
): Promise<void> {
  const { PutObjectCommand } = await import("@aws-sdk/client-s3");
  const client = await getR2Client();
  await client.send(
    new PutObjectCommand({
      Bucket: getBucketName(),
      Key: key,
      Body: body,
      ContentType: contentType,
      Metadata: { "uploaded-at": new Date().toISOString() },
    })
  );
}

export async function generatePresignedDownloadUrl(
  key: string,
  expiresInSeconds = 3600
): Promise<string> {
  const { GetObjectCommand } = await import("@aws-sdk/client-s3");
  const { getSignedUrl } = await import("@aws-sdk/s3-request-presigner");
  const client = await getR2Client();
  return getSignedUrl(
    client,
    new GetObjectCommand({ Bucket: getBucketName(), Key: key }),
    { expiresIn: expiresInSeconds }
  );
}

export async function deleteFromR2(key: string): Promise<void> {
  const { DeleteObjectCommand } = await import("@aws-sdk/client-s3");
  const client = await getR2Client();
  await client.send(
    new DeleteObjectCommand({ Bucket: getBucketName(), Key: key })
  );
}

export async function listOldObjects(olderThanMs: number): Promise<string[]> {
  const { ListObjectsV2Command } = await import("@aws-sdk/client-s3");
  const client = await getR2Client();
  const cutoff = new Date(Date.now() - olderThanMs);
  const response = await client.send(
    new ListObjectsV2Command({ Bucket: getBucketName() })
  );
  return (response.Contents ?? [])
    .filter((obj) => obj.LastModified && obj.LastModified < cutoff)
    .map((obj) => obj.Key!)
    .filter(Boolean);
}
