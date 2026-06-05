'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Send,
  Menu,
  Sparkles,
  Trash2,
  X,
  ArrowRight,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useIsMobile } from '@/hooks/use-mobile'
import { useChatStore } from '@/store/chat-store'
import { AGENTS, getAgentByType } from './agents'
import { MessageBubble } from './message-bubble'
import { TypingIndicator } from './typing-indicator'
import type { ChatMessage, AgentType } from '@/types'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet'

// ─── Agent Sidebar Card ────────────────────────────────────────────────

function AgentCard({
  agent,
  isActive,
  onClick,
}: {
  agent: (typeof AGENTS)[number]
  isActive: boolean
  onClick: () => void
}) {
  return (
    <motion.button
      whileHover={{ x: 2 }}
      whileTap={{ scale: 0.98 }}
      onClick={onClick}
      className={cn(
        'w-full flex items-center gap-3 p-3 rounded-xl text-left transition-all duration-200',
        isActive
          ? 'bg-white dark:bg-white/5 shadow-sm border'
          : 'hover:bg-muted/50 border border-transparent'
      )}
      style={
        isActive
          ? {
              borderColor: agent.color + '60',
              boxShadow: `0 0 16px -4px ${agent.color}25`,
            }
          : undefined
      }
    >
      {/* Emoji avatar with colored bg */}
      <div
        className="flex items-center justify-center w-10 h-10 rounded-full text-base shrink-0 transition-transform duration-200"
        style={{
          backgroundColor: agent.color + '18',
          border: isActive ? `2px solid ${agent.color}` : `1.5px solid ${agent.color}30`,
        }}
      >
        {agent.emoji}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold truncate">{agent.name}</span>
          {isActive && (
            <motion.div
              layoutId="activeAgentDot"
              className="w-2 h-2 rounded-full shrink-0"
              style={{ backgroundColor: agent.color }}
              animate={{ scale: [1, 1.3, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
            />
          )}
        </div>
        <span className="text-xs text-muted-foreground truncate block">
          {agent.description}
        </span>
      </div>
    </motion.button>
  )
}

// ─── Agent Sidebar (Desktop) ──────────────────────────────────────────

function AgentSidebar({
  currentAgent,
  onAgentChange,
}: {
  currentAgent: AgentType
  onAgentChange: (type: AgentType) => void
}) {
  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b border-border/50">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-restaurant-gold" />
          <h2 className="text-sm font-semibold tracking-wide">AI Agents</h2>
        </div>
        <p className="text-[11px] text-muted-foreground mt-1">
          Choose a specialist to chat with
        </p>
      </div>

      <div className="flex-1 p-3 space-y-1.5 overflow-y-auto">
        {AGENTS.map((agent) => (
          <AgentCard
            key={agent.type}
            agent={agent}
            isActive={currentAgent === agent.type}
            onClick={() => onAgentChange(agent.type)}
          />
        ))}
      </div>

      {/* Branding footer */}
      <div className="p-4 border-t border-border/50">
        <div className="flex items-center gap-2 text-[11px] text-muted-foreground/60">
          <Sparkles className="h-3 w-3 text-restaurant-gold/60" />
          <span>Powered by Lauren AI</span>
        </div>
      </div>
    </div>
  )
}

// ─── Empty State ──────────────────────────────────────────────────────

function EmptyChatState({ agentType, onQuickPrompt }: { agentType: AgentType; onQuickPrompt: (prompt: string) => void }) {
  const agent = getAgentByType(agentType)

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="flex-1 flex items-center justify-center p-8"
    >
      <div className="text-center max-w-sm">
        <motion.div
          animate={{ y: [0, -6, 0] }}
          transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
          className="text-5xl mb-4"
        >
          {agent.emoji}
        </motion.div>
        <h3 className="text-lg font-semibold mb-1">{agent.name}</h3>
        <p className="text-sm text-muted-foreground mb-6">{agent.description}</p>

        <div className="space-y-2">
          {agent.quickPrompts.map((prompt, i) => (
            <motion.button
              key={prompt}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.1 + i * 0.08 }}
              whileHover={{ x: 4, scale: 1.01 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => onQuickPrompt(prompt)}
              className="w-full text-left px-4 py-2.5 rounded-xl text-sm border border-border/50 bg-card hover:bg-accent/50 hover:border-border transition-colors"
            >
              <span className="text-muted-foreground mr-2">→</span>
              {prompt}
            </motion.button>
          ))}
        </div>
      </div>
    </motion.div>
  )
}

// ─── Handoff Notification Banner ──────────────────────────────────────

