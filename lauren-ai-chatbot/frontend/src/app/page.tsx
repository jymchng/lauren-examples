"use client";

/**
 * SecureBank AI — banking demo main page.
 *
 * Layout
 * ------
 * Desktop (lg+):
 *   Left sidebar (fixed 288px) — user selector, account card, activity feed, info panel
 *   Right main area (flex-1)  — BankingChatInterface
 *
 * Mobile (< lg):
 *   Header with hamburger → slide-in sidebar drawer
 *   Compact user pill strip pinned below header
 *   Full-height chat beneath it
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { Shield, Lock, Sparkles, Zap, Menu, X } from "lucide-react";
import { UserSelector, type AccountSummary } from "@/components/UserSelector";
import { AccountCard } from "@/components/AccountCard";
import { BankingChatInterface } from "@/components/BankingChatInterface";
import { DemoInfoPanel } from "@/components/DemoInfoPanel";
import { LiveActivityFeed, type ActivityEntry } from "@/components/LiveActivityFeed";
import { SettingsPanel, type Theme, type FontSize } from "@/components/SettingsPanel";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useWebSocket, type WsEvent } from "@/hooks/useWebSocket";
import { cn } from "@/lib/utils";

function initials(name: string): string {
  return name.split(" ").map((p) => p[0]).join("").toUpperCase().slice(0, 2);
}

function formatBalance(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(amount);
}

export default function Home() {
  const [accounts, setAccounts] = useState<AccountSummary[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [accountRefreshKey, setAccountRefreshKey] = useState(0);

  const [liveBalances, setLiveBalances] = useState<Record<string, number>>({});
  const [activityEntries, setActivityEntries] = useState<ActivityEntry[]>([]);
  const activityCounterRef = useRef(0);

  // ── UI state ────────────────────────────────────────────────────────
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [theme, setTheme] = useState<Theme>("system");
  const [fontSize, setFontSize] = useState<FontSize>("md");
  const [settingsOpen, setSettingsOpen] = useState(false);

  // Load preferences from localStorage on mount
  useEffect(() => {
    const savedTheme = localStorage.getItem("theme") as Theme | null;
    if (savedTheme) setTheme(savedTheme);
    const savedFontSize = localStorage.getItem("fontSize") as FontSize | null;
    if (savedFontSize) setFontSize(savedFontSize);
  }, []);

  // Apply theme to <html>
  useEffect(() => {
    const root = document.documentElement;
    const applyDark = (dark: boolean) => root.classList.toggle("dark", dark);
    if (theme === "system") {
      const mq = window.matchMedia("(prefers-color-scheme: dark)");
      applyDark(mq.matches);
      const handler = (e: MediaQueryListEvent) => applyDark(e.matches);
      mq.addEventListener("change", handler);
      return () => mq.removeEventListener("change", handler);
    } else {
      applyDark(theme === "dark");
    }
  }, [theme]);

  // Apply font size to <html>
  useEffect(() => {
    document.documentElement.setAttribute("data-font-size", fontSize);
  }, [fontSize]);

  // Close mobile sidebar on Escape or viewport ≥ lg
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setSidebarOpen(false); };
    const onResize = () => { if (window.innerWidth >= 1024) setSidebarOpen(false); };
    document.addEventListener("keydown", onKey);
    window.addEventListener("resize", onResize);
    return () => {
      document.removeEventListener("keydown", onKey);
      window.removeEventListener("resize", onResize);
    };
  }, []);

  const handleThemeChange = (t: Theme) => {
    setTheme(t);
    localStorage.setItem("theme", t);
  };

  const handleFontSizeChange = (f: FontSize) => {
    setFontSize(f);
    localStorage.setItem("fontSize", f);
  };

  const handleWsEvent = useCallback((event: WsEvent) => {
    if (event.type === "balance_changed") {
      const balances = event.balances as Record<string, number>;
      setLiveBalances((prev) => ({ ...prev, ...balances }));
    } else {
      activityCounterRef.current += 1;
      setActivityEntries((prev) =>
        [...prev, { id: activityCounterRef.current, event, timestamp: Date.now() }].slice(-50)
      );
    }
  }, []);

  const { connected } = useWebSocket({ userId: selectedUserId, onEvent: handleWsEvent });

  useEffect(() => {
    setSelectedUserId("alice");
  }, []);

  useEffect(() => {
    fetch(`/api/banking/accounts?_t=${Date.now()}`)
      .then((r) => r.json())
      .then((data) => {
        if (data.accounts) {
          setAccounts(data.accounts as AccountSummary[]);
        } else {
          setLoadError(data.error ?? "Failed to load accounts");
        }
      })
      .catch((err) => setLoadError(String(err)));
  }, [accountRefreshKey]);

  const selectedAccount = accounts.find((a) => a.user_id === selectedUserId);

  // ── Sidebar content (shared by desktop aside and mobile drawer) ──────
  const sidebarContent = (
    <>
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
                <div key={i} className="h-16 rounded-xl bg-muted animate-pulse" />
              ))}
            </div>
          ) : (
            <UserSelector
              accounts={accounts}
              selectedUserId={selectedUserId}
              onSelect={(id) => { setSelectedUserId(id); setSidebarOpen(false); }}
            />
          )}
        </CardContent>
      </Card>

      {/* Account detail card */}
      {selectedUserId && (
        <Card className="shadow-sm flex-shrink-0">
          <CardContent className="p-4">
            <AccountCard
              key={`${selectedUserId}-${accountRefreshKey}`}
              userId={selectedUserId}
              liveBalance={liveBalances[selectedUserId]}
            />
          </CardContent>
        </Card>
      )}

      {/* Live activity feed */}
      {selectedUserId && (
        <LiveActivityFeed entries={activityEntries} connected={connected} />
      )}

      {/* Demo info panel */}
      <DemoInfoPanel />
    </>
  );

  return (
    <div className="h-screen bg-gradient-to-br from-slate-50 to-blue-50 dark:from-slate-950 dark:to-blue-950 flex flex-col overflow-hidden">

      {/* ── Mobile sidebar drawer ────────────────────────────────────── */}
      <div className={cn("lg:hidden fixed inset-0 z-50", sidebarOpen ? "pointer-events-auto" : "pointer-events-none")}>
        {/* Backdrop */}
        <div
          className={cn(
            "absolute inset-0 bg-black/50 transition-opacity duration-300",
            sidebarOpen ? "opacity-100" : "opacity-0",
          )}
          onClick={() => setSidebarOpen(false)}
        />
        {/* Drawer panel */}
        <div className={cn(
          "absolute left-0 top-0 h-full w-72 bg-background border-r border-border flex flex-col gap-4 p-4 overflow-y-auto transition-transform duration-300",
          sidebarOpen ? "translate-x-0" : "-translate-x-full",
        )}>
          <div className="flex items-center justify-between flex-shrink-0">
            <div className="flex items-center gap-2">
              <Shield className="h-4 w-4 text-primary" />
              <span className="font-bold text-sm">SecureBank AI</span>
            </div>
            <button
              onClick={() => setSidebarOpen(false)}
              aria-label="Close sidebar"
              className="h-7 w-7 flex items-center justify-center rounded-md border border-border text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
          {sidebarContent}
        </div>
      </div>

      {/* ── Top header bar ─────────────────────────────────────────── */}
      <header className="flex-shrink-0 border-b border-border bg-card/80 backdrop-blur-sm px-4 py-3">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            {/* Hamburger — mobile only */}
            <button
              className="lg:hidden h-8 w-8 flex items-center justify-center rounded-md border border-border text-muted-foreground hover:bg-accent hover:text-foreground transition-colors mr-1"
              onClick={() => setSidebarOpen(true)}
              aria-label="Open sidebar"
            >
              <Menu className="h-4 w-4" />
            </button>
            <Shield className="h-5 w-5 text-primary" />
            <div>
              <span className="font-bold text-base tracking-tight">SecureBank AI</span>
              <span className="hidden sm:inline text-xs text-muted-foreground ml-2">
                Multi-agent banking demo
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2">
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
              <span className="inline-flex items-center gap-1 text-[10px] bg-amber-500/10 text-amber-700 dark:text-amber-400 rounded-full px-2.5 py-1">
                <Zap className="h-2.5 w-2.5" />
                Live WebSocket Events
              </span>
            </div>
            {/* Settings */}
            <SettingsPanel
              theme={theme}
              fontSize={fontSize}
              onThemeChange={handleThemeChange}
              onFontSizeChange={handleFontSizeChange}
              open={settingsOpen}
              onOpenChange={setSettingsOpen}
            />
          </div>
        </div>
      </header>

      {/* ── Mobile-only: compact user + balance strip ───────────────── */}
      <div className="lg:hidden flex-shrink-0 border-b border-border bg-card/60 backdrop-blur-sm px-3 py-2">
        {loadError ? (
          <p className="text-xs text-destructive px-1">{loadError}</p>
        ) : accounts.length === 0 ? (
          <div className="flex gap-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-8 w-24 rounded-full bg-muted animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="flex items-center gap-2 overflow-x-auto pb-0.5">
            {accounts.map((account) => {
              const selected = account.user_id === selectedUserId;
              const balance = liveBalances[account.user_id] ?? account.balance;
              return (
                <button
                  key={account.user_id}
                  onClick={() => setSelectedUserId(account.user_id)}
                  className={cn(
                    "flex-shrink-0 flex items-center gap-2 rounded-full px-3 py-1.5 border transition-all text-xs font-medium",
                    selected
                      ? "bg-primary/10 border-primary/40 shadow-sm"
                      : "bg-card border-border hover:bg-accent/50"
                  )}
                >
                  <span
                    className="w-5 h-5 rounded-full flex items-center justify-center text-white text-[10px] font-bold flex-shrink-0"
                    style={{ backgroundColor: account.avatar_color }}
                  >
                    {initials(account.name)}
                  </span>
                  <span className={selected ? "text-primary" : "text-foreground"}>
                    {account.name.split(" ")[0]}
                  </span>
                  {selected && (
                    <span className="font-bold tabular-nums text-primary">
                      {formatBalance(balance)}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* ── Main body ───────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col lg:flex-row overflow-hidden max-w-7xl w-full mx-auto p-4 gap-4 min-h-0">

        {/* Left sidebar — desktop only */}
        <aside className="hidden lg:flex flex-shrink-0 w-72 flex-col gap-4 overflow-y-auto">
          {sidebarContent}
        </aside>

        {/* Right panel — chat (full height on both mobile and desktop) */}
        <main className="flex-1 flex flex-col min-h-0">
          <Card className="flex-1 shadow-sm flex flex-col min-h-0 overflow-hidden">
            <CardHeader className="flex-shrink-0 pb-0 px-4 pt-4 border-b border-border">
              <div className="flex items-center justify-between pb-3">
                <div>
                  <CardTitle className="text-base">Banking Assistant</CardTitle>
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
                    {initials(selectedAccount.name)}
                  </div>
                )}
              </div>
            </CardHeader>

            <CardContent className="flex-1 p-0 min-h-0 overflow-hidden">
              {selectedUserId && selectedAccount ? (
                <div className="h-full" style={{ minHeight: "300px" }}>
                  <BankingChatInterface
                    key={selectedUserId}
                    userId={selectedUserId}
                    userName={selectedAccount.name.split(" ")[0]}
                    onComplete={() => setAccountRefreshKey((k) => k + 1)}
                  />
                </div>
              ) : (
                <div className="flex items-center justify-center h-full min-h-[200px] text-muted-foreground text-sm">
                  Select a user above to start banking
                </div>
              )}
            </CardContent>
          </Card>
        </main>
      </div>
    </div>
  );
}
