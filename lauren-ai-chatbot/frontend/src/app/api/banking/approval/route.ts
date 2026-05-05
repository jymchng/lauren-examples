/**
 * Approval proxy — signs the approval body with HMAC-SHA256 and forwards it
 * to the backend's POST /api/banking/approval endpoint.
 *
 * The backend's SignatureGuard verifies the signature before resolving the
 * pending asyncio.Future in ApprovalService.  This ensures the browser cannot
 * forge an approval without the server-held PAYLOAD_SECRET.
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
    backendResponse = await fetch(`${BACKEND_URL}/api/banking/approval`, {
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

  const data = await backendResponse.text();
  return new Response(data, {
    status: backendResponse.status,
    headers: { "Content-Type": "application/json" },
  });
}
