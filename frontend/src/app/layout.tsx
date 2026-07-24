import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "@/components/layout/Sidebar";
import Providers from "@/components/Providers";

export const metadata: Metadata = {
  title: "Scrappers Dashboard — Multi-Platform Data Intelligence",
  description:
    "Professional all-in-one business data scraper. Crawl websites, Google Maps, Instagram, LinkedIn, and Facebook with a single URL.",
  keywords: "scraper, data extraction, business intelligence, google maps, instagram, linkedin",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body>
        <Providers>
          <div className="app-layout">
            <Sidebar />
            <main className="main-content">{children}</main>
          </div>
        </Providers>
      </body>
    </html>
  );
}
