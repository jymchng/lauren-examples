/**
 * generateId — returns a v4 UUID string.
 *
 * - Server-side (Node.js): uses `require("crypto").randomUUID()` which is
 *   always available regardless of protocol.
 * - Client-side secure context: delegates to `crypto.randomUUID()`.
 * - Client-side insecure context (plain HTTP dev): pure-JS RFC 4122 fallback
 *   so the app never crashes with "crypto.randomUUID is not a function".
 */
export function generateId(): string {
  // Node.js / Edge runtime
  if (typeof window === "undefined") {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    return require("crypto").randomUUID() as string;
  }
  // Browser secure context
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  // Browser insecure context fallback (RFC 4122 v4)
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}
