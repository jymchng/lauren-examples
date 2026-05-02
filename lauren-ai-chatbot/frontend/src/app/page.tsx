import { ChatInterface } from "@/components/ChatInterface";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Sparkles, Shield, Zap } from "lucide-react";

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 dark:from-slate-950 dark:to-blue-950 flex flex-col items-center justify-center px-2 py-4 sm:p-4">
      <div className="w-full max-w-3xl">
        {/* Header */}
        <div className="mb-6 text-center">
          <h1 className="text-3xl font-bold tracking-tight text-foreground mb-2">
            Lauren AI Chatbot
          </h1>
          <p className="text-muted-foreground text-sm">
            Full-stack SSE streaming demo · Built with{" "}
            <span className="font-semibold text-primary">Lauren</span> &amp; Next.js
          </p>

          {/* Feature pills */}
          <div className="mt-3 flex flex-wrap justify-center gap-2">
            <span className="inline-flex items-center gap-1 text-xs bg-primary/10 text-primary rounded-full px-3 py-1">
              <Zap className="h-3 w-3" />
              SSE Streaming
            </span>
            <span className="inline-flex items-center gap-1 text-xs bg-emerald-500/10 text-emerald-600 rounded-full px-3 py-1">
              <Shield className="h-3 w-3" />
              HMAC-signed Payloads
            </span>
            <span className="inline-flex items-center gap-1 text-xs bg-violet-500/10 text-violet-600 rounded-full px-3 py-1">
              <Sparkles className="h-3 w-3" />
              Guards · Interceptors · Middlewares
            </span>
          </div>
        </div>

        {/* Chat card */}
        <Card className="w-full shadow-xl">
          <CardHeader className="pb-0">
            <CardTitle className="text-base text-muted-foreground font-normal">
              Chat — powered by OpenRouter
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="h-[480px] sm:h-[560px] flex flex-col">
              <ChatInterface />
            </div>
          </CardContent>
        </Card>

        {/* Architecture notes */}
        <div className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs text-muted-foreground">
          <div className="bg-card rounded-lg p-3 border border-border">
            <p className="font-semibold text-foreground mb-1">SignatureGuard</p>
            <p>
              Every chat request carries an HMAC-SHA256 signature. Lauren's
              guard verifies it before the handler runs.
            </p>
          </div>
          <div className="bg-card rounded-lg p-3 border border-border">
            <p className="font-semibold text-foreground mb-1">TimingInterceptor</p>
            <p>
              Wraps all handlers and injects an{" "}
              <code className="font-mono text-[10px]">X-Response-Time</code>{" "}
              header — visible in browser DevTools.
            </p>
          </div>
          <div className="bg-card rounded-lg p-3 border border-border">
            <p className="font-semibold text-foreground mb-1">CORS &amp; Logging</p>
            <p>
              Global middlewares handle CORS headers and structured request/
              response logging for all routes.
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}
