"use client";

import { useEffect, useRef } from "react";
import { Settings, Sun, Moon, Monitor } from "lucide-react";
import { cn } from "@/lib/utils";

export type Theme = "light" | "dark" | "system";
export type FontSize = "sm" | "md" | "lg";

interface Props {
  theme: Theme;
  fontSize: FontSize;
  onThemeChange: (t: Theme) => void;
  onFontSizeChange: (f: FontSize) => void;
  open: boolean;
  onOpenChange: (v: boolean) => void;
}

const THEMES: { value: Theme; Icon: React.ComponentType<{ className?: string }>; label: string }[] = [
  { value: "light", Icon: Sun,     label: "Light"  },
  { value: "dark",  Icon: Moon,    label: "Dark"   },
  { value: "system",Icon: Monitor, label: "System" },
];

const FONT_SIZES: { value: FontSize; label: string; size: string }[] = [
  { value: "sm", label: "Small",   size: "text-xs"   },
  { value: "md", label: "Default", size: "text-sm"   },
  { value: "lg", label: "Large",   size: "text-base" },
];

export function SettingsPanel({ theme, fontSize, onThemeChange, onFontSizeChange, open, onOpenChange }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  /* Close on outside click */
  useEffect(() => {
    if (!open) return;
    function handler(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        onOpenChange(false);
      }
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open, onOpenChange]);

  return (
    <div ref={containerRef} className="relative">
      <button
        onClick={() => onOpenChange(!open)}
        aria-label="Settings"
        aria-expanded={open}
        className={cn(
          "h-8 w-8 flex items-center justify-center rounded-md border border-border transition-colors",
          "text-muted-foreground hover:bg-accent hover:text-foreground",
          open && "bg-accent text-foreground",
        )}
      >
        <Settings className="h-[15px] w-[15px]" />
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 z-[60] w-52 rounded-xl border border-border bg-card shadow-xl p-4 space-y-4">

          {/* ── Theme ──────────────────────────────────────────── */}
          <div>
            <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest mb-2.5">
              Theme
            </p>
            <div className="grid grid-cols-3 gap-1">
              {THEMES.map(({ value, Icon, label }) => (
                <button
                  key={value}
                  onClick={() => onThemeChange(value)}
                  className={cn(
                    "flex flex-col items-center gap-1.5 rounded-lg py-2.5 border text-[10px] font-medium transition-all",
                    theme === value
                      ? "border-primary bg-primary/10 text-primary shadow-sm"
                      : "border-transparent bg-muted/50 hover:bg-accent text-muted-foreground hover:text-foreground",
                  )}
                >
                  <Icon className="h-3.5 w-3.5" />
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* ── Font size ──────────────────────────────────────── */}
          <div>
            <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest mb-2.5">
              Font Size
            </p>
            <div className="grid grid-cols-3 gap-1">
              {FONT_SIZES.map(({ value, label, size }) => (
                <button
                  key={value}
                  onClick={() => onFontSizeChange(value)}
                  className={cn(
                    "flex flex-col items-center gap-1 rounded-lg py-2.5 border transition-all",
                    fontSize === value
                      ? "border-primary bg-primary/10 text-primary shadow-sm"
                      : "border-transparent bg-muted/50 hover:bg-accent text-muted-foreground hover:text-foreground",
                  )}
                >
                  <span className={cn("font-bold leading-none", size)}>Aa</span>
                  <span className="text-[10px] font-medium">{label}</span>
                </button>
              ))}
            </div>
          </div>

        </div>
      )}
    </div>
  );
}
