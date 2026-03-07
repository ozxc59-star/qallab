export const runtime = "edge";

import { useTranslations } from "next-intl";
import Link from "next/link";

export default function PricingPage() {
  const t = useTranslations("pricing");
  const tCommon = useTranslations("common");
  const tNav = useTranslations("nav");

  const plans = [
    {
      key: "free" as const,
      highlighted: false,
    },
    {
      key: "pro" as const,
      highlighted: true,
    },
    {
      key: "enterprise" as const,
      highlighted: false,
    },
  ];

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
              href="/convert"
              className="text-sm font-medium text-gray-600 hover:text-brand-600 transition-colors"
            >
              {tNav("convert")}
            </Link>
          </div>
        </div>
      </nav>

      <main className="max-w-5xl mx-auto px-4 py-16">
        <div className="text-center mb-16">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">{t("title")}</h1>
          <p className="text-lg text-gray-600">{t("subtitle")}</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {plans.map(({ key, highlighted }) => {
            const features = t.raw(`${key}.features`) as string[];
            const hasPrice = key !== "enterprise";
            const hasBadge = key === "pro";

            return (
              <div
                key={key}
                className={`relative card flex flex-col ${
                  highlighted
                    ? "border-brand-500 border-2 shadow-lg scale-105"
                    : ""
                }`}
              >
                {hasBadge && (
                  <div className="absolute -top-3 start-1/2 -translate-x-1/2">
                    <span className="badge bg-brand-600 text-white">
                      {t("pro.badge")}
                    </span>
                  </div>
                )}

                <div className="mb-6">
                  <h3 className="text-xl font-bold text-gray-900 mb-2">
                    {t(`${key}.name`)}
                  </h3>

                  {hasPrice ? (
                    <div className="flex items-baseline gap-1">
                      <span className="text-4xl font-extrabold text-gray-900">
                        <span className="ltr-text">{t(`${key}.price`)}</span>
                      </span>
                      <span className="text-gray-500">
                        {t(`${key}.currency`)} / {t(`${key}.period`)}
                      </span>
                    </div>
                  ) : (
                    <p className="text-2xl font-bold text-gray-900">
                      {t("enterprise.price")}
                    </p>
                  )}
                </div>

                <ul className="space-y-3 mb-8 flex-1">
                  {features.map((feature, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <svg
                        className="w-5 h-5 text-green-500 shrink-0 mt-0.5"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={2}
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="m4.5 12.75 6 6 9-13.5"
                        />
                      </svg>
                      <span className="text-sm text-gray-600">{feature}</span>
                    </li>
                  ))}
                </ul>

                <Link
                  href={key === "enterprise" ? "#" : "/convert"}
                  className={`w-full text-center py-3 px-4 rounded-xl font-semibold transition-all ${
                    highlighted
                      ? "btn-primary"
                      : "btn-secondary"
                  }`}
                >
                  {t(`${key}.cta`)}
                </Link>
              </div>
            );
          })}
        </div>
      </main>
    </div>
  );
}
