"use client";

/**
 * LiveActivityFeed — real-time display of agent events streamed over WebSocket.
 *
 * Renders a scrollable list of the most recent events:
 * • tool_started / tool_complete  — which tool ran and how long it took
 *   (handoff_to tool calls are suppressed — agent_handoff provides richer context)
 * • agent_handoff                 — which agent handed off to which
 * • token_usage                   — tokens consumed and estimated cost
 * • run_complete                  — summary of the full agent run
 *
 * Balance-changed events are handled by the parent page (not shown here since
 * they update the AccountCard directly).
 */

import { useEffect, useRef } from "react";
import { Zap, Wrench, CheckCircle, XCircle, Activity, ArrowRight, Shield } from "lucide-react";
import { cn } from "@/lib/utils";
import type { WsEvent } from "@/hooks/useWebSocket";

export interface ActivityEntry {
  id: number;
  event: WsEvent;
  timestamp: number;
}

interface LiveActivityFeedProps {
  entries: ActivityEntry[];
  connected: boolean;
}

function formatCost(usd: number): string {
  if (usd < 0.001) return `$${(usd * 1000).toFixed(4)}m`;
  return `$${usd.toFixed(5)}`;
}

function formatToolName(raw: string): string {
  return raw.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function abbreviateAgent(name: string): string {
  return name
    .replace("Banking CRM Agent (Authenticated)", "Auth CRM")
    .replace("Banking CRM Agent (Public)", "Public CRM")
    .replace("Banking Transfer Agent", "Transfer")
    .replace("Banking Disputes Agent", "Disputes");
}

function EventRow({ entry }: { entry: ActivityEntry }) {
  const { event } = entry;

  if (event.type === "tool_started") {
    const name = String(event.tool_name);
    // Suppress noise:
    //   - handoff_to    → already shown via the richer agent_handoff event
    //   - check_authentication_tool → runs on every authenticated turn; would
    //     dominate the feed with 2 entries per turn (start + complete) for
    //     no useful signal.
    if (name === "handoff_to" || name === "check_authentication_tool") return null;
    return (
      <div className="flex items-center gap-2 py-1">
        <Wrench className="h-3 w-3 text-blue-500 flex-shrink-0" />
        <span className="text-[11px] text-muted-foreground">
          Calling{" "}
          <span className="font-medium text-foreground">
            {formatToolName(String(event.tool_name))}
          </span>
          &hellip;
        </span>
      </div>
    );
  }

  if (event.type === "tool_complete") {
    const name = String(event.tool_name);
    if (name === "handoff_to" || name === "check_authentication_tool") return null;
    const success = Boolean(event.success);
    const durationMs = Number(event.duration_ms);
    return (
      <div className="flex items-center gap-2 py-1">
        {success ? (
          <CheckCircle className="h-3 w-3 text-emerald-500 flex-shrink-0" />
        ) : (
          <XCircle className="h-3 w-3 text-red-500 flex-shrink-0" />
        )}
        <span className="text-[11px] text-muted-foreground">
          <span className="font-medium text-foreground">
            {formatToolName(String(event.tool_name))}
          </span>{" "}
          {success ? "done" : "failed"}{" "}
          <span className="tabular-nums">({durationMs}ms)</span>
          {!success && event.error != null && (
            <span className="text-red-500 ml-1">— {String(event.error)}</span>
          )}
        </span>
      </div>
    );
  }

  if (event.type === "token_usage") {
    const input = Number(event.input_tokens);
    const output = Number(event.output_tokens);
    const durationMs = Number(event.duration_ms);
    return (
      <div className="flex items-center gap-2 py-1">
        <Zap className="h-3 w-3 text-amber-500 flex-shrink-0" />
        <span className="text-[11px] text-muted-foreground">
          <span className="tabular-nums">
            {input}↑ {output}↓ tokens
          </span>{" "}
          &middot;{" "}
          <span className="font-medium text-foreground">
            {formatCost(Number(event.cost_usd))}
          </span>{" "}
          &middot;{" "}
          <span className="tabular-nums text-muted-foreground/70">
            {durationMs}ms
          </span>
        </span>
      </div>
    );
  }

  if (event.type === "run_complete") {
    const turns = Number(event.turns);
    return (
      <div className="flex items-center gap-2 py-1 border-t border-border/50 mt-0.5">
        <Activity className="h-3 w-3 text-violet-500 flex-shrink-0" />
        <span className="text-[11px] text-muted-foreground">
          Run complete &middot;{" "}
          <span className="tabular-nums">{turns} turns</span>{" "}
          &middot;{" "}
          <span className="font-medium text-foreground">
            {formatCost(Number(event.total_cost_usd))} total
          </span>
        </span>
      </div>
    );
  }

  if (event.type === "guardrail_triggered") {
    const agentName = event.agent_name ? String(event.agent_name) : null;
    return (
      <div className="flex items-center gap-2 py-1">
        <Shield className="h-3 w-3 text-orange-500 flex-shrink-0" />
        <span className="text-[11px] text-muted-foreground">
          <span className="font-medium text-orange-600 dark:text-orange-400">
            {String(event.guardrail_name)}
          </span>{" "}
          blocked off-topic response
          {agentName && (
            <>
              {" "}
              &middot;{" "}
              <span className="text-foreground/60">{agentName}</span>
            </>
          )}
        </span>
      </div>
    );
  }

  if (event.type === "agent_handoff") {
    const from = abbreviateAgent(String(event.from_agent));
    const to = abbreviateAgent(String(event.to_agent));
    return (
      <div className="flex items-center gap-2 py-1 border-t border-border/50 mt-0.5">
        <ArrowRight className="h-3 w-3 text-violet-500 flex-shrink-0" />
        <span className="text-[11px] text-muted-foreground">
          Handoff{" "}
          <span className="font-medium text-foreground">{from}</span>
          {" → "}
          <span className="font-medium text-foreground">{to}</span>
        </span>
      </div>
    );
  }

  return null;
}

export function LiveActivityFeed({
  entries,
  connected,
}: LiveActivityFeedProps) {
  const listRef = useRef<HTMLDivElement>(null);

  // Scroll the feed's own container — never the sidebar
  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [entries.length]);

  const visibleEntries = entries
    .filter((e) =>
      ["tool_started", "tool_complete", "token_usage", "run_complete", "agent_handoff", "guardrail_triggered"].includes(
        e.event.type
      )
    )
    .slice(-30);

  return (
    <div className="rounded-lg border border-border bg-card p-3">
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
          Live Activity
        </p>
        <span
          className={cn(
            "inline-flex items-center gap-1 text-[10px] rounded-full px-2 py-0.5",
            connected
              ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
              : "bg-muted text-muted-foreground"
          )}
        >
          <span
            className={cn(
              "w-1.5 h-1.5 rounded-full",
              connected ? "bg-emerald-500 animate-pulse" : "bg-muted-foreground"
            )}
          />
          {connected ? "Live" : "Offline"}
        </span>
      </div>

      {/* Event list */}
      <div ref={listRef} className="max-h-40 overflow-y-auto space-y-0.5">
        {visibleEntries.length === 0 ? (
          <p className="text-[11px] text-muted-foreground italic py-1">
            {connected ? "Waiting for activity…" : "Connect to see live events"}
          </p>
        ) : (
          visibleEntries.map((entry) => (
            <EventRow key={entry.id} entry={entry} />
          ))
        )}
      </div>
    </div>
  );
}
