import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { prismTheme } from "@/lib/prism-theme";
import type { Components } from "react-markdown";
import { cn } from "@/lib/utils";

export interface Message {
  id: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
}

interface MessageBubbleProps {
  message: Message;
}

const mdComponents: Components = {
  p: ({ children }) => <p className="mb-2 last:mb-0 leading-6">{children}</p>,
  h1: ({ children }) => <h1 className="text-lg font-bold mb-2 mt-3 first:mt-0">{children}</h1>,
  h2: ({ children }) => <h2 className="text-base font-bold mb-2 mt-3 first:mt-0">{children}</h2>,
  h3: ({ children }) => <h3 className="text-sm font-bold mb-1 mt-2 first:mt-0">{children}</h3>,
  ul: ({ children }) => <ul className="list-disc pl-4 mb-2 space-y-0.5">{children}</ul>,
  ol: ({ children }) => <ol className="list-decimal pl-4 mb-2 space-y-0.5">{children}</ol>,
  li: ({ children }) => <li className="leading-6">{children}</li>,
  strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
  em: ({ children }) => <em className="italic">{children}</em>,
  hr: () => <hr className="border-muted-foreground/20 my-3" />,
  blockquote: ({ children }) => (
    <blockquote className="border-l-4 border-muted-foreground/30 pl-3 my-2 text-muted-foreground italic">
      {children}
    </blockquote>
  ),
  a: ({ href, children }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="underline underline-offset-2 hover:opacity-80"
    >
      {children}
    </a>
  ),
  table: ({ children }) => (
    <div className="overflow-x-auto my-2">
      <table className="min-w-full border-collapse text-xs">{children}</table>
    </div>
  ),
  th: ({ children }) => (
    <th className="px-3 py-1.5 text-left font-semibold bg-black/5 dark:bg-white/5 border border-muted-foreground/20">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="px-3 py-1.5 border border-muted-foreground/20">{children}</td>
  ),
  pre: ({ children }) => <>{children}</>,
  code: ({ className, children, ...props }) => {
    const match = /language-([A-Za-z0-9-]+)/.exec(className || "");
    const lang = match ? match[1] : null;
    if (lang) {
      return (
        <div className="my-2 rounded-lg overflow-hidden border border-white/10 text-xs">
          <div className="px-3 py-1 bg-[#252526] text-[#9da5b4] text-[10px] font-mono border-b border-white/10">
            {lang}
          </div>
          <div className="overflow-x-auto">
            <SyntaxHighlighter
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              style={prismTheme as any}
              language={lang}
              customStyle={{
                margin: 0,
                background: "#1e1e1e",
                padding: "0.65rem 0.85rem",
                fontSize: "0.72rem",
                lineHeight: "1.5",
              }}
            >
              {String(children).replace(/\n$/, "")}
            </SyntaxHighlighter>
          </div>
        </div>
      );
    }
    return (
      <code
        className="bg-black/10 dark:bg-white/10 px-1 py-0.5 rounded text-[0.78rem] font-mono"
        {...props}
      >
        {children}
      </code>
    );
  },
};

export function MessageBubble({ message }: MessageBubbleProps) {
  if (message.role === "system") {
    return (
      <div className="flex items-center gap-3 my-3 px-2">
        <div className="flex-1 h-px bg-border" />
        <span className="flex-shrink-0 text-[11px] text-muted-foreground font-medium px-2">
          {message.content}
        </span>
        <div className="flex-1 h-px bg-border" />
      </div>
    );
  }

  const isUser = message.role === "user";

  return (
    <div className={cn("flex w-full mb-4", isUser ? "justify-end" : "justify-start")}>
      {!isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary flex items-center justify-center text-primary-foreground text-xs font-bold mr-2 mt-1">
          AI
        </div>
      )}

      <div
        className={cn(
          "max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed break-words",
          isUser
            ? "bg-primary text-primary-foreground rounded-br-sm whitespace-pre-wrap"
            : "bg-muted text-foreground rounded-bl-sm"
        )}
      >
        {isUser ? (
          message.content
        ) : (
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>
            {message.content}
          </ReactMarkdown>
        )}
      </div>

      {isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-secondary flex items-center justify-center text-secondary-foreground text-xs font-bold ml-2 mt-1">
          You
        </div>
      )}
    </div>
  );
}

export function MarkdownContent({ content }: { content: string }) {
  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>
      {content}
    </ReactMarkdown>
  );
}
