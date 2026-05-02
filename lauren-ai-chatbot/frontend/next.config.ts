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
};

export default nextConfig;
