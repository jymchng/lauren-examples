/**
 * Proxies GET /api/banking/accounts to the backend.
 * Returns all three accounts for the user-selector panel.
 */

import { NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/banking/accounts`, {
      cache: "no-store",
    });
    const data = await res.json();
    return NextResponse.json(data, {
      headers: { "Cache-Control": "no-store" },
    });
  } catch (err) {
    return NextResponse.json(
      { error: "Failed to reach backend", detail: String(err) },
      { status: 502 }
    );
  }
}
