"use client";

/**
 * ChatInterface — the main chat UI component.
 *
 * Flow
 * ----
 * 1. User types a message and submits.
 * 2. We POST to the Next.js API route `/api/chat` with the conversation
 *    history.  The API route signs the payload with HMAC-SHA256 and proxies
 *    it to the Lauren backend.
 * 3. The response is an SSE stream.  We consume it with the Fetch streaming
 *    API (reading the response body as a `ReadableStream`).
 * 4. Each `token` event appends a token to the in-progress assistant message.
 * 5. A `done` event finalises the message.
 * 6. An `error` event shows an error in the assistant bubble.
 */

import { useRef, useState, useCallback, useEffect } from "react";
import { SendHorizonal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MessageBubble, type Message } from "@/components/MessageBubble";
import { StreamingMessage } from "@/components/StreamingMessage";

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

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, streamingContent]);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      const text = input.trim();
      if (!text || streaming) return;

      setError(null);
      setInput("");
      if (inputRef.current) inputRef.current.style.height = "auto";

      const userMessage: Message = {
        id: crypto.randomUUID(),
        role: "user",
        content: text,
      };

      const updatedMessages = [...messages, userMessage];
      setMessages(updatedMessages);
      setStreaming(true);
      setStreamingContent("");

      try {
        const response = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            messages: updatedMessages.map(({ role, content }) => ({
              role,
              content,
            })),
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

          // Process complete SSE events (terminated by \n\n)
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
                  id: crypto.randomUUID(),
                  role: "assistant",
                  content: accumulated,
                };
                setMessages((prev) => [...prev, assistantMessage]);
                setStreamingContent("");
                setStreaming(false);
                return;
              } else if (event === "error") {
                throw new Error(data);
              }
            }
          }
        }

        // Stream ended without a `done` event — finalise anyway
        if (accumulated) {
          setMessages((prev) => [
            ...prev,
            { id: crypto.randomUUID(), role: "assistant", content: accumulated },
          ]);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            content: `⚠️ Error: ${err instanceof Error ? err.message : String(err)}`,
          },
        ]);
      } finally {
        setStreaming(false);
        setStreamingContent("");
        inputRef.current?.focus();
      }
    },
    [input, messages, streaming]
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as React.FormEvent);
    }
  };

  const handleTextareaInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    // Auto-resize
    e.target.style.height = "auto";
    e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`;
  };

  return (
    <div className="flex flex-col h-full">
      {/* Message list */}
      <ScrollArea className="flex-1 px-4 py-4" ref={scrollRef as React.Ref<HTMLDivElement>}>
        {messages.length === 0 && !streaming && (
          <div className="flex h-full min-h-[300px] items-center justify-center text-muted-foreground text-sm">
            Send a message to start chatting
          </div>
        )}

        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {streaming && <StreamingMessage content={streamingContent} />}
      </ScrollArea>

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
            placeholder={streaming ? "Waiting for response…" : "Type a message… (Shift+Enter for new line)"}
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
          Powered by{" "}
          <span className="font-semibold">Lauren</span> (SSE streaming) ·
          Payloads signed with HMAC-SHA256
        </p>
      </div>
    </div>
  );
}
