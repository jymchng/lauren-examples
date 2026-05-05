"use client";

/**
 * BankingChatInterface — agentic banking chat backed by BankingCRMAgent.
 *
 * Differences from the general ChatInterface:
 * - Sends to `/api/banking/chat` (HMAC-signed by the server-side proxy).
 * - Includes `user_id` and `conversation_id` in the payload.
 * - Resets history and generates a new conversation_id when `userId` changes
 *   so each user gets an isolated conversation.
 * - SSE events are identical: `token`, `done`, `error`.
 */

import { useRef, useState, useCallback, useEffect } from "react";
import { SendHorizonal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { MessageBubble, type Message } from "@/components/MessageBubble";
import { StreamingMessage } from "@/components/StreamingMessage";
import { generateId } from "@/lib/uuid";

function parseSSEChunk(chunk: string): Array<{ event: string; data: string }> {
  const events: Array<{ event: string; data: string }> = [];
  let currentEvent = "";
  let currentData = "";

  for (const line of chunk.split("\n")) {
    if (line.startsWith("event: ")) {
      currentEvent = line.slice(7).trim();
    } else if (line.startsWith("data: ")) {
      currentData += (currentData ? "\n" : "") + line.slice(6);
    } else if (line === "" && (currentEvent || currentData)) {
      events.push({ event: currentEvent, data: currentData });
      currentEvent = "";
      currentData = "";
    }
  }
  return events;
}

interface BankingChatInterfaceProps {
  userId: string;
  userName: string;
  onComplete?: () => void;
}

const SUGGESTIONS = [
  "What's my current balance?",
  "Show me my recent transactions.",
  "Transfer $100 to Bob.",
  "What's the account ID for my account?",
];

export function BankingChatInterface({ userId, userName, onComplete }: BankingChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [conversationId] = useState(() => generateId());
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const prevUserIdRef = useRef(userId);

  // Reset conversation when user switches
  useEffect(() => {
    if (prevUserIdRef.current !== userId) {
      prevUserIdRef.current = userId;
      setMessages([]);
      setInput("");
      setStreamingContent("");
      setError(null);
      setStreaming(false);
    }
  }, [userId]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, streamingContent]);

  const handleSubmit = useCallback(
    async (e: React.FormEvent, overrideText?: string) => {
      e.preventDefault();
      const text = (overrideText ?? input).trim();
      if (!text || streaming) return;

      setError(null);
      setInput("");
      if (inputRef.current) inputRef.current.style.height = "auto";

      const userMessage: Message = {
        id: generateId(),
        role: "user",
        content: text,
      };

      const updatedMessages = [...messages, userMessage];
      setMessages(updatedMessages);
      setStreaming(true);
      setStreamingContent("");

      try {
        const response = await fetch("/api/banking/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            messages: updatedMessages
              .filter((m) => m.role !== "system")
              .map(({ role, content }) => ({
                role,
                content,
              })),
            user_id: userId,
            conversation_id: conversationId,
          }),
        });

        if (!response.ok) {
          const text = await response.text();
          throw new Error(`${response.status}: ${text}`);
        }

        if (!response.body) throw new Error("No response body");

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let accumulated = "";
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          const parts = buffer.split("\n\n");
          buffer = parts.pop() ?? "";

          for (const part of parts) {
            const events = parseSSEChunk(part + "\n\n");
            for (const { event, data } of events) {
              if (event === "token") {
                accumulated += data;
                setStreamingContent(accumulated);
              } else if (event === "done") {
                const assistantMessage: Message = {
                  id: generateId(),
                  role: "assistant",
                  content: accumulated,
                };
                setMessages((prev) => [...prev, assistantMessage]);
                setStreamingContent("");
                setStreaming(false);
                return;
              } else if (event === "break") {
                // Flush the before-handoff agent's response, then inject
                // the agent-change divider. Order matters: response first,
                // divider second, so messages appear in the correct sequence.
                const msgs: Message[] = [];
                if (accumulated) {
                  msgs.push({ id: generateId(), role: "assistant", content: accumulated });
                }
                if (data) {
                  msgs.push({ id: generateId(), role: "system", content: data });
                }
                if (msgs.length) setMessages((prev) => [...prev, ...msgs]);
                setStreamingContent("");
                accumulated = "";
              } else if (event === "error") {
                throw new Error(data);
              }
            }
          }
        }

        if (accumulated) {
          setMessages((prev) => [
            ...prev,
            { id: generateId(), role: "assistant", content: accumulated },
          ]);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
        setMessages((prev) => [
          ...prev,
          {
            id: generateId(),
            role: "assistant",
            content: `⚠️ Error: ${err instanceof Error ? err.message : String(err)}`,
          },
        ]);
      } finally {
        setStreaming(false);
        setStreamingContent("");
        inputRef.current?.focus();
        onComplete?.();
      }
    },
    [input, messages, streaming, userId, conversationId, onComplete]
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as React.FormEvent);
    }
  };

  const handleTextareaInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`;
  };

  const isEmpty = messages.length === 0 && !streaming;

  return (
    <div className="flex flex-col h-full">
      {/* Message list */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto min-h-0 px-4 py-4">
        {isEmpty && (
          <div className="flex flex-col items-center justify-center min-h-[200px] gap-4">
            <p className="text-muted-foreground text-sm">
              Hi {userName}! How can I help you today?
            </p>
            <div className="flex flex-wrap justify-center gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={(e) => {
                    e.preventDefault();
                    handleSubmit(
                      { preventDefault: () => {} } as React.FormEvent,
                      s
                    );
                  }}
                  disabled={streaming}
                  className="text-xs px-3 py-1.5 rounded-full border border-border bg-card hover:bg-accent/50 text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {streaming && <StreamingMessage content={streamingContent} />}
      </div>

      {/* Error banner */}
      {error && (
        <div className="mx-4 mb-2 px-3 py-2 rounded-lg bg-destructive/10 text-destructive text-xs">
          {error}
        </div>
      )}

      {/* Input bar */}
      <div className="p-4 border-t border-border bg-card/50">
        <form onSubmit={handleSubmit} className="flex gap-2 items-end">
          <textarea
            ref={inputRef}
            value={input}
            onChange={handleTextareaInput}
            onKeyDown={handleKeyDown}
            placeholder={
              streaming
                ? "Waiting for response…"
                : "Ask about your balance, transfers, transactions…"
            }
            disabled={streaming}
            rows={1}
            className="flex-1 resize-none rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 overflow-y-auto"
            style={{ minHeight: "40px", maxHeight: "160px" }}
            autoFocus
          />
          <Button
            type="submit"
            size="icon"
            disabled={!input.trim() || streaming}
            aria-label="Send"
          >
            <SendHorizonal className="h-4 w-4" />
          </Button>
        </form>
        <p className="mt-1.5 text-[10px] text-muted-foreground text-center">
          Identity verified · Payloads signed with HMAC-SHA256
        </p>
      </div>
    </div>
  );
}
