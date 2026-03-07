"use client";

import { useTranslations } from "next-intl";

interface ErrorDisplayProps {
  errorKey: string;
  onRetry?: () => void;
  onDismiss?: () => void;
}

export default function ErrorDisplay({
  errorKey,
  onRetry,
  onDismiss,
}: ErrorDisplayProps) {
  const t = useTranslations("errors");
  const tCommon = useTranslations("common");

  // Map errorKey to translation key, fallback to "general"
  const validKeys = [
    "general",
    "fileTooLarge",
    "invalidFileType",
    "uploadFailed",
    "conversionFailed",
    "downloadExpired",
    "networkError",
    "serverError",
    "jobNotFound",
    "corruptedFile",
    "passwordProtected",
    "emptyFile",
  ];

  const translationKey = validKeys.includes(errorKey) ? errorKey : "general";

  return (
    <div className="card border-red-200 bg-red-50 animate-fade-in">
      <div className="flex items-start gap-3">
        {/* Error icon */}
        <div className="shrink-0 w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
          <svg
            className="w-5 h-5 text-red-600"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z"
            />
          </svg>
        </div>

        <div className="flex-1">
          <h4 className="font-semibold text-red-800 mb-1">{tCommon("error")}</h4>
          <p className="text-sm text-red-700">{t(translationKey)}</p>
        </div>

        {onDismiss && (
          <button
            onClick={onDismiss}
            className="shrink-0 p-1 rounded-lg hover:bg-red-100 text-red-400 hover:text-red-600 transition-colors"
            aria-label={tCommon("close")}
          >
            <svg
              className="w-4 h-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6 18 18 6M6 6l12 12"
              />
            </svg>
          </button>
        )}
      </div>

      {onRetry && (
        <div className="mt-4 flex justify-end">
          <button
            onClick={onRetry}
            className="text-sm font-semibold text-red-700 hover:text-red-900 px-4 py-2 rounded-lg hover:bg-red-100 transition-colors"
          >
            {tCommon("retry")}
          </button>
        </div>
      )}
    </div>
  );
}
