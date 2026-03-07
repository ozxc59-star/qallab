export const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB

export const ALLOWED_MIME_TYPES = {
  pdf: "application/pdf",
  docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  doc: "application/msword",
} as const;

export const ALLOWED_EXTENSIONS = [".pdf", ".docx", ".doc"] as const;

// Magic bytes for file validation (server-side)
export const MAGIC_BYTES = {
  pdf: [0x25, 0x50, 0x44, 0x46], // %PDF
  docx: [0x50, 0x4b, 0x03, 0x04], // PK (ZIP-based)
  doc: [0xd0, 0xcf, 0x11, 0xe0], // OLE Compound Document
} as const;

export type ConversionType = "pdf-to-docx" | "docx-to-pdf";

export interface FileValidationResult {
  valid: boolean;
  error?: string;
}

export function validateFileClient(
  file: File,
  conversionType: ConversionType
): FileValidationResult {
  if (file.size > MAX_FILE_SIZE_BYTES) {
    return { valid: false, error: "fileTooLarge" };
  }

  const extension = getFileExtension(file.name);

  if (conversionType === "pdf-to-docx" && extension !== ".pdf") {
    return { valid: false, error: "invalidFileType" };
  }

  if (
    conversionType === "docx-to-pdf" &&
    extension !== ".docx" &&
    extension !== ".doc"
  ) {
    return { valid: false, error: "invalidFileType" };
  }

  return { valid: true };
}

export function getFileExtension(filename: string): string {
  const ext = filename.lastIndexOf(".");
  if (ext === -1) return "";
  return filename.slice(ext).toLowerCase();
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024 * 1024) {
    const kb = bytes / 1024;
    return new Intl.NumberFormat("ar-u-nu-latn", {
      maximumFractionDigits: 1,
    }).format(kb);
  }
  const mb = bytes / (1024 * 1024);
  return new Intl.NumberFormat("ar-u-nu-latn", {
    maximumFractionDigits: 2,
  }).format(mb);
}

export function isFileSizeInMB(bytes: number): boolean {
  return bytes >= 1024 * 1024;
}

export function getAcceptedFileTypes(
  conversionType: ConversionType
): Record<string, string[]> {
  if (conversionType === "pdf-to-docx") {
    return { "application/pdf": [".pdf"] };
  }
  return {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
      [".docx"],
    "application/msword": [".doc"],
  };
}