function HandoffBanner({
  fromName,
  fromEmoji,
  fromColor,
  toName,
  toEmoji,
  toColor,
  onDismiss,
}: {
  fromName: string
  fromEmoji: string
  fromColor: string
  toName: string
  toEmoji: string
  toColor: string
  onDismiss: () => void
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -20, scale: 0.95 }}
      transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
      className="absolute top-16 left-0 right-0 z-20 px-4 pt-2"
    >
      <div className="mx-auto max-w-lg">
        <div
          className="relative overflow-hidden rounded-xl border shadow-lg px-4 py-3 flex items-center gap-3"
          style={{
            borderColor: toColor + '40',
            background: `linear-gradient(135deg, ${fromColor}08, ${toColor}12)`,
          }}
        >
          {/* From agent */}
          <div
            className="flex items-center justify-center w-8 h-8 rounded-full text-sm shrink-0"
            style={{
              backgroundColor: fromColor + '15',
              border: `1.5px solid ${fromColor}30`,
            }}
          >
            {fromEmoji}
          </div>

          <ArrowRight className="h-3.5 w-3.5 text-restaurant-gold shrink-0" />

          {/* To agent */}
          <div
            className="flex items-center justify-center w-8 h-8 rounded-full text-sm shrink-0 ring-2 ring-restaurant-gold/30"
            style={{
              backgroundColor: toColor + '15',
              border: `1.5px solid ${toColor}`,
            }}
          >
            {toEmoji}
          </div>

          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-foreground">
              Handed off to <span className="font-bold" style={{ color: toColor }}>{toName}</span>
            </p>
            <p className="text-[10px] text-muted-foreground truncate">
              {fromName} transferred this conversation
            </p>
          </div>

          <button
            onClick={onDismiss}
            className="shrink-0 p-1 rounded-full hover:bg-muted/50 transition-colors"
          >
            <X className="h-3.5 w-3.5 text-muted-foreground" />
          </button>
        </div>
      </div>
    </motion.div>
  )
}

// ─── Main Chat Interface ──────────────────────────────────────────────

