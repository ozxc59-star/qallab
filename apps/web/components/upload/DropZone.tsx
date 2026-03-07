"use client";

import { useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { useTranslations } from "next-intl";
import type { ConversionType } from "@/lib/validators";
import {
  MAX_FILE_SIZE_BYTES,
  getAcceptedFileTypes,
  validateFileClient,
  formatFileSize,
  isFileSizeInMB,
} from "@/lib/validators";

interface DropZoneProps {
  conversionType: ConversionType;
  onFileSelected: (file: File) => void;
  onError: (errorKey: string) => void;
  disabled?: boolean;
}

export default function DropZone({
  conversionType,
  onFileSelected,
  onError,
  disabled = false,
}: DropZoneProps) {
  const t = useTranslations("upload");

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      if (acceptedFiles.length === 0) return;

      const file = acceptedFiles[0];
      const result = validateFileClient(file, conversionType);

      if (!result.valid) {
        onError(result.error!);
        return;
      }

      onFileSelected(file);
    },
    [conversionType, onFileSelected, onError]
  );

  const { getRootProps, getInputProps, isDragActive, isDragAccept } =
    useDropzone({
      onDrop,
      accept: getAcceptedFileTypes(conversionType),
      maxSize: MAX_FILE_SIZE_BYTES,
      multiple: false,
      disabled,
      onDropRejected: (rejections) => {
        const error = rejections[0]?.errors[0];
        if (error?.code === "file-too-large") {
          onError("fileTooLarge");
        } else {
          onError("invalidFileType");
        }
      },
    });

  return (
    <div
      {...getRootProps()}
      className={`
        relative border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer
        transition-all duration-200
        ${disabled ? "opacity-50 cursor-not-allowed" : ""}
        ${
          isDragActive
            ? "border-brand-500 bg-brand-50"
            : "border-gray-300 hover:border-brand-400 hover:bg-surface-subtle"
        }
        ${isDragAccept ? "border-green-500 bg-green-50" : ""}
      `}
    >
      <input {...getInputProps()} />

      {/* Upload icon */}
      <div className="mx-auto mb-4 w-16 h-16 rounded-full bg-brand-100 flex items-center justify-center">
        <svg
          className="w-8 h-8 text-brand-600"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={1.5}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5"
          />
        </svg>
      </div>

      <p className="text-lg font-semibold text-gray-700 mb-2">
        {isDragActive ? t("dropzone.active") : t("dropzone.idle")}
      </p>

      <p className="text-sm text-gray-500 mb-1">{t("supportedFormats")}</p>
      <p className="text-sm text-gray-400">{t("maxSize")}</p>
    </div>
  );
}
