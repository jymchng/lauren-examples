import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SecureBank AI — Banking Demo",
  description:
    "Multi-agent banking demo: CRM agent, Transfer agent, identity verification, and security safeguards built with Lauren AI.",
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
