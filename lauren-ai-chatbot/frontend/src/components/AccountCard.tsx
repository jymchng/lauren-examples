"use client";

/**
 * AccountCard — shows the selected user's account balance and recent
 * transactions.  Fetches from /api/banking/accounts/[userId] on mount
 * and whenever userId changes.
 */

import { useEffect, useState } from "react";
import { ArrowDownLeft, ArrowUpRight, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";

interface Transaction {
  tx_id: string;
  type: "debit" | "credit";
  counterparty_name: string;
  amount: number;
  description: string;
  timestamp: string;
}

interface AccountDetail {
  user_id: string;
  name: string;
  account_id: string;
  balance: number;
  avatar_color: string;
  transactions: Transaction[];
}

interface AccountCardProps {
  userId: string;
}

function formatBalance(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(amount);
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    });
  } catch {
    return iso.slice(0, 10);
  }
}

function initials(name: string): string {
  return name
    .split(" ")
    .map((p) => p[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

export function AccountCard({ userId }: AccountCardProps) {
  const [account, setAccount] = useState<AccountDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setAccount(null);

    fetch(`/api/banking/accounts/${userId}`)
      .then((r) => r.json())
      .then((data) => {
        if (!cancelled) {
          if (data.error) {
            setError(data.error);
          } else {
            setAccount(data as AccountDetail);
          }
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(String(err));
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [userId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center gap-2 py-6 text-muted-foreground text-sm">
        <RefreshCw className="h-4 w-4 animate-spin" />
        Loading account…
      </div>
    );
  }

  if (error || !account) {
    return (
      <div className="py-4 px-3 text-destructive text-xs rounded-lg bg-destructive/10">
        {error ?? "Account not found"}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Balance hero */}
      <div
        className="rounded-xl p-4 text-white"
        style={{ backgroundColor: account.avatar_color }}
      >
        <div className="flex items-center gap-3 mb-3">
          <div className="w-9 h-9 rounded-full bg-white/20 flex items-center justify-center text-white text-sm font-bold">
            {initials(account.name)}
          </div>
          <div>
            <p className="text-sm font-semibold leading-tight">{account.name}</p>
            <p className="text-xs text-white/70">{account.account_id}</p>
          </div>
        </div>
        <p className="text-xs text-white/70 mb-0.5">Available Balance</p>
        <p className="text-2xl font-bold tabular-nums tracking-tight">
          {formatBalance(account.balance)}
        </p>
      </div>

      {/* Transactions */}
      <div>
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
          Recent Transactions
        </p>
        {account.transactions.length === 0 ? (
          <p className="text-xs text-muted-foreground italic py-2">No transactions yet</p>
        ) : (
          <div className="space-y-1">
            {account.transactions.map((tx) => (
              <div
                key={tx.tx_id}
                className="flex items-center gap-2.5 rounded-lg px-2.5 py-2 bg-card border border-border"
              >
                <div
                  className={cn(
                    "flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center",
                    tx.type === "credit"
                      ? "bg-emerald-100 text-emerald-600 dark:bg-emerald-900/30"
                      : "bg-red-100 text-red-500 dark:bg-red-900/30"
                  )}
                >
                  {tx.type === "credit" ? (
                    <ArrowDownLeft className="h-3.5 w-3.5" />
                  ) : (
                    <ArrowUpRight className="h-3.5 w-3.5" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium truncate">{tx.counterparty_name}</p>
                  <p className="text-[10px] text-muted-foreground truncate">{tx.description}</p>
                </div>
                <div className="flex-shrink-0 text-right">
                  <p
                    className={cn(
                      "text-xs font-semibold tabular-nums",
                      tx.type === "credit" ? "text-emerald-600" : "text-red-500"
                    )}
                  >
                    {tx.type === "credit" ? "+" : "-"}
                    {formatBalance(tx.amount)}
                  </p>
                  <p className="text-[10px] text-muted-foreground">{formatDate(tx.timestamp)}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
