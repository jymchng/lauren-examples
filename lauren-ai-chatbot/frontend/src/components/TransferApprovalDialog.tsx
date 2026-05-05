"use client";

/**
 * TransferApprovalDialog — HITL gate rendered when the backend sends a
 * transfer_approval_request WebSocket event.
 *
 * The dialog is a fixed overlay (z-50) with a centered card.  It shows the
 * transfer summary and lets the user confirm or cancel.  While the HTTP
 * request is in-flight, both buttons are disabled and a spinner is shown.
 */

import { useState } from "react";
import type { TransferApprovalRequest } from "@/hooks/useWebSocket";

interface Props {
  request: TransferApprovalRequest | null;
  userId: string;
  onClose: () => void;
}

function Spinner() {
  return (
    <svg
      className="animate-spin h-4 w-4 text-current"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8v8H4z"
      />
    </svg>
  );
}

export function TransferApprovalDialog({ request, userId, onClose }: Props) {
  const [loading, setLoading] = useState(false);

  if (!request) return null;

  const { approval_id, from_user, to_user, amount_usd, description } = request;

  const respond = async (approved: boolean) => {
    setLoading(true);
    try {
      await fetch("/api/banking/approval", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          approval_id,
          approved,
          user_id: userId,
        }),
      });
    } catch {
      // Even on network error, close the dialog — the backend will timeout.
    } finally {
      setLoading(false);
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50" />

      {/* Card */}
      <div className="relative z-10 bg-background border border-border rounded-xl shadow-2xl w-full max-w-sm mx-4 p-6">
        {/* Header */}
        <div className="flex items-center gap-2 mb-4">
          <span className="text-amber-500 text-xl">🔐</span>
          <h2 className="text-base font-semibold text-foreground">
            Approve Transfer
          </h2>
        </div>

        {/* Transfer summary */}
        <div className="bg-muted/60 rounded-lg p-4 mb-5 space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">From</span>
            <span className="font-medium capitalize">{from_user}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">To</span>
            <span className="font-medium capitalize">{to_user}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Amount</span>
            <span className="font-bold text-foreground text-base">
              {new Intl.NumberFormat("en-US", {
                style: "currency",
                currency: "USD",
                minimumFractionDigits: 2,
              }).format(amount_usd)}
            </span>
          </div>
          {description && (
            <div className="flex justify-between">
              <span className="text-muted-foreground">Note</span>
              <span className="text-right max-w-[180px] truncate">{description}</span>
            </div>
          )}
        </div>

        <p className="text-xs text-muted-foreground mb-5">
          Your banking AI agent is requesting permission to make this transfer.
          Approve only if you initiated this request.
        </p>

        {/* Actions */}
        <div className="flex gap-3">
          <button
            disabled={loading}
            onClick={() => respond(true)}
            className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-primary text-primary-foreground px-4 py-2.5 text-sm font-medium hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? <Spinner /> : null}
            Confirm Transfer
          </button>
          <button
            disabled={loading}
            onClick={() => respond(false)}
            className="flex-1 flex items-center justify-center gap-2 rounded-lg border border-destructive text-destructive px-4 py-2.5 text-sm font-medium hover:bg-destructive/10 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
