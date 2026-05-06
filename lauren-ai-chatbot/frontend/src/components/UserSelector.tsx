"use client";

/**
 * UserSelector — displays a "Public (Guest)" option plus Alice, Bob, and Charlie.
 *
 * The public option sets userId to null (unauthenticated session).
 * Clicking an account card fires `onSelect` with the user_id string.
 */

import { Globe } from "lucide-react";
import { cn } from "@/lib/utils";

export interface AccountSummary {
  user_id: string;
  name: string;
  account_id: string;
  balance: number;
  avatar_color: string;
}

interface UserSelectorProps {
  accounts: AccountSummary[];
  selectedUserId: string | null;
  onSelect: (userId: string | null) => void;
}

function initials(name: string): string {
  return name
    .split(" ")
    .map((p) => p[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

function formatBalance(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(amount);
}

export function UserSelector({
  accounts,
  selectedUserId,
  onSelect,
}: UserSelectorProps) {
  const publicSelected = selectedUserId === null;

  return (
    <div className="flex flex-col gap-2">
      {/* Public / Guest option */}
      <button
        onClick={() => onSelect(null)}
        className={cn(
          "w-full flex items-center gap-3 rounded-xl px-3 py-3 text-left transition-all",
          "border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
          publicSelected
            ? "bg-primary/10 border-primary/30 shadow-sm"
            : "bg-card border-border hover:bg-accent/50"
        )}
      >
        <div className="flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center bg-muted border border-border shadow-sm">
          <Globe className={cn("h-5 w-5", publicSelected ? "text-primary" : "text-muted-foreground")} />
        </div>
        <div className="flex-1 min-w-0">
          <p className={cn("text-sm font-semibold truncate", publicSelected ? "text-primary" : "text-foreground")}>
            Public (Guest)
          </p>
          <p className="text-xs text-muted-foreground truncate">Not logged in</p>
        </div>
        <div className="flex-shrink-0 text-right">
          <p className="text-xs text-muted-foreground">Browse only</p>
        </div>
      </button>

      {/* Authenticated accounts */}
      {accounts.map((account) => {
        const selected = account.user_id === selectedUserId;
        return (
          <button
            key={account.user_id}
            onClick={() => onSelect(account.user_id)}
            className={cn(
              "w-full flex items-center gap-3 rounded-xl px-3 py-3 text-left transition-all",
              "border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              selected
                ? "bg-primary/10 border-primary/30 shadow-sm"
                : "bg-card border-border hover:bg-accent/50"
            )}
          >
            <div
              className="flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center text-white text-sm font-bold shadow-sm"
              style={{ backgroundColor: account.avatar_color }}
            >
              {initials(account.name)}
            </div>
            <div className="flex-1 min-w-0">
              <p className={cn("text-sm font-semibold truncate", selected ? "text-primary" : "text-foreground")}>
                {account.name}
              </p>
              <p className="text-xs text-muted-foreground truncate">
                {account.account_id}
              </p>
            </div>
            <div className="flex-shrink-0 text-right">
              <p className={cn("text-sm font-bold tabular-nums", selected ? "text-primary" : "text-foreground")}>
                {formatBalance(account.balance)}
              </p>
            </div>
          </button>
        );
      })}
    </div>
  );
}
