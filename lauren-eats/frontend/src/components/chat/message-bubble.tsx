'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Copy, Check, ArrowRight } from 'lucide-react'
import { cn } from '@/lib/utils'
import { getAgentByType } from './agents'
import type { ChatMessage } from '@/types'

interface MessageBubbleProps {
  message: ChatMessage
}

/** Simple markdown-like renderer for bold, italic, bullet lists */
function renderContent(content: string) {
  // Split into lines for list handling
  const lines = content.split('\n')
  const elements: React.ReactNode[] = []

  lines.forEach((line, lineIdx) => {
    // Bullet list items
    if (line.match(/^\s*[-•*]\s/)) {
      const text = line.replace(/^\s*[-•*]\s/, '')
      elements.push(
        <li key={lineIdx} className="ml-3 list-disc">
          {renderInline(text)}
        </li>
      )
      return
    }

    // Numbered list items
    if (line.match(/^\s*\d+\.\s/)) {
      const text = line.replace(/^\s*\d+\.\s/, '')
      elements.push(
        <li key={lineIdx} className="ml-3 list-decimal">
          {renderInline(text)}
        </li>
      )
      return
    }

    // Empty line = paragraph break
    if (line.trim() === '') {
      if (lineIdx > 0 && lineIdx < lines.length - 1) {
        elements.push(<div key={lineIdx} className="h-2" />)
      }
      return
    }

    // Normal paragraph
    elements.push(<p key={lineIdx}>{renderInline(line)}</p>)
  })

  return elements
}

function renderInline(text: string): React.ReactNode {
  // Process bold and italic
  const parts: React.ReactNode[] = []
  // Match **bold** and *italic*
  const regex = /(\*\*.*?\*\*|\*.*?\*)/g
  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = regex.exec(text)) !== null) {
    // Push text before match
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index))
    }

    const matched = match[0]
    if (matched.startsWith('**') && matched.endsWith('**')) {
      parts.push(
        <strong key={match.index} className="font-semibold">
          {matched.slice(2, -2)}
        </strong>
      )
    } else if (matched.startsWith('*') && matched.endsWith('*')) {
      parts.push(
        <em key={match.index} className="italic">
          {matched.slice(1, -1)}
        </em>
      )
    }
    lastIndex = match.index + matched.length
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex))
  }

  return parts.length > 0 ? parts : text
}

// ─── Handoff Message Component ──────────────────────────────────────────

function HandoffMessage({
  fromName,
  toName,
  fromEmoji,
  toEmoji,
  fromColor,
  toColor,
  reason,
}: {
  fromName: string
  toName: string
  fromEmoji: string
  toEmoji: string
  fromColor: string
  toColor: string
  reason?: string
}) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95, y: 8 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] }}
      className="mx-4 my-3"
    >
      <div className="relative overflow-hidden rounded-xl border border-border/60 bg-gradient-to-r from-muted/30 via-muted/50 to-muted/30 shadow-sm">
        {/* Animated background shimmer */}
        <motion.div
          className="absolute inset-0 opacity-30"
          style={{
            background: `linear-gradient(90deg, ${fromColor}15, ${toColor}15, ${fromColor}15)`,
            backgroundSize: '200% 100%',
          }}
          animate={{ backgroundPosition: ['0% 0%', '100% 0%', '0% 0%'] }}
          transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
        />

        <div className="relative px-4 py-3 flex items-center gap-3">
          {/* From agent */}
          <motion.div
            initial={{ x: -10, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            transition={{ delay: 0.1 }}
            className="flex items-center gap-2"
          >
            <div
              className="flex items-center justify-center w-8 h-8 rounded-full text-sm shrink-0"
              style={{
                backgroundColor: fromColor + '20',
                border: `1.5px solid ${fromColor}50`,
              }}
            >
              {fromEmoji}
            </div>
            <span className="text-xs font-medium text-muted-foreground">{fromName}</span>
          </motion.div>

          {/* Arrow animation */}
          <motion.div
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.3, type: 'spring', stiffness: 300 }}
            className="flex items-center gap-1"
          >
            <motion.div
              animate={{ x: [0, 4, 0] }}
              transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
            >
              <ArrowRight className="h-4 w-4 text-restaurant-gold" />
            </motion.div>
          </motion.div>

          {/* To agent */}
          <motion.div
            initial={{ x: 10, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="flex items-center gap-2"
          >
            <div
              className="flex items-center justify-center w-8 h-8 rounded-full text-sm shrink-0 ring-2 ring-restaurant-gold/30"
              style={{
                backgroundColor: toColor + '20',
                border: `1.5px solid ${toColor}`,
              }}
            >
              {toEmoji}
            </div>
            <div>
              <span className="text-xs font-semibold text-foreground">{toName}</span>
              <AnimatePresence>
                <motion.span
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.8 }}
                  className="ml-1.5 inline-flex items-center gap-1 text-[10px] text-restaurant-gold"
                >
                  <motion.span
                    animate={{ scale: [1, 1.2, 1] }}
                    transition={{ duration: 1, repeat: Infinity }}
                  >
                    ✦
                  </motion.span>
                  Active
                </motion.span>
              </AnimatePresence>
            </div>
          </motion.div>
        </div>

        {/* Reason text */}
        {reason && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6 }}
            className="relative px-4 pb-3 pt-0"
          >
            <p className="text-xs text-muted-foreground italic">{reason}</p>
          </motion.div>
        )}
      </div>
    </motion.div>
  )
}

