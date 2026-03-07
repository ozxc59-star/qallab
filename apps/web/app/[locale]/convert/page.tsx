"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import DropZone from "@/components/upload/DropZone";
import FilePreview from "@/components/upload/FilePreview";
import ConversionTypeSelector from "@/components/upload/ConversionTypeSelector";
import ProgressIndicator from "@/components/conversion/ProgressIndicator";
import DownloadCard from "@/components/conversion/DownloadCard";
import ErrorDisplay from "@/components/conversion/ErrorDisplay";
import type { ConversionType } from "@/lib/validators";
import type { JobStatus } from "@/lib/jobs";

type PageState = "idle" | "file-selected" | "converting" | "done" | "error";

export default function ConvertPage() {
  const t = useTranslations("conversion");
  const tCommon = useTranslations("common");
  const tNav = useTranslations("nav");

  const [pageState, setPageState] = useState<PageState>("idle");
  const [conversionType, setConversionType] =
    useState<ConversionType>("pdf-to-docx");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatus>("pending");
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [outputFileName, setOutputFileName] = useState<string>("");
  const [errorKey, setErrorKey] = useState<string>("general");

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Clean up polling on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const reset = useCallback(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    setPageState("idle");
    setSelectedFile(null);
    setJobId(null);
    setJobStatus("pending");
    setDownloadUrl(null);
    setOutputFileName("");
    setErrorKey("general");
  }, []);

  const handleFileSelected = useCallback((file: File) => {
    setSelectedFile(file);
    setPageState("file-selected");
    setErrorKey("general");
  }, []);

  const handleError = useCallback((key: string) => {
    setErrorKey(key);
    setPageState("error");
  }, []);

  const pollJobStatus = useCallback(
    (id: string) => {
      pollRef.current = setInterval(async () => {
        try {
          const res = await fetch(`/api/jobs/${id}`);
          if (!res.ok) {
            clearInterval(pollRef.current!);
            handleError("jobNotFound");
            return;
          }

          const data = await res.json();
          setJobStatus(data.status);

          if (data.status === "done") {
            clearInterval(pollRef.current!);

            // Get download URL
            const dlRes = await fetch(`/api/download/${id}`);
            if (dlRes.ok) {
              const dlData = await dlRes.json();
              setDownloadUrl(dlData.url);
              setOutputFileName(dlData.fileName || data.outputFileName);
              setPageState("done");
            } else {
              handleError("conversionFailed");
            }
          } else if (data.status === "error") {
            clearInterval(pollRef.current!);
            handleError(data.error || "conversionFailed");
          }
        } catch {
          clearInterval(pollRef.current!);
          handleError("networkError");
        }
      }, 1500);
    },
    [handleError]
  );

  const startConversion = useCallback(async () => {
    if (!selectedFile) return;

    setPageState("converting");
    setJobStatus("uploading");

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("conversionType", conversionType);

      const res = await fetch("/api/jobs", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        handleError(data.error || "uploadFailed");
        return;
      }

      const { jobId: id } = await res.json();
      setJobId(id);
      setJobStatus("converting");

      // Start polling
      pollJobStatus(id);
    } catch {
      handleError("networkError");
    }
  }, [selectedFile, conversionType, handleError, pollJobStatus]);

  return (
    <div className="min-h-screen bg-surface-muted">
      {/* Navigation */}
      <nav className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-gray-100">
        <div className="max-w-6xl mx-auto px-4 flex items-center justify-between h-16">
          <Link href="/" className="text-2xl font-extrabold text-brand-600">
            {tCommon("appName")}
          </Link>
          <div className="flex items-center gap-6">
            <Link
              href="/"
              className="text-sm font-medium text-gray-600 hover:text-brand-600 transition-colors"
            >
              {tNav("home")}
            </Link>
            <Link
              href="/pricing"
              className="text-sm font-medium text-gray-600 hover:text-brand-600 transition-colors"
            >
              {tNav("pricing")}
            </Link>
          </div>
        </div>
      </nav>

      {/* Main content */}
      <main className="max-w-2xl mx-auto px-4 py-12">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            {tCommon("tagline")}
          </h1>
        </div>

        <div className="space-y-6">
          {/* Conversion type selector — always visible */}
          {(pageState === "idle" || pageState === "file-selected") && (
            <ConversionTypeSelector
              value={conversionType}
              onChange={(type) => {
                setConversionType(type);
                // Reset file if conversion type changes
                if (selectedFile) {
                  setSelectedFile(null);
                  setPageState("idle");
                }
              }}
              disabled={false}
            />
          )}

          {/* Upload area */}
          {pageState === "idle" && (
            <DropZone
              conversionType={conversionType}
              onFileSelected={handleFileSelected}
              onError={handleError}
            />
          )}

          {/* File preview + start button */}
          {pageState === "file-selected" && selectedFile && (
            <>
              <FilePreview file={selectedFile} onRemove={reset} />

              {/* Scanned PDF warning for pdf-to-docx */}
              {conversionType === "pdf-to-docx" && (
                <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-700">
                  {t("scannedPdfWarning")}
                </div>
              )}

              <button onClick={startConversion} className="btn-primary w-full text-lg">
                {t("startButton")}
              </button>
            </>
          )}

          {/* Progress indicator */}
          {pageState === "converting" && (
            <ProgressIndicator status={jobStatus} />
          )}

          {/* Download card */}
          {pageState === "done" && downloadUrl && (
            <DownloadCard
              downloadUrl={downloadUrl}
              fileName={outputFileName}
              onReset={reset}
            />
          )}

          {/* Error display */}
          {pageState === "error" && (
            <ErrorDisplay
              errorKey={errorKey}
              onRetry={reset}
              onDismiss={reset}
            />
          )}
        </div>
      </main>
    </div>
  );
}
