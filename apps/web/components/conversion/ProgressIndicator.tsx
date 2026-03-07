"use client";

import { useTranslations } from "next-intl";
import type { JobStatus } from "@/lib/jobs";

interface ProgressIndicatorProps {
  status: JobStatus;
}

const STAGES: { key: JobStatus; stageIndex: number }[] = [
  { key: "uploading", stageIndex: 0 },
  { key: "converting", stageIndex: 1 },
  { key: "done", stageIndex: 2 },
];

export default function ProgressIndicator({ status }: ProgressIndicatorProps) {
  const t = useTranslations("conversion");

  const currentStageIndex =
    STAGES.find((s) => s.key === status)?.stageIndex ?? 0;

  const stageLabels = [
    t("stages.uploading"),
    t("stages.converting"),
    t("stages.ready"),
  ];

  return (
    <div className="card animate-fade-in">
      <h3 className="text-lg font-semibold text-gray-800 mb-6">{t("title")}</h3>

      {/* Progress bar */}
      <div className="relative mb-8">
        <div className="h-2 bg-gray-200 rounded-full">
          <div
            className={`h-2 rounded-full transition-all duration-700 ease-out ${
              status === "done" ? "bg-green-500" : "bg-brand-500 progress-pulse"
            }`}
            style={{
              width:
                status === "done"
                  ? "100%"
                  : `${((currentStageIndex + 0.5) / 3) * 100}%`,
            }}
          />
        </div>
      </div>

      {/* Stage indicators */}
      <div className="flex justify-between">
        {stageLabels.map((label, i) => {
          const isActive = i === currentStageIndex && status !== "done";
          const isComplete = i < currentStageIndex || status === "done";

          return (
            <div key={i} className="flex flex-col items-center gap-2">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center transition-all duration-300 ${
                  isComplete
                    ? "bg-green-500 text-white"
                    : isActive
                      ? "bg-brand-500 text-white"
                      : "bg-gray-200 text-gray-400"
                }`}
              >
                {isComplete ? (
                  <svg
                    className="w-4 h-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={3}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="m4.5 12.75 6 6 9-13.5"
                    />
                  </svg>
                ) : isActive ? (
                  <div className="w-3 h-3 rounded-full bg-white animate-pulse" />
                ) : (
                  <span className="text-xs font-bold">{i + 1}</span>
                )}
              </div>
              <span
                className={`text-xs font-medium ${
                  isComplete
                    ? "text-green-600"
                    : isActive
                      ? "text-brand-600"
                      : "text-gray-400"
                }`}
              >
                {label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
