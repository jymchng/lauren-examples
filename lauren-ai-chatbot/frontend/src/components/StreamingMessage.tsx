/**
 * StreamingMessage — shows a live typing indicator while the AI is streaming.
 *
 * Renders content as raw text (whitespace preserved) with a blinking cursor.
 * Markdown parsing and normalization are deliberately skipped during the
 * stream — re-parsing on every chunk is expensive and can produce flickery
 * intermediate states when partial text triggers spurious pattern matches.
 *
 * When the ``done`` SSE event arrives, ``BankingChatInterface`` finalizes
 * the accumulated text as an ``assistant`` ``Message`` and ``MessageBubble``
 * takes over rendering with full Markdown + normalization.
 */

import { cn } from "@/lib/utils";

interface StreamingMessageProps {
  content: string;
  toolHint?: string | null;
}

export function StreamingMessage({ content, toolHint }: StreamingMessageProps) {
  return (
    <div className="flex w-full mb-4 justify-start">
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary flex items-center justify-center text-primary-foreground text-xs font-bold mr-2 mt-1">
        AI
      </div>

      <div className="max-w-[75%] rounded-2xl rounded-bl-sm px-4 py-3 text-sm leading-relaxed bg-muted text-foreground/70 break-words whitespace-pre-wrap">
        {content ? (
          <>
            {content}
            {/* Blinking cursor */}
            <span
              className={cn(
                "inline-block w-0.5 h-4 bg-foreground ml-0.5 align-middle",
                "animate-pulse"
              )}
              aria-hidden
            />
            {toolHint && (
              <div className="mt-1 text-[11px] italic text-muted-foreground">
                {toolHint}…
              </div>
            )}
          </>
        ) : (
          <span className="text-muted-foreground italic text-xs">
            {toolHint ? `${toolHint}…` : "Thinking…"}
          </span>
        )}
      </div>
    </div>
  );
}
