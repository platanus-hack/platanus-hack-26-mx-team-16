import type { Metadata, Viewport } from "next";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getTranslations } from "next-intl/server";
import "./globals.css";
import { Albert_Sans, Alumni_Sans, Roboto_Mono } from "next/font/google";
import { SessionProvider } from "@/src/application/contexts/session";
import { QueryProvider } from "@/src/application/providers/query-provider";

import { ThemeProvider } from "@/src/presentation/common/theme-provider";

const albertSans = Albert_Sans({
  subsets: ["latin"],
  variable: "--font-albert-sans",
  display: "swap",
});
const alumniSans = Alumni_Sans({
  subsets: ["latin"],
  variable: "--font-alumni-sans",
  display: "swap",
});
const robotoMono = Roboto_Mono({
  subsets: ["latin"],
  variable: "--font-roboto-mono",
  display: "swap",
});

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("Metadata");
  const locale = await getLocale();
  const title = t("title");
  const description = t("description");

  return {
    metadataBase: new URL(
      process.env.NEXT_PUBLIC_APP_URL || "https://owliver.mx"
    ),
    title: {
      default: title,
      template: "%s | Owliver",
    },
    description,
    authors: [{ name: "Owliver" }],
    creator: "Owliver",
    publisher: "Owliver",
    openGraph: {
      type: "website",
      locale: locale === "es" ? "es_ES" : "en_US",
      url: "https://owliver.mx",
      title,
      description,
      siteName: "Owliver",
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
      creator: "@owliver",
    },
    robots: {
      index: true,
      follow: true,
      googleBot: {
        index: true,
        follow: true,
        "max-video-preview": -1,
        "max-image-preview": "large",
        "max-snippet": -1,
      },
    },
    icons: {
      icon: "/favicon.ico",
      shortcut: "/favicon.ico",
      apple: "/favicon.png",
    },
    manifest: "/manifest.json",
    appleWebApp: {
      capable: true,
      statusBarStyle: "default",
      title: "Owliver",
    },
  };
}

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const locale = await getLocale();

  return (
    <html
      lang={locale}
      className={`${albertSans.variable} ${alumniSans.variable} ${robotoMono.variable}`}
      suppressHydrationWarning
    >
      <body className="antialiased font-sans">
        <NextIntlClientProvider>
          <ThemeProvider
            attribute="class"
            defaultTheme="system"
            enableSystem
            disableTransitionOnChange
          >
            <QueryProvider>
              <SessionProvider>{children}</SessionProvider>
            </QueryProvider>
          </ThemeProvider>
        </NextIntlClientProvider>
      {/* impeccable-live-start */}
<script src="http://localhost:8400/live.js"></script>
{/* impeccable-live-end */}
</body>
    </html>
  );
}
