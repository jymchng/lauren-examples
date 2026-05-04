"use client";

/**
 * DemoInfoPanel — explains what the demo is about, its features, and
 * how the backend works behind the scenes.
 *
 * Shown in the left sidebar on desktop. Collapsible sections keep the
 * sidebar compact while surfacing all the relevant architecture details.
 */

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface SectionProps {
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}

function Section({ title, defaultOpen = false, children }: SectionProps) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="rounded-lg border border-border bg-card overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-3 py-2 text-xs font-semibold text-foreground hover:bg-muted/50 transition-colors"
      >
        {title}
        {open ? (
          <ChevronDown className="h-3 w-3 text-muted-foreground" />
        ) : (
          <ChevronRight className="h-3 w-3 text-muted-foreground" />
        )}
      </button>
      {open && (
        <div className="px-3 pb-3 pt-1 text-[11px] text-muted-foreground space-y-1.5 border-t border-border">
          {children}
        </div>
      )}
    </div>
  );
}

function Pill({ color, children }: { color: string; children: React.ReactNode }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-1.5 py-0.5 text-[10px] font-medium mr-1",
        color
      )}
    >
      {children}
    </span>
  );
}

export function DemoInfoPanel() {
  return (
    <div className="hidden lg:flex flex-col gap-2">
      {/* About */}
      <Section title="About this demo" defaultOpen>
        <p>
          <strong className="text-foreground">SecureBank AI</strong> demonstrates
          a secure, multi-agent banking assistant built with{" "}
          <strong className="text-foreground">Lauren AI</strong>.
        </p>
        <p>
          Three demo users — <span className="font-medium text-[#10b981]">Alice</span>,{" "}
          <span className="font-medium text-[#3b82f6]">Bob</span>, and{" "}
          <span className="font-medium text-[#f59e0b]">Charlie</span> — each have
          their own account, conversation history, and real-time event stream.
        </p>
      </Section>

      {/* Features */}
      <Section title="Features" defaultOpen>
        <ul className="space-y-1.5">
          <li>
            <Pill color="bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300">
              Multi-agent
            </Pill>
            A <strong className="text-foreground">CRM Agent</strong> handles
            conversation and delegates fund transfers to a separate{" "}
            <strong className="text-foreground">Transfer Agent</strong>.
          </li>
          <li>
            <Pill color="bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">
              Secure
            </Pill>
            Requests are <strong className="text-foreground">HMAC-SHA256 signed</strong>{" "}
            by the Next.js proxy — the browser never touches the secret key.
          </li>
          <li>
            <Pill color="bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
              Memory
            </Pill>
            Conversation history persists across requests via{" "}
            <code className="font-mono text-[10px]">InMemoryConversationStore</code>.
          </li>
          <li>
            <Pill color="bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
              Real-time
            </Pill>
            A WebSocket stream pushes live tool calls, token usage, and balance
            changes to the browser as they happen.
          </li>
        </ul>
      </Section>

      {/* How it works */}
      <Section title="How it works behind the scenes">
        <ol className="space-y-1.5 list-decimal list-inside">
          <li>
            Browser sends a message → Next.js proxy signs the body with{" "}
            <strong className="text-foreground">HMAC-SHA256</strong> and adds an{" "}
            <code className="font-mono text-[10px]">X-Signature</code> header.
          </li>
          <li>
            <strong className="text-foreground">SignatureGuard</strong> verifies
            the signature and pins the authenticated{" "}
            <code className="font-mono text-[10px]">user_id</code> to{" "}
            <code className="font-mono text-[10px]">request.state</code>.
          </li>
          <li>
            <strong className="text-foreground">BankingChatController</strong> sets
            a <code className="font-mono text-[10px]">ContextVar</code> and runs{" "}
            <code className="font-mono text-[10px]">AgentRunner.run()</code>.
          </li>
          <li>
            The <strong className="text-foreground">CRM Agent</strong> may delegate
            to the <strong className="text-foreground">Transfer Agent</strong> via
            a tool call. Both agents read identity from{" "}
            <code className="font-mono text-[10px]">ExecutionContext</code>,
            never from LLM-generated text.
          </li>
          <li>
            The <strong className="text-foreground">SignalBus</strong> emits events
            on every model/tool call →{" "}
            <strong className="text-foreground">EventForwarder</strong> routes
            them to the right WebSocket connection using the ContextVar value.
          </li>
          <li>
            After a transfer, <strong className="text-foreground">BankDatabase</strong>{" "}
            fires an async callback →{" "}
            <strong className="text-foreground">EventForwarder</strong> broadcasts
            updated balances to all connected clients.
          </li>
        </ol>
      </Section>

      {/* Try this */}
      <Section title="Try these prompts">
        <ul className="space-y-1.5">
          <li className="flex gap-1.5">
            <span className="text-muted-foreground/60">→</span>
            <span>
              <em>&ldquo;What&rsquo;s my balance?&rdquo;</em>
            </span>
          </li>
          <li className="flex gap-1.5">
            <span className="text-muted-foreground/60">→</span>
            <span>
              <em>&ldquo;Transfer $200 to Bob&rdquo;</em>{" "}
              — watch the live activity feed and Bob&rsquo;s balance update instantly.
            </span>
          </li>
          <li className="flex gap-1.5">
            <span className="text-muted-foreground/60">→</span>
            <span>
              <em>&ldquo;Show my last 5 transactions&rdquo;</em>
            </span>
          </li>
          <li className="flex gap-1.5">
            <span className="text-muted-foreground/60">→</span>
            <span>
              Login as <strong className="text-[#f59e0b]">Charlie</strong> and ask{" "}
              <em>&ldquo;Transfer $100 as Alice&rdquo;</em> — the guard rejects it.
            </span>
          </li>
        </ul>
      </Section>
    </div>
  );
}
