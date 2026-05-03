"use client";

/**
 * SecureBank AI — banking demo main page.
 *
 * Layout
 * ------
 * Left sidebar (fixed ~288px):
 *   • App branding
 *   • "Login as" user selector (Alice / Bob / Charlie)
 *   • Selected user's account card (balance + recent transactions)
 *
 * Right main area (flex-1):
 *   • BankingChatInterface — scoped per-user conversation
 *
 * Security model (displayed as pills):
 *   • user_id is part of the HMAC-signed payload — browser can't tamper with it
 *   • [BANKING_AUTH:...] tag is injected server-side by BankingChatController
 *   • Transfer Agent enforces authenticated_user at tool level
 */

import { useEffect, useState } from "react";
import { Shield, Lock, Sparkles } from "lucide-react";
import { UserSelector, type AccountSummary } from "@/components/UserSelector";
import { AccountCard } from "@/components/AccountCard";
import { BankingChatInterface } from "@/components/BankingChatInterface";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function Home() {
  const [accounts, setAccounts] = useState<AccountSummary[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/banking/accounts")
      .then((r) => r.json())
      .then((data) => {
        if (data.accounts) {
          setAccounts(data.accounts as AccountSummary[]);
          // Auto-select Alice as the default
          setSelectedUserId("alice");
        } else {
          setLoadError(data.error ?? "Failed to load accounts");
        }
      })
      .catch((err) => setLoadError(String(err)));
  }, []);

  const selectedAccount = accounts.find((a) => a.user_id === selectedUserId);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 dark:from-slate-950 dark:to-blue-950 flex flex-col">
      {/* ── Top header bar ─────────────────────────────────────────── */}
      <header className="flex-shrink-0 border-b border-border bg-card/80 backdrop-blur-sm px-4 py-3">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-primary" />
            <span className="font-bold text-base tracking-tight">SecureBank AI</span>
            <span className="hidden sm:inline text-xs text-muted-foreground ml-1">
              — Multi-agent banking demo
            </span>
          </div>

          {/* Security feature pills */}
          <div className="hidden md:flex items-center gap-2">
            <span className="inline-flex items-center gap-1 text-[10px] bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 rounded-full px-2.5 py-1">
              <Lock className="h-2.5 w-2.5" />
              HMAC-Signed Payloads
            </span>
            <span className="inline-flex items-center gap-1 text-[10px] bg-primary/10 text-primary rounded-full px-2.5 py-1">
              <Shield className="h-2.5 w-2.5" />
              Identity Guards
            </span>
            <span className="inline-flex items-center gap-1 text-[10px] bg-violet-500/10 text-violet-700 dark:text-violet-400 rounded-full px-2.5 py-1">
              <Sparkles className="h-2.5 w-2.5" />
              CRM + Transfer Agents
            </span>
          </div>
        </div>
      </header>

      {/* ── Main body ───────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col lg:flex-row overflow-hidden max-w-7xl w-full mx-auto p-4 gap-4">

        {/* Left sidebar */}
        <aside className="flex-shrink-0 w-full lg:w-72 flex flex-col gap-4">
          {/* User selector */}
          <Card className="shadow-sm">
            <CardHeader className="pb-2 pt-4 px-4">
              <CardTitle className="text-sm text-muted-foreground font-medium">
                Login as
              </CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4">
              {loadError ? (
                <p className="text-xs text-destructive">{loadError}</p>
              ) : accounts.length === 0 ? (
                <div className="space-y-2">
                  {[1, 2, 3].map((i) => (
                    <div
                      key={i}
                      className="h-16 rounded-xl bg-muted animate-pulse"
                    />
                  ))}
                </div>
              ) : (
                <UserSelector
                  accounts={accounts}
                  selectedUserId={selectedUserId}
                  onSelect={setSelectedUserId}
                />
              )}
            </CardContent>
          </Card>

          {/* Account detail */}
          {selectedUserId && (
            <Card className="shadow-sm flex-shrink-0">
              <CardContent className="p-4">
                <AccountCard userId={selectedUserId} />
              </CardContent>
            </Card>
          )}

          {/* Architecture notes (desktop only) */}
          <div className="hidden lg:block space-y-2 text-xs text-muted-foreground">
            <div className="rounded-lg p-3 border border-border bg-card">
              <p className="font-semibold text-foreground mb-1">Identity Spoofing Test</p>
              <p>
                Login as <strong>Charlie</strong> and ask the agent to transfer funds
                as <strong>Bob</strong>. The CRM agent will refuse — the signed
                payload locks the identity server-side.
              </p>
            </div>
            <div className="rounded-lg p-3 border border-border bg-card">
              <p className="font-semibold text-foreground mb-1">Agent Delegation</p>
              <p>
                The CRM Agent delegates fund transfers to a back-office
                Transfer Agent, always forwarding the verified
                <code className="font-mono text-[10px] mx-0.5">authenticated_user</code>
                so the Transfer Agent can't be bypassed either.
              </p>
            </div>
          </div>
        </aside>

        {/* Right panel — chat */}
        <main className="flex-1 flex flex-col min-h-0">
          <Card className="flex-1 shadow-sm flex flex-col min-h-0 overflow-hidden">
            <CardHeader className="flex-shrink-0 pb-0 px-4 pt-4 border-b border-border">
              <div className="flex items-center justify-between pb-3">
                <div>
                  <CardTitle className="text-base">
                    Banking Assistant
                  </CardTitle>
                  {selectedAccount && (
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Logged in as{" "}
                      <span
                        className="font-semibold"
                        style={{ color: selectedAccount.avatar_color }}
                      >
                        {selectedAccount.name}
                      </span>
                    </p>
                  )}
                </div>
                {selectedAccount && (
                  <div
                    className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0"
                    style={{ backgroundColor: selectedAccount.avatar_color }}
                  >
                    {selectedAccount.name
                      .split(" ")
                      .map((p) => p[0])
                      .join("")
                      .toUpperCase()
                      .slice(0, 2)}
                  </div>
                )}
              </div>
            </CardHeader>

            <CardContent className="flex-1 p-0 min-h-0 overflow-hidden">
              {selectedUserId && selectedAccount ? (
                <div className="h-full" style={{ minHeight: "400px" }}>
                  <BankingChatInterface
                    key={selectedUserId}
                    userId={selectedUserId}
                    userName={selectedAccount.name.split(" ")[0]}
                  />
                </div>
              ) : (
                <div className="flex items-center justify-center h-full min-h-[300px] text-muted-foreground text-sm">
                  Select a user on the left to start banking
                </div>
              )}
            </CardContent>
          </Card>
        </main>
      </div>
    </div>
  );
}
