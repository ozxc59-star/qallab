"use client";

import { useTranslations } from "next-intl";

interface DownloadCardProps {
  downloadUrl: string;
  fileName: string;
  onReset: () => void;
}

export default function DownloadCard({
  downloadUrl,
  fileName,
  onReset,
}: DownloadCardProps) {
  const t = useTranslations("conversion");

  return (
    <div className="card text-center animate-fade-in">
      {/* Success icon */}
      <div className="mx-auto mb-4 w-16 h-16 rounded-full bg-green-100 flex items-center justify-center">
        <svg
          className="w-8 h-8 text-green-600"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={1.5}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="m4.5 12.75 6 6 9-13.5"
          />
        </svg>
      </div>

      <h3 className="text-xl font-bold text-gray-800 mb-2">
        {t("downloadReady")}
      </h3>

      <p className="text-sm text-gray-500 mb-1">
        <span className="filename">{fileName}</span>
      </p>

      <p className="text-xs text-amber-600 mb-6">{t("expiryNotice")}</p>

      <div className="flex flex-col sm:flex-row gap-3 justify-center">
        <a
          href={downloadUrl}
          download={fileName}
          className="btn-primary inline-flex items-center justify-center gap-2"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3"
            />
          </svg>
          {t("downloadButton")}
        </a>

        <button onClick={onReset} className="btn-secondary">
          {t("convertAnother")}
        </button>
      </div>
    </div>
  );
}
