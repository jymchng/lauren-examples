/**
 * Public WebSocket token proxy — issues a guest WS token with no authentication.
 *
 * Any visitor (logged-in or not) can call this to get a token that connects
 * to the backend's __public__ WS channel, receiving agent activity events
 * (token_usage, tool_started, tool_complete, run_complete) for public sessions.
 *
 * No HMAC signing required — the backend endpoint has no SignatureGuard.
 */

import { NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function POST() {
  let backendResponse: Response;
  try {
    backendResponse = await fetch(`${BACKEND_URL}/api/banking/ws-token/public`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
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
