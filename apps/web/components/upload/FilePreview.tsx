"use client";

import { useTranslations } from "next-intl";
import { formatFileSize, isFileSizeInMB } from "@/lib/validators";

interface FilePreviewProps {
  file: File;
  onRemove: () => void;
}

export default function FilePreview({ file, onRemove }: FilePreviewProps) {
  const t = useTranslations("upload");

  const sizeFormatted = formatFileSize(file.size);
  const sizeLabel = isFileSizeInMB(file.size)
    ? t("fileSize", { size: sizeFormatted })
    : t("fileSizeKB", { size: sizeFormatted });

  const isPdf = file.name.toLowerCase().endsWith(".pdf");

  return (
    <div className="card flex items-center gap-4 animate-fade-in">
      {/* File type icon */}
      <div
        className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 ${
          isPdf ? "bg-red-100 text-red-600" : "bg-blue-100 text-blue-600"
        }`}
      >
        <svg
          className="w-6 h-6"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={1.5}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"
          />
        </svg>
      </div>

      {/* File info */}
      <div className="flex-1 min-w-0">
        <p className="font-semibold text-gray-800 truncate">
          <span className="filename">{file.name}</span>
        </p>
        <p className="text-sm text-gray-500">{sizeLabel}</p>
      </div>

      {/* Remove button */}
      <button
        onClick={onRemove}
        className="shrink-0 p-2 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-red-500 transition-colors"
        aria-label={t("removeFile")}
      >
        <svg
          className="w-5 h-5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={1.5}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M6 18 18 6M6 6l12 12"
          />
        </svg>
      </button>
    </div>
  );
}
