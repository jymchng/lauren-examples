import { NextRequest, NextResponse } from "next/server";

/**
 * Dev-only API proxy.
 *
 * In dev, the browser can only reach the Next.js dev server (port 3000
 * is forwarded from the remote dev environment), not the Python
 * backend (port 8000).  This middleware intercepts ``/api/*`` requests
 * before the internal Prisma-based route handlers and proxies them
 * to ``BACKEND_URL`` (defaulting to ``http://localhost:8000``) so the
 * browser only needs to know about the dev server's port.
 *
 * In production (``NODE_ENV !== "development"``) the middleware is a
 * no-op — ``NEXT_PUBLIC_BACKEND_URL`` is set in the Netlify env and
 * the browser calls the backend directly.
 */
export async function middleware(request: NextRequest) {
  if (process.env.NODE_ENV !== "development") {
    return NextResponse.next();
  }

  const backend = process.env.BACKEND_URL || "http://localhost:8000";
  const targetUrl = new URL(request.nextUrl.pathname, backend);
  targetUrl.search = request.nextUrl.search;

  const headers = new Headers(request.headers);
  // Strip the host header so the backend doesn't see the dev server's host.
  headers.delete("host");
  // Forward the original origin so the backend's CORS middleware can
  // echo it back in the response.
  const origin = request.headers.get("origin");
  if (origin) {
    headers.set("origin", origin);
  }

  try {
    const backendResponse = await fetch(targetUrl, {
      method: request.method,
      headers,
      body:
        request.method === "GET" || request.method === "HEAD"
          ? undefined
          : await request.arrayBuffer(),
      // @ts-expect-error -- duplex is required for streaming bodies.
      duplex: "half",
      redirect: "manual",
    });

    const responseHeaders = new Headers(backendResponse.headers);
    // Allow the browser to see SSE / chunked responses through the proxy.
    responseHeaders.delete("content-encoding");
    responseHeaders.delete("content-length");

    return new NextResponse(backendResponse.body, {
      status: backendResponse.status,
      statusText: backendResponse.statusText,
      headers: responseHeaders,
    });
  } catch (err) {
    console.error("[api-proxy] backend unreachable:", targetUrl, err);
    return NextResponse.json(
      {
        success: false,
        error: "Backend unreachable. Is the Python backend running?",
      },
      { status: 502 },
    );
  }
}

export const config = {
  matcher: "/api/:path*",
};
