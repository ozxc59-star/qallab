export const runtime = "edge";

import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "قلّب — تحويل PDF وWord بالعربية",
  description:
    "أسرع وأدق أداة لتحويل ملفات PDF إلى Word والعكس. يدعم اللغة العربية والتشكيل والكشيدة.",
  keywords: ["تحويل PDF", "PDF إلى Word", "Word إلى PDF", "عربي", "قلّب"],
  openGraph: {
    title: "قلّب — تحويل PDF وWord بالعربية",
    description:
      "أسرع وأدق أداة لتحويل ملفات PDF إلى Word والعكس. يدعم اللغة العربية.",
    locale: "ar_SA",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ar" dir="rtl">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;500;600;700;800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="font-arabic bg-surface-muted min-h-screen">
        {children}
      </body>
    </html>
  );
}
