"use client";

import { useTranslations } from "next-intl";
import Link from "next/link";

export default function Hero() {
  const t = useTranslations("landing.hero");

  return (
    <section className="relative overflow-hidden py-20 sm:py-32">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-b from-brand-50 via-white to-transparent" />

      <div className="relative max-w-4xl mx-auto px-4 text-center">
        {/* Badge */}
        <div className="inline-block mb-6">
          <span className="badge bg-brand-100 text-brand-700">
            {t("badge")}
          </span>
        </div>

        {/* Headline */}
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-gray-900 leading-tight mb-6">
          {t("headline")}
        </h1>

        {/* Subheadline */}
        <p className="text-lg sm:text-xl text-gray-600 leading-arabic max-w-2xl mx-auto mb-10">
          {t("subheadline")}
        </p>

        {/* CTA buttons */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link href="/convert" className="btn-primary text-lg px-8 py-4">
            {t("cta")}
          </Link>
          <a href="#how-it-works" className="btn-secondary text-lg px-8 py-4">
            {t("secondaryCta")}
          </a>
        </div>

        {/* Trust badge */}
        <p className="mt-8 text-sm text-gray-400">{t("trustBadge")}</p>
      </div>
    </section>
  );
}
