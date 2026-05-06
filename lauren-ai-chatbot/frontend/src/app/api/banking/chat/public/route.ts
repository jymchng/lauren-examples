/**
 * Public banking chat proxy — signs the payload and streams the
 * UnauthenticatedCRMAgent response back to the browser.
 *
 * Used when the visitor is not logged in. No user_id is required.
 * The backend endpoint /api/banking/chat/public never applies
 * AuthenticatedUserGuard, so unauthenticated sessions are accepted.
 */

import { createHmac } from "crypto";
import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";
const PAYLOAD_SECRET = process.env.PAYLOAD_SECRET ?? "";

function signPayload(body: string): string {
  return createHmac("sha256", PAYLOAD_SECRET).update(body).digest("hex");
}

export async function POST(request: NextRequest) {
  const bodyText = await request.text();
  const signature = signPayload(bodyText);

  let backendResponse: Response;
  try {
    backendResponse = await fetch(`${BACKEND_URL}/api/banking/chat/public`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Signature": signature,
      },
      body: bodyText,
      // @ts-expect-error -- Next.js extended fetch
      duplex: "half",
    });
  } catch (err) {
    return NextResponse.json(
      { error: "Failed to reach the banking backend", detail: String(err) },
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
