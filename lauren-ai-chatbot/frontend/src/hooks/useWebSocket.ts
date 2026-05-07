"use client";

/**
 * useWebSocket — manages the banking WebSocket connection lifecycle.
 *
 * Flow:
 * 1. When userId changes, fetch a short-lived token from /api/banking/ws-token.
 * 2. Open a WebSocket to the backend at NEXT_PUBLIC_WS_URL/ws/banking?token=...
 * 3. Parse incoming JSON frames and dispatch them via onEvent.
 * 4. Close and re-connect when userId changes or the component unmounts.
 *
 * The hook does NOT auto-reconnect on unexpected disconnects to keep the
 * demo simple. Production code would add exponential back-off reconnection.
 */

import { useCallback, useEffect, useRef, useState } from "react";

export interface TransferApprovalRequest {
  type: "transfer_approval_request";
  approval_id: string;
  from_user: string;
  to_user: string;
  amount_usd: number;
  description: string;
  conversation_id: string;
  /** Epoch ms when the backend stamped the request. Used to drop stale prompts after a refresh / WS reconnect. */
  created_at?: number;
}

export interface AgentHandoffEvent {
  type: "agent_handoff";
  from_agent: string;
  to_agent: string;
  reason?: string;
  summary?: string;
}

export interface WsEvent {
  type:
    | "token_usage"
    | "tool_started"
    | "tool_complete"
    | "run_complete"
    | "balance_changed"
    | "transfer_approval_request"
    | "agent_handoff";
  [key: string]: unknown;
}

interface UseWebSocketOptions {
  userId: string | null;
  onEvent: (event: WsEvent) => void;
}

export interface UseWebSocketReturn {
  connected: boolean;
}

export function useWebSocket({
  userId,
  onEvent,
}: UseWebSocketOptions): UseWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  // Keep a stable ref to onEvent so the ws.onmessage closure never goes stale
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  const closeWs = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.onopen = null;
      wsRef.current.onclose = null;
      wsRef.current.onmessage = null;
      wsRef.current.onerror = null;
      wsRef.current.close();
      wsRef.current = null;
    }
    setConnected(false);
  }, []);

  const openWs = useCallback(
    (token: string) => {
      const wsBase =
        process.env.NEXT_PUBLIC_WS_URL ||
        (typeof window !== "undefined"
          ? `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.hostname}:8000`
          : "ws://localhost:8000");
      const ws = new WebSocket(
        `${wsBase}/ws/banking?token=${encodeURIComponent(token)}`
      );
      wsRef.current = ws;

      ws.onopen = () => setConnected(true);
      ws.onclose = () => setConnected(false);
      ws.onerror = (e) => console.warn("[WS] error:", e);
      ws.onmessage = (e) => {
        try {
          const evt = JSON.parse(e.data as string) as WsEvent;
          onEventRef.current(evt);
        } catch {
          // ignore malformed frames
        }
      };
    },
    []
  );

  const connect = useCallback(
    async (uid: string) => {
      closeWs();
      try {
        const resp = await fetch("/api/banking/ws-token", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ user_id: uid }),
        });
        if (!resp.ok) { console.warn("[WS] token fetch failed:", resp.status); return; }
        const data = await resp.json();
        if (!data.token) return;
        openWs(data.token);
      } catch (err) {
        console.warn("[WS] token fetch error:", err);
      }
    },
    [closeWs, openWs]
  );

  const connectPublic = useCallback(
    async () => {
      closeWs();
      try {
        const resp = await fetch("/api/banking/ws-token/public", { method: "POST" });
        if (!resp.ok) { console.warn("[WS] public token fetch failed:", resp.status); return; }
        const data = await resp.json();
        if (!data.token) return;
        openWs(data.token);
      } catch (err) {
        console.warn("[WS] public token fetch error:", err);
      }
    },
    [closeWs, openWs]
  );

  useEffect(() => {
    if (userId) {
      connect(userId);
    } else {
      connectPublic();
    }
    return closeWs;
  }, [userId, connect, connectPublic, closeWs]);

  return { connected };
}
