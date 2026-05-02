import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Lauren AI Chatbot",
  description:
    "Full-stack AI chatbot showcasing Lauren's SSE streaming, HMAC-signed payloads, guards, interceptors, and middlewares.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  );
}
