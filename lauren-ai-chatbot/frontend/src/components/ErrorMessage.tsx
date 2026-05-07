"use client";

/**
 * ErrorMessage — friendly inline error bubble for chat-thread errors.
 *
 * Replaces the previous "⚠️ Error: <huge JSON dump>" assistant pseudo-message.
 * Renders a short summary (extracted from the raw error string) with a
 * Show details button that reveals the full payload in a scrollable
 * monospace panel.  Used for both SSE error events and fetch failures.
 */

import { useState } from "react";
import { AlertTriangle, ChevronDown, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface ErrorMessageProps {
  message: string;
}

/**
 * Extract a one-line summary from a raw error string.
 *
 * Backend errors arrive as either:
 *   - "422: {\"error\":\"Backend error\",\"detail\":\"{...nested JSON...}\"}"
 *   - a bare string like "LLM exploded"
 *   - a fetch network error message
 *
 * Try, in order: nested ``message`` field → top-level ``error`` field →
 * first line truncated.  Always returns something printable.
 */
function summarizeError(raw: string): string {
  // Look for a nested "message": "..." which is usually the most useful.
  const nestedMessage = raw.match(/"message"\s*:\s*"((?:\\.|[^"\\])+)"/);
  if (nestedMessage) {
    try {
      return JSON.parse(`"${nestedMessage[1]}"`);
    } catch {
      return nestedMessage[1];
    }
  }
  // Fall back to the top-level "error" field.
  const topError = raw.match(/"error"\s*:\s*"((?:\\.|[^"\\])+)"/);
  if (topError) {
    try {
      return JSON.parse(`"${topError[1]}"`);
    } catch {
      return topError[1];
    }
  }
  const firstLine = raw.split("\n")[0].trim();
  return firstLine.length > 140 ? firstLine.slice(0, 140) + "…" : firstLine;
}

export function ErrorMessage({ message }: ErrorMessageProps) {
  const [expanded, setExpanded] = useState(false);
  const summary = summarizeError(message);

  return (
    <div className="flex w-full mb-4 justify-start">
      <div
        className={cn(
          "flex-shrink-0 w-8 h-8 rounded-full mr-2 mt-1",
          "bg-destructive/10 flex items-center justify-center",
        )}
      >
        <AlertTriangle className="h-4 w-4 text-destructive" />
      </div>

      <div
        className={cn(
          "max-w-[75%] rounded-2xl rounded-bl-sm px-4 py-3 text-sm leading-relaxed break-words",
          "bg-destructive/5 border border-destructive/30",
        )}
      >
        <div className="font-medium text-destructive text-xs uppercase tracking-wide mb-1">
          Something went wrong
        </div>
        <div className="text-foreground/90 text-[13px]">{summary}</div>

        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          aria-expanded={expanded}
          className={cn(
            "mt-2 inline-flex items-center gap-1 text-[11px]",
            "text-muted-foreground hover:text-foreground transition-colors",
            "focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring rounded",
          )}
        >
          {expanded ? (
            <ChevronDown className="h-3 w-3" />
          ) : (
            <ChevronRight className="h-3 w-3" />
          )}
          {expanded ? "Hide details" : "Show details"}
        </button>

        {expanded && (
          <pre
            className={cn(
              "mt-2 max-h-48 overflow-y-auto p-2 rounded",
              "bg-card border border-border",
              "text-[10px] font-mono text-muted-foreground",
              "whitespace-pre-wrap break-all",
            )}
          >
            {message}
          </pre>
        )}
      </div>
    </div>
  );
}
