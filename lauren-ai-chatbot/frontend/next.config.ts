import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // distDir is overridden per-run via NEXT_DIST_DIR so that a stale
  // root-owned dev-server process (which may be watching this config)
  // uses the default ".next" directory while fresh runs use an isolated dir.
  distDir: process.env.NEXT_DIST_DIR ?? ".next",
  serverRuntimeConfig: {
    backendUrl: process.env.BACKEND_URL ?? "http://localhost:8000",
    payloadSecret: process.env.PAYLOAD_SECRET ?? "",
  },
  // Allow the dev origin (localhost:3000) in CORS headers for all API routes
  // so that the browser can call the Next.js proxy from the same dev server.
  async headers() {
    return [
      {
        source: "/api/:path*",
        headers: [
          { key: "Access-Control-Allow-Origin", value: "http://localhost:3000" },
          { key: "Access-Control-Allow-Methods", value: "GET, POST, OPTIONS" },
          { key: "Access-Control-Allow-Headers", value: "Content-Type, X-Signature" },
        ],
      },
    ];
  },
};

export default nextConfig;
