import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  /* config options here */
  typescript: {
    ignoreBuildErrors: true,
  },
  reactStrictMode: false,
  async rewrites() {
    // In development, proxy ``/api/*`` to the Python backend.  This
    // means the browser only needs port 3000 forwarded (the Next.js
    // dev server), not 8000 — which matters when the user is in a
    // remote dev environment (VS Code Server, Codespaces, etc.) where
    // the backend port is not exposed to the local browser.
    //
    // In production, ``NEXT_PUBLIC_BACKEND_URL`` is set on Netlify and
    // the frontend calls the backend URL directly (no proxy needed).
    if (process.env.NODE_ENV === "development") {
      const backend =
        process.env.BACKEND_URL || "http://localhost:8000";
      return [
        {
          source: "/api/:path*",
          destination: `${backend}/api/:path*`,
        },
      ];
    }
    return [];
  },
};

export default nextConfig;
