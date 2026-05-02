/**
 * Next.js API route — signs the chat payload and proxies it to the Lauren backend.
 *
 * Why server-side signing?
 * -------------------------
 * The HMAC secret (`PAYLOAD_SECRET`) must never be exposed to the browser.
 * By routing all chat traffic through this Next.js server handler we can:
 *   1. Sign the payload with the shared secret.
 *   2. Forward the signed request to the Lauren backend.
 *   3. Stream the SSE response back to the browser transparently.
 *
 * The browser only ever talks to the Next.js origin (same-origin); it never
 * sees the backend URL or the signing secret.
 *
 * Signing algorithm
 * -----------------
 * HMAC-SHA256 over the raw JSON-serialised request body, hex-encoded.
 * The signature is sent in the `X-Signature` header.  The Lauren backend's
 * `SignatureGuard` verifies it before the handler runs.
 */

import { createHmac } from "crypto";
import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";
const PAYLOAD_SECRET = process.env.PAYLOAD_SECRET ?? "";

function signPayload(body: string): string {
  return createHmac("sha256", PAYLOAD_SECRET).update(body).digest("hex");
}

export async function POST(request: NextRequest) {
  // Read the request body once and keep it as a string so we can both sign it
  // and forward the exact same bytes (avoids JSON round-trip differences).
  const bodyText = await request.text();
  const signature = signPayload(bodyText);

  let backendResponse: Response;
  try {
    backendResponse = await fetch(`${BACKEND_URL}/api/agent/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Signature": signature,
      },
      body: bodyText,
      // Node 18+ fetch supports streaming; keep the connection open
      // @ts-expect-error -- Next.js extended fetch
      duplex: "half",
    });
  } catch (err) {
    return NextResponse.json(
      { error: "Failed to reach the Lauren backend", detail: String(err) },
      { status: 502 }
    );
  }

  if (!backendResponse.ok) {
    const detail = await backendResponse.text();
    return NextResponse.json(
      { error: "Backend error", detail },
      { status: backendResponse.status }
    );
  }

  // Stream the SSE response back to the browser.
  // We pass through the body stream directly — no buffering.
  return new Response(backendResponse.body, {
    status: 200,
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache",
      "X-Accel-Buffering": "no",
      Connection: "keep-alive",
    },
  });
}