// ─── Main Message Bubble ──────────────────────────────────────────────

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user'
  const [copied, setCopied] = useState(false)
  const agent = !isUser && message.agentType ? getAgentByType(message.agentType) : null

  // Check if this is a handoff message
  const isHandoff = message.metadata?.type === 'handoff'
  const handoffData = isHandoff
    ? (message.metadata as {
        type: 'handoff'
        fromAgent: string
        toAgent: string
        fromName: string
        toName: string
        fromEmoji: string
        toEmoji: string
      })
    : null

  // Render handoff message
  if (isHandoff && handoffData) {
    const fromAgentDef = getAgentByType(handoffData.fromAgent as any)
    const toAgentDef = getAgentByType(handoffData.toAgent as any)
    return (
      <HandoffMessage
        fromName={handoffData.fromName || fromAgentDef.name}
        toName={handoffData.toName || toAgentDef.name}
        fromEmoji={handoffData.fromEmoji || fromAgentDef.emoji}
        toEmoji={handoffData.toEmoji || toAgentDef.emoji}
        fromColor={fromAgentDef.color}
        toColor={toAgentDef.color}
        reason={message.content !== `Transferring you to ${handoffData.toName}` ? message.content : undefined}
      />
    )
  }

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // Fallback
    }
  }

  const timeStr = new Date(message.timestamp).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  })

  return (
    <motion.div
      initial={{ opacity: 0, y: 12, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.3, ease: [0.25, 0.46, 0.45, 0.94] }}
      className={cn(
        'group flex gap-2.5 px-4 py-1.5',
        isUser ? 'flex-row-reverse' : 'flex-row'
      )}
    >
      {/* Avatar */}
      {!isUser && agent && (
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: 'spring', stiffness: 400, damping: 20, delay: 0.1 }}
          className="flex items-center justify-center w-8 h-8 rounded-full shrink-0 text-sm shadow-sm mt-1"
          style={{
            backgroundColor: agent.color + '20',
            border: `1.5px solid ${agent.color}40`,
          }}
        >
          {agent.emoji}
        </motion.div>
      )}

      {/* Bubble */}
      <div className={cn('relative max-w-[80%] sm:max-w-[70%]', isUser ? 'items-end' : 'items-start')}>
        <div
          className={cn(
            'rounded-2xl px-4 py-2.5 text-sm leading-relaxed shadow-sm',
            isUser
              ? 'bg-restaurant-red text-restaurant-red-foreground rounded-br-md'
              : 'bg-card border border-border/60 text-card-foreground rounded-bl-md'
          )}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap break-words">{message.content}</p>
          ) : (
            <div className="whitespace-pre-wrap break-words space-y-0.5">
              {renderContent(message.content)}
            </div>
          )}

          {/* Streaming cursor */}
          {message.isStreaming && (
            <motion.span
              className="inline-block w-1.5 h-4 ml-0.5 align-text-bottom rounded-sm"
              style={{ backgroundColor: agent?.color ?? '#C41E3A' }}
              animate={{ opacity: [1, 0] }}
              transition={{ duration: 0.6, repeat: Infinity, repeatType: 'reverse' }}
            />
          )}
        </div>

        {/* Timestamp & copy */}
        <div
          className={cn(
            'flex items-center gap-2 mt-1 px-1',
            isUser ? 'justify-end' : 'justify-start'
          )}
        >
          <span className="text-[10px] text-muted-foreground/60">{timeStr}</span>

          {/* Copy button - visible on hover */}
          <button
            onClick={handleCopy}
            className="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 rounded hover:bg-muted/50"
            aria-label="Copy message"
          >
            {copied ? (
              <Check className="h-3 w-3 text-green-500" />
            ) : (
              <Copy className="h-3 w-3 text-muted-foreground/50" />
            )}
          </button>
        </div>
      </div>
    </motion.div>
  )
}
