export const runtime = "edge";

import { useTranslations } from "next-intl";
import Link from "next/link";
import Hero from "@/components/landing/Hero";
import HowItWorks from "@/components/landing/HowItWorks";
import Features from "@/components/landing/Features";

export default function HomePage() {
  const t = useTranslations("landing");
  const tNav = useTranslations("nav");
  const tCommon = useTranslations("common");

  return (
    <div className="min-h-screen">
      {/* Navigation */}
      <nav className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-gray-100">
        <div className="max-w-6xl mx-auto px-4 flex items-center justify-between h-16">
          <Link href="/" className="text-2xl font-extrabold text-brand-600">
            {tCommon("appName")}
          </Link>

          <div className="flex items-center gap-6">
            <Link
              href="/convert"
              className="text-sm font-medium text-gray-600 hover:text-brand-600 transition-colors"
            >
              {tNav("convert")}
            </Link>
            <Link
              href="/pricing"
              className="text-sm font-medium text-gray-600 hover:text-brand-600 transition-colors"
            >
              {tNav("pricing")}
            </Link>
            <Link href="/convert" className="btn-primary text-sm py-2 px-4">
              {t("hero.cta")}
            </Link>
          </div>
        </div>
      </nav>

      {/* Landing sections */}
      <Hero />
      <HowItWorks />
      <Features />

      {/* Bottom CTA */}
      <section className="py-20 bg-gradient-to-b from-white to-brand-50">
        <div className="max-w-3xl mx-auto px-4 text-center">
          <h2 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
            {t("cta.title")}
          </h2>
          <p className="text-lg text-gray-600 mb-8">{t("cta.subtitle")}</p>
          <Link href="/convert" className="btn-primary text-lg px-8 py-4">
            {t("cta.button")}
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-gray-400 py-8">
        <div className="max-w-6xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-sm">
            &copy; {new Date().getFullYear()} {tCommon("appName")} — {t("footer.rights")}
          </p>
          <div className="flex gap-6 text-sm">
            <a href="#" className="hover:text-white transition-colors">
              {t("footer.privacy")}
            </a>
            <a href="#" className="hover:text-white transition-colors">
              {t("footer.terms")}
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