export function ChatInterface() {
  const isMobile = useIsMobile()
  const [sheetOpen, setSheetOpen] = useState(false)
  const [handoffBanner, setHandoffBanner] = useState<{
    fromName: string
    fromEmoji: string
    fromColor: string
    toName: string
    toEmoji: string
    toColor: string
  } | null>(null)

  const {
    messages,
    currentAgent,
    isStreaming,
    conversationId,
    addMessage,
    updateMessage,
    setStreaming,
    setAgent,
    setConversationId,
    addHandoffMessage,
    clearMessages,
  } = useChatStore()

  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const abortRef = useRef<AbortController | null>(null)

  const currentAgentDef = getAgentByType(currentAgent)

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isStreaming])

  // Focus textarea on agent change
  useEffect(() => {
    if (!isMobile) {
      textareaRef.current?.focus()
    }
  }, [currentAgent, isMobile])

  // Auto-dismiss handoff banner after 5 seconds
  useEffect(() => {
    if (handoffBanner) {
      const timer = setTimeout(() => setHandoffBanner(null), 5000)
      return () => clearTimeout(timer)
    }
  }, [handoffBanner])

  const handleAgentChange = useCallback(
    (type: AgentType) => {
      setAgent(type)
      setSheetOpen(false)
    },
    [setAgent]
  )

  const handleQuickPrompt = useCallback(
    (prompt: string) => {
      setInput(prompt)
      // Auto-send after a tick
      setTimeout(() => {
        handleSend(prompt)
      }, 50)
    },
    [currentAgent, conversationId]
  )

  const handleHandoff = useCallback(
    (data: {
      toAgent: string
      fromAgentName: string
      toAgentName: string
      fromAgentEmoji: string
      toAgentEmoji: string
      reason?: string
    }) => {
      const targetAgent = data.toAgent as AgentType
      const fromAgentDef = getAgentByType(currentAgent)
      const toAgentDef = getAgentByType(targetAgent)

      // Add handoff message to chat
      addHandoffMessage(
        currentAgent,
        targetAgent,
        data.fromAgentName || fromAgentDef.name,
        data.toAgentName || toAgentDef.name,
        data.fromAgentEmoji || fromAgentDef.emoji,
        data.toAgentEmoji || toAgentDef.emoji,
        data.reason
      )

      // Show handoff banner
      setHandoffBanner({
        fromName: data.fromAgentName || fromAgentDef.name,
        fromEmoji: data.fromAgentEmoji || fromAgentDef.emoji,
        fromColor: fromAgentDef.color,
        toName: data.toAgentName || toAgentDef.name,
        toEmoji: data.toAgentEmoji || toAgentDef.emoji,
        toColor: toAgentDef.color,
      })

      // The agent switch is handled inside addHandoffMessage
    },
    [currentAgent, addHandoffMessage]
  )

  const handleSend = useCallback(
    async (messageText?: string) => {
      const text = (messageText ?? input).trim()
      if (!text || isStreaming) return

      setInput('')

      // Create user message
      const userMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'user',
        content: text,
        agentType: currentAgent,
        timestamp: Date.now(),
      }
      addMessage(userMsg)

      // Create placeholder assistant message
      const assistantMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: '',
        agentType: currentAgent,
        timestamp: Date.now(),
        isStreaming: true,
      }
      addMessage(assistantMsg)

      setStreaming(true)

      // Abort any previous request
      if (abortRef.current) {
        abortRef.current.abort()
      }
      const abortController = new AbortController()
      abortRef.current = abortController

      try {
        const response = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: text,
            conversationId,
            agentType: currentAgent,
          }),
          signal: abortController.signal,
        })

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }

        const reader = response.body?.getReader()
        if (!reader) throw new Error('No reader available')

        const decoder = new TextDecoder()
        let buffer = ''
        let accumulated = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })

          // Parse SSE lines from buffer
          const lines = buffer.split('\n')
          buffer = lines.pop() ?? ''

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue
            const data = line.slice(6).trim()

            if (data === '[DONE]') {
              // Stream complete
              updateMessage(assistantMsg.id, { isStreaming: false })
              setStreaming(false)
              return
            }

            try {
              const parsed = JSON.parse(data)

              // Handle metadata event
              if (parsed.type === 'meta' && parsed.conversationId) {
                setConversationId(parsed.conversationId)
                continue
              }

              // ─── Handle handoff event ──────────────────────────────
              if (parsed.type === 'handoff') {
                handleHandoff(parsed)
                continue
              }

              // ─── Handle content-replace event (cleaned handoff content) ─
              if (parsed.type === 'content_replace') {
                updateMessage(assistantMsg.id, {
                  content: parsed.content,
                  isStreaming: false,
                })
                setStreaming(false)
                continue
              }

              // Handle streaming delta content
              const delta = parsed.choices?.[0]?.delta?.content
              if (delta) {
                accumulated += delta
                updateMessage(assistantMsg.id, { content: accumulated })
              }
            } catch {
              // Skip malformed JSON
            }
          }
        }

        // Stream ended without [DONE] — still mark as complete
        updateMessage(assistantMsg.id, { isStreaming: false })
        setStreaming(false)
      } catch (err: unknown) {
        if (err instanceof DOMException && err.name === 'AbortError') {
          // Aborted intentionally — ignore
          return
        }

        console.error('Chat stream error:', err)
        updateMessage(assistantMsg.id, {
          content:
            'Sorry, I encountered an error. Please try again.',
          isStreaming: false,
        })
        setStreaming(false)
      }
    },
    [
      input,
      isStreaming,
      currentAgent,
      conversationId,
      addMessage,
      updateMessage,
      setStreaming,
      setConversationId,
      handleHandoff,
    ]
  )

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleClearChat = () => {
    if (abortRef.current) {
      abortRef.current.abort()
    }
    clearMessages()
    setStreaming(false)
    setHandoffBanner(null)
  }

  return (
    <div className="flex h-[calc(100vh-4rem)] overflow-hidden bg-background relative">
      {/* Desktop Agent Sidebar */}
      {!isMobile && (
        <motion.aside
          initial={{ x: -20, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          transition={{ duration: 0.3 }}
          className="w-72 border-r border-border/50 bg-muted/20 shrink-0"
        >
          <AgentSidebar
            currentAgent={currentAgent}
            onAgentChange={handleAgentChange}
          />
        </motion.aside>
      )}

      {/* Chat Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Chat Header */}
        <motion.div
          initial={{ y: -10, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.3 }}
          className="flex items-center justify-between px-4 py-3 border-b border-border/50 bg-background/80 backdrop-blur-sm"
        >
          <div className="flex items-center gap-3">
            {/* Mobile menu button */}
            {isMobile && (
              <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
                <SheetTrigger asChild>
                  <Button variant="ghost" size="icon" className="shrink-0">
                    <Menu className="h-5 w-5" />
                    <span className="sr-only">Open agents</span>
                  </Button>
                </SheetTrigger>
                <SheetContent side="left" className="w-72 p-0">
                  <SheetHeader className="sr-only">
                    <SheetTitle>AI Agents</SheetTitle>
                  </SheetHeader>
                  <AgentSidebar
                    currentAgent={currentAgent}
                    onAgentChange={handleAgentChange}
                  />
                </SheetContent>
              </Sheet>
            )}

            {/* Current agent info */}
            <div className="flex items-center gap-2.5">
              <AnimatePresence mode="wait">
                <motion.div
                  key={currentAgent}
                  initial={{ scale: 0.5, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  exit={{ scale: 0.5, opacity: 0 }}
                  transition={{ type: 'spring', stiffness: 300, damping: 20 }}
                  className="flex items-center justify-center w-9 h-9 rounded-full text-base shrink-0"
                  style={{
                    backgroundColor: currentAgentDef.color + '18',
                    border: `1.5px solid ${currentAgentDef.color}40`,
                  }}
                >
                  {currentAgentDef.emoji}
                </motion.div>
              </AnimatePresence>
              <div>
                <AnimatePresence mode="wait">
                  <motion.h2
                    key={currentAgent}
                    initial={{ y: 5, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    exit={{ y: -5, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="text-sm font-semibold leading-tight"
                  >
                    {currentAgentDef.name}
                  </motion.h2>
                </AnimatePresence>
                <div className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                  <span className="text-[11px] text-muted-foreground">
                    {isStreaming ? 'Typing...' : 'Online'}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Clear chat button */}
          {messages.length > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleClearChat}
              className="text-muted-foreground hover:text-destructive gap-1.5"
            >
              <Trash2 className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Clear</span>
            </Button>
          )}
        </motion.div>

        {/* Handoff Notification Banner */}
        <AnimatePresence>
          {handoffBanner && (
            <HandoffBanner
              {...handoffBanner}
              onDismiss={() => setHandoffBanner(null)}
            />
          )}
        </AnimatePresence>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto">
          {messages.length === 0 ? (
            <EmptyChatState
              agentType={currentAgent}
              onQuickPrompt={handleQuickPrompt}
            />
          ) : (
            <div className="py-4 space-y-1">
              <AnimatePresence mode="popLayout">
                {messages.map((msg) => (
                  <MessageBubble key={msg.id} message={msg} />
                ))}
              </AnimatePresence>

              {/* Typing indicator */}
              <AnimatePresence>
                {isStreaming &&
                  messages[messages.length - 1]?.content === '' && (
                    <TypingIndicator agentType={currentAgent} />
                  )}
              </AnimatePresence>

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="border-t border-border/50 bg-background/80 backdrop-blur-sm">
          {/* Quick Prompts (context-aware) */}
          {messages.length > 0 && !isStreaming && (
            <div className="px-4 pt-3 flex gap-2 overflow-x-auto pb-0 scrollbar-none">
              {currentAgentDef.quickPrompts.map((prompt) => (
                <motion.button
                  key={prompt}
                  whileHover={{ scale: 1.03 }}
                  whileTap={{ scale: 0.97 }}
                  onClick={() => handleSend(prompt)}
                  className="shrink-0 px-3 py-1.5 rounded-full text-xs border border-border/50 bg-card hover:bg-accent/50 transition-colors whitespace-nowrap"
                >
                  {prompt}
                </motion.button>
              ))}
            </div>
          )}

          <div className="p-4 flex items-end gap-2">
            <div className="flex-1 relative">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={`Ask ${currentAgentDef.name}...`}
                disabled={isStreaming}
                rows={1}
                className="w-full resize-none rounded-xl border border-border/60 bg-card px-4 py-3 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-restaurant-red/30 focus:border-restaurant-red/40 disabled:opacity-50 transition-all min-h-[44px] max-h-[120px] placeholder:text-muted-foreground/50"
                style={{
                  height: 'auto',
                  overflow: input.split('\n').length > 3 ? 'auto' : 'hidden',
                }}
                onInput={(e) => {
                  const target = e.target as HTMLTextAreaElement
                  target.style.height = 'auto'
                  target.style.height = Math.min(target.scrollHeight, 120) + 'px'
                }}
              />
              {input && (
                <button
                  onClick={() => setInput('')}
                  className="absolute right-3 top-3 p-0.5 rounded-full hover:bg-muted/80 transition-colors text-muted-foreground/50 hover:text-muted-foreground"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
            </div>

            <motion.div whileTap={{ scale: 0.9 }}>
              <Button
                onClick={() => handleSend()}
                disabled={!input.trim() || isStreaming}
                size="icon"
                className="h-11 w-11 rounded-xl bg-restaurant-red hover:bg-restaurant-red/90 text-restaurant-red-foreground shadow-md shrink-0"
              >
                <Send className="h-4 w-4" />
                <span className="sr-only">Send message</span>
              </Button>
            </motion.div>
          </div>
        </div>
      </div>
    </div>
  )
}
