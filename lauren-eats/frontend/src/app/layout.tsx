import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Toaster } from "@/components/ui/toaster";
import { Providers } from "@/components/layout/providers";
import { Navigation } from "@/components/layout/navigation";
import { Footer } from "@/components/layout/footer";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Lauren Eats - AI-Powered Chinese Restaurant",
  description:
    "Where tradition meets innovation. Experience authentic Chinese cuisine, elevated by AI-powered personalization and modern culinary artistry.",
  keywords: [
    "Chinese restaurant",
    "AI dining",
    "Lauren Eats",
    "authentic Chinese cuisine",
    "smart dining",
    "restaurant reservations",
  ],
  authors: [{ name: "Lauren Eats" }],
  icons: {
    icon: "https://z-cdn.chatglm.cn/z-ai/static/logo.svg",
  },
  openGraph: {
    title: "Lauren Eats - AI-Powered Chinese Restaurant",
    description:
      "Where tradition meets innovation. Experience authentic Chinese cuisine, elevated by AI-powered personalization.",
    siteName: "Lauren Eats",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Lauren Eats - AI-Powered Chinese Restaurant",
    description:
      "Where tradition meets innovation. Experience authentic Chinese cuisine, elevated by AI-powered personalization.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-background text-foreground`}
      >
        <Providers>
          <div className="min-h-screen flex flex-col">
            <Navigation />
            <main className="flex-1 pt-16">{children}</main>
            <Footer />
          </div>
          <Toaster />
        </Providers>
      </body>
    </html>
  );
}
