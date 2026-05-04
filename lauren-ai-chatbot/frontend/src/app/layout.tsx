import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SecureBank AI — Banking Demo",
  description:
    "Multi-agent banking demo: CRM agent, Transfer agent, identity verification, and security safeguards.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        {/* Blocking script: applies theme + font-size from localStorage before hydration (prevents FOUC) */}
        <script dangerouslySetInnerHTML={{ __html: `(function(){try{var t=localStorage.getItem('theme')||'system';if(t==='dark'||(t==='system'&&window.matchMedia('(prefers-color-scheme: dark)').matches)){document.documentElement.classList.add('dark')}var f=localStorage.getItem('fontSize');if(f)document.documentElement.setAttribute('data-font-size',f)}catch(e){}})();` }} />
        {children}
      </body>
    </html>
  );
}
