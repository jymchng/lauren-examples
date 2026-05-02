/**
 * StreamingMessage — shows a live typing indicator while the AI is streaming.
 *
 * Renders like a regular assistant bubble but appends an animated cursor
 * to the end of the content to indicate that more tokens are coming.
 */

import { cn } from "@/lib/utils";

interface StreamingMessageProps {
  content: string;
}

export function StreamingMessage({ content }: StreamingMessageProps) {
  return (
    <div className="flex w-full mb-4 justify-start">
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary flex items-center justify-center text-primary-foreground text-xs font-bold mr-2 mt-1">
        AI
      </div>

      <div className="max-w-[75%] rounded-2xl rounded-bl-sm px-4 py-3 text-sm leading-relaxed bg-muted text-foreground whitespace-pre-wrap break-words">
        {content || (
          <span className="text-muted-foreground italic text-xs">
            Thinking…
          </span>
        )}
        {/* Blinking cursor */}
        <span
          className={cn(
            "inline-block w-0.5 h-4 bg-foreground ml-0.5 align-middle",
            "animate-pulse"
          )}
          aria-hidden
        />
      </div>
    </div>
  );
}
