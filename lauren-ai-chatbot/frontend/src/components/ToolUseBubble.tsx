"use client";

/**
 * ToolUseBubble — small system-style pill rendered inline in the chat thread
 * to record that the agent invoked a tool.
 *
 * Inserted by `BankingChatInterface` whenever a `tool_use` SSE event arrives
 * for a non-routine tool (handoff_to_* and check_authentication_tool are
 * filtered out — see `bubbleLabelFor` in BankingChatInterface.tsx).  The
 * bubble lives in the persistent `messages` array so users can scroll back
 * and audit what the agent did.
 */

import { cn } from "@/lib/utils";

interface ToolUseBubbleProps {
  label: string;
}

export function ToolUseBubble({ label }: ToolUseBubbleProps) {
  return (
    <div className="flex w-full mb-3 justify-center">
      <div
        className={cn(
          "inline-flex items-center gap-2 px-3 py-1 rounded-full",
          "bg-card border border-border text-[11px] text-muted-foreground italic",
        )}
      >
        {label}
      </div>
    </div>
  );
}
