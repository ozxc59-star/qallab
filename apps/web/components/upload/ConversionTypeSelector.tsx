"use client";

import { useTranslations } from "next-intl";
import type { ConversionType } from "@/lib/validators";

interface ConversionTypeSelectorProps {
  value: ConversionType;
  onChange: (type: ConversionType) => void;
  disabled?: boolean;
}

export default function ConversionTypeSelector({
  value,
  onChange,
  disabled = false,
}: ConversionTypeSelectorProps) {
  const t = useTranslations("conversionType");

  const options: { type: ConversionType; key: "pdfToWord" | "wordToPdf" }[] = [
    { type: "pdf-to-docx", key: "pdfToWord" },
    { type: "docx-to-pdf", key: "wordToPdf" },
  ];

  return (
    <div>
      <h3 className="text-lg font-semibold text-gray-800 mb-3">{t("title")}</h3>
      <div className="grid grid-cols-2 gap-3">
        {options.map(({ type, key }) => (
          <button
            key={type}
            onClick={() => onChange(type)}
            disabled={disabled}
            className={`
              p-4 rounded-xl border-2 text-start transition-all duration-200
              ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}
              ${
                value === type
                  ? "border-brand-500 bg-brand-50 shadow-sm"
                  : "border-gray-200 hover:border-brand-300 hover:bg-surface-subtle"
              }
            `}
          >
            <div className="flex items-center gap-3">
              {/* Arrow icon indicating direction */}
              <div
                className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 ${
                  value === type
                    ? "bg-brand-100 text-brand-600"
                    : "bg-gray-100 text-gray-400"
                }`}
              >
                {type === "pdf-to-docx" ? (
                  // PDF → Word icon
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
                      d="M7.5 21 3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5"
                    />
                  </svg>
                ) : (
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
                      d="M7.5 21 3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5"
                    />
                  </svg>
                )}
              </div>

              <div>
                <p className="font-semibold text-gray-800">{t(`${key}.label`)}</p>
                <p className="text-xs text-gray-500 mt-0.5">
                  {t(`${key}.description`)}
                </p>
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
