/**
 * WebSocket token proxy — issues a short-lived WS auth token for the given user.
 *
 * The browser calls this route (POST /api/banking/ws-token) with a JSON body
 * containing { user_id }.  This server-side handler signs the body with
 * HMAC-SHA256 and forwards it to the backend, which verifies the
 * signature via SignatureGuard and returns a short-lived token.
 *
 * The browser then uses that token as a query parameter when opening the
 * WebSocket connection: ws://backend/ws/banking?token=<token>
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
    backendResponse = await fetch(`${BACKEND_URL}/api/banking/ws-token`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Signature": signature,
      },
      body: bodyText,
    });
  } catch (err) {
    return NextResponse.json(
      { error: "Failed to reach the banking backend", detail: String(err) },
      { status: 502 }
    );
  }

  const data = await backendResponse.json();
  return NextResponse.json(data, { status: backendResponse.status });
}
