'use client'

import { useState, useRef, useCallback, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { format } from 'date-fns'
import {
  Calendar,
  Clock,
  Users,
  Phone,
  Mail,
  ChevronDown,
  Check,
  Minus,
  Plus,
  Send,
  Sparkles,
  User,
  MessageCircle,
  X,
  Loader2,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Calendar as CalendarComponent } from '@/components/ui/calendar'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import type { Reservation } from '@/types'

// ─── Time Slots Generation ──────────────────────────────────────────────

function generateTimeSlots(): { value: string; label: string }[] {
  const slots: { value: string; label: string }[] = []
  for (let hour = 11; hour <= 22; hour++) {
    for (const min of [0, 30]) {
      if (hour === 22 && min > 0) break
      const h12 = hour > 12 ? hour - 12 : hour
      const ampm = hour >= 12 ? 'PM' : 'AM'
      const timeStr = `${hour.toString().padStart(2, '0')}:${min.toString().padStart(2, '0')}`
      const label = `${h12}:${min.toString().padStart(2, '0')} ${ampm}`
      slots.push({ value: timeStr, label })
    }
  }
  return slots
}

const TIME_SLOTS = generateTimeSlots()

const OCCASIONS = [
  { value: 'birthday', label: 'Birthday', emoji: '🎂' },
  { value: 'anniversary', label: 'Anniversary', emoji: '💕' },
  { value: 'business', label: 'Business', emoji: '💼' },
  { value: 'date_night', label: 'Date Night', emoji: '🌹' },
  { value: 'casual', label: 'Casual', emoji: '🍽️' },
  { value: 'other', label: 'Other', emoji: '✨' },
]

// ─── Chat Types ─────────────────────────────────────────────────────────

interface ConciergeMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
}

// ─── Form State ─────────────────────────────────────────────────────────

interface FormState {
  customerName: string
  customerPhone: string
  customerEmail: string
  partySize: number
  date: Date | undefined
  time: string
  occasion: string
  specialRequests: string
}

interface FormErrors {
  customerName?: string
  customerPhone?: string
  partySize?: string
  date?: string
  time?: string
}

// ─── Success Confirmation Card ──────────────────────────────────────────

function SuccessConfirmation({
  reservation,
  onClose,
}: {
  reservation: Reservation
  onClose: () => void
}) {
  const occasionLabel = OCCASIONS.find((o) => o.value === reservation.occasion)?.label

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5, ease: 'easeOut' }}
      className="flex flex-col items-center text-center py-4"
    >
      {/* Animated checkmark */}
      <motion.div
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ type: 'spring', stiffness: 200, damping: 15, delay: 0.2 }}
        className="w-20 h-20 rounded-full bg-gradient-to-br from-emerald-400 to-emerald-600 flex items-center justify-center mb-6 shadow-lg shadow-emerald-500/25"
      >
        <motion.div
          initial={{ scale: 0, rotate: -90 }}
          animate={{ scale: 1, rotate: 0 }}
          transition={{ delay: 0.5, type: 'spring', stiffness: 200 }}
        >
          <Check className="h-10 w-10 text-white" strokeWidth={3} />
        </motion.div>
      </motion.div>

      <motion.h3
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="text-2xl font-bold text-foreground mb-2"
      >
        Reservation Confirmed!
      </motion.h3>

      <motion.p
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        className="text-muted-foreground mb-8"
      >
        We look forward to welcoming you
      </motion.p>

      {/* Reservation Details Card */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
        className="w-full"
      >
        <Card className="border-restaurant-gold/20 bg-gradient-to-br from-restaurant-cream/50 to-transparent dark:from-restaurant-dark/50">
          <CardContent className="p-6 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Name</span>
              <span className="text-sm font-semibold">{reservation.customerName}</span>
            </div>
            <Separator className="bg-border/50" />
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground flex items-center gap-1.5">
                <Calendar className="h-3.5 w-3.5" /> Date
              </span>
              <span className="text-sm font-semibold">{reservation.date}</span>
            </div>
            <Separator className="bg-border/50" />
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground flex items-center gap-1.5">
                <Clock className="h-3.5 w-3.5" /> Time
              </span>
              <span className="text-sm font-semibold">{reservation.time}</span>
            </div>
            <Separator className="bg-border/50" />
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground flex items-center gap-1.5">
                <Users className="h-3.5 w-3.5" /> Party
              </span>
              <span className="text-sm font-semibold">{reservation.partySize} guests</span>
            </div>
            {occasionLabel && (
              <>
                <Separator className="bg-border/50" />
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Occasion</span>
                  <Badge variant="outline" className="border-restaurant-gold/30 text-restaurant-gold">
                    {occasionLabel}
                  </Badge>
                </div>
              </>
            )}
            {reservation.specialRequests && (
              <>
                <Separator className="bg-border/50" />
                <div className="text-left">
                  <span className="text-sm text-muted-foreground block mb-1">Special Requests</span>
                  <p className="text-sm">{reservation.specialRequests}</p>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </motion.div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.8 }}
        className="mt-8 flex gap-3"
      >
        <Button
          onClick={onClose}
          className="bg-restaurant-red hover:bg-restaurant-red/90 text-white gap-2"
        >
          Make Another Reservation
        </Button>
      </motion.div>
    </motion.div>
  )
}

// ─── AI Concierge Mini Chat ─────────────────────────────────────────────

function AIConciergeChat() {
  const [messages, setMessages] = useState<ConciergeMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: "Hello! I'm your reservation concierge. How can I help you book the perfect table?",
    },
  ])
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isStreaming])

  const handleSend = useCallback(
    async (messageText?: string) => {
      const text = (messageText ?? input).trim()
      if (!text || isStreaming) return
      setInput('')

      const userMsg: ConciergeMessage = {
        id: crypto.randomUUID(),
        role: 'user',
        content: text,
      }
      setMessages((prev) => [...prev, userMsg])

      const assistantMsg: ConciergeMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: '',
      }
      setMessages((prev) => [...prev, assistantMsg])
      setIsStreaming(true)

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
            agentType: 'reservation',
          }),
          signal: abortController.signal,
        })

        if (!response.ok) throw new Error(`HTTP ${response.status}`)

        const reader = response.body?.getReader()
        if (!reader) throw new Error('No reader available')

        const decoder = new TextDecoder()
        let buffer = ''
        let accumulated = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })

          const lines = buffer.split('\n')
          buffer = lines.pop() ?? ''

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue
            const data = line.slice(6).trim()

            if (data === '[DONE]') {
              setIsStreaming(false)
              return
            }

            try {
              const parsed = JSON.parse(data)

              if (parsed.type === 'meta' && parsed.conversationId) {
                setConversationId(parsed.conversationId)
                continue
              }

              const delta = parsed.choices?.[0]?.delta?.content
              if (delta) {
                accumulated += delta
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantMsg.id ? { ...m, content: accumulated } : m
                  )
                )
              }
            } catch {
              // Skip malformed JSON
            }
          }
        }

        setIsStreaming(false)
      } catch (err: unknown) {
        if (err instanceof DOMException && err.name === 'AbortError') return
        console.error('Chat error:', err)
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsg.id
              ? { ...m, content: 'Sorry, I encountered an error. Please try again.' }
              : m
          )
        )
        setIsStreaming(false)
      }
    },
    [input, isStreaming, conversationId]
  )

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleSend()
    }
  }

  const quickPrompts = [
    "What's the best time for a quiet dinner?",
    'Do you have private rooms?',
    'Can I request a window seat?',
  ]

  return (
    <Card className="h-full flex flex-col border-restaurant-gold/20 bg-gradient-to-br from-restaurant-cream/30 to-transparent dark:from-restaurant-dark/30">
      <CardHeader className="pb-3 border-b border-border/50">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-restaurant-red to-restaurant-gold flex items-center justify-center shrink-0">
            <Sparkles className="h-5 w-5 text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <CardTitle className="text-sm font-semibold">Reservation Concierge</CardTitle>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-[11px] text-muted-foreground">
                {isStreaming ? 'Typing...' : 'Online'}
              </span>
            </div>
          </div>
          <Badge variant="outline" className="border-restaurant-gold/30 text-restaurant-gold text-[10px] gap-1 shrink-0">
            <MessageCircle className="h-2.5 w-2.5" />
            AI
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col p-0 overflow-hidden">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3 max-h-[380px]">
          <AnimatePresence mode="popLayout">
            {messages.map((msg) => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.25 }}
                className={cn(
                  'flex',
                  msg.role === 'user' ? 'justify-end' : 'justify-start'
                )}
              >
                <div
                  className={cn(
                    'max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed',
                    msg.role === 'user'
                      ? 'bg-restaurant-red/15 text-foreground rounded-br-md'
                      : 'bg-muted/60 text-foreground rounded-bl-md'
                  )}
                >
                  {msg.role === 'assistant' && msg.content === '' && isStreaming ? (
                    <div className="flex items-center gap-1.5 py-1">
                      <motion.div
                        className="w-1.5 h-1.5 rounded-full bg-restaurant-gold"
                        animate={{ opacity: [0.3, 1, 0.3] }}
                        transition={{ duration: 1.2, repeat: Infinity, delay: 0 }}
                      />
                      <motion.div
                        className="w-1.5 h-1.5 rounded-full bg-restaurant-gold"
                        animate={{ opacity: [0.3, 1, 0.3] }}
                        transition={{ duration: 1.2, repeat: Infinity, delay: 0.2 }}
                      />
                      <motion.div
                        className="w-1.5 h-1.5 rounded-full bg-restaurant-gold"
                        animate={{ opacity: [0.3, 1, 0.3] }}
                        transition={{ duration: 1.2, repeat: Infinity, delay: 0.4 }}
                      />
                    </div>
                  ) : (
                    msg.content
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
          <div ref={messagesEndRef} />
        </div>

        {/* Quick Prompts */}
        {messages.length <= 2 && !isStreaming && (
          <div className="px-4 pb-2 flex flex-wrap gap-1.5">
            {quickPrompts.map((prompt) => (
              <motion.button
                key={prompt}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => handleSend(prompt)}
                className="px-2.5 py-1.5 rounded-lg text-[11px] border border-border/50 bg-card hover:bg-accent/50 transition-colors text-left leading-tight"
              >
                {prompt}
              </motion.button>
            ))}
          </div>
        )}

        {/* Input */}
        <div className="p-3 border-t border-border/50">
          <div className="flex items-center gap-2">
            <div className="flex-1 relative">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about reservations..."
                disabled={isStreaming}
                className="w-full h-9 rounded-lg border border-border/60 bg-card px-3 pr-8 text-sm focus:outline-none focus:ring-2 focus:ring-restaurant-red/30 focus:border-restaurant-red/40 disabled:opacity-50 placeholder:text-muted-foreground/50"
              />
              {input && (
                <button
                  onClick={() => setInput('')}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 rounded-full hover:bg-muted/80 transition-colors text-muted-foreground/50 hover:text-muted-foreground"
                >
                  <X className="h-3 w-3" />
                </button>
              )}
            </div>
            <motion.div whileTap={{ scale: 0.9 }}>
              <Button
                onClick={() => handleSend()}
                disabled={!input.trim() || isStreaming}
                size="icon"
                className="h-9 w-9 rounded-lg bg-restaurant-red hover:bg-restaurant-red/90 text-white shrink-0"
              >
                <Send className="h-3.5 w-3.5" />
                <span className="sr-only">Send message</span>
              </Button>
            </motion.div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// ─── Main Reservation Form ───────────────────────────────────────────────

export function ReservationForm() {
  const [form, setForm] = useState<FormState>({
    customerName: '',
    customerPhone: '',
    customerEmail: '',
    partySize: 2,
    date: undefined,
    time: '',
    occasion: '',
    specialRequests: '',
  })
  const [errors, setErrors] = useState<FormErrors>({})
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [confirmedReservation, setConfirmedReservation] = useState<Reservation | null>(null)
  const [calendarOpen, setCalendarOpen] = useState(false)

  const updateField = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }))
    // Clear error when user modifies the field
    if (key in errors) {
      setErrors((prev) => {
        const next = { ...prev }
        delete next[key as keyof FormErrors]
        return next
      })
    }
  }

  const validate = (): boolean => {
    const newErrors: FormErrors = {}

    if (!form.customerName.trim()) {
      newErrors.customerName = 'Name is required'
    }
    if (!form.customerPhone.trim()) {
      newErrors.customerPhone = 'Phone number is required'
    }
    if (form.partySize < 1 || form.partySize > 20) {
      newErrors.partySize = 'Party size must be 1-20'
    }
    if (!form.date) {
      newErrors.date = 'Please select a date'
    } else {
      const today = new Date()
      today.setHours(0, 0, 0, 0)
      if (form.date < today) {
        newErrors.date = 'Date must be today or later'
      }
    }
    if (!form.time) {
      newErrors.time = 'Please select a time'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!validate()) return

    setIsSubmitting(true)

    try {
      const payload = {
        customerName: form.customerName.trim(),
        customerPhone: form.customerPhone.trim(),
        customerEmail: form.customerEmail.trim() || undefined,
        partySize: form.partySize,
        date: form.date ? format(form.date, 'yyyy-MM-dd') : '',
        time: form.time,
        occasion: form.occasion || undefined,
        specialRequests: form.specialRequests.trim() || undefined,
      }

      const response = await fetch('/api/reservations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      const data = await response.json()

      if (!data.success) {
        throw new Error(data.error || 'Failed to create reservation')
      }

      setConfirmedReservation(data.data)
    } catch (err) {
      console.error('Reservation error:', err)
      // Use a simple error display instead of toast for now
      setErrors((prev) => ({
        ...prev,
        customerName: err instanceof Error ? err.message : 'Something went wrong. Please try again.',
      }))
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleReset = () => {
    setForm({
      customerName: '',
      customerPhone: '',
      customerEmail: '',
      partySize: 2,
      date: undefined,
      time: '',
      occasion: '',
      specialRequests: '',
    })
    setErrors({})
    setConfirmedReservation(null)
  }

  // If confirmed, show success dialog
  if (confirmedReservation) {
    return (
      <Dialog open onOpenChange={() => {}} modal>
        <DialogContent className="sm:max-w-md">
          <DialogHeader className="sr-only">
            <DialogTitle>Reservation Confirmed</DialogTitle>
          </DialogHeader>
          <SuccessConfirmation
            reservation={confirmedReservation}
            onClose={handleReset}
          />
        </DialogContent>
      </Dialog>
    )
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 lg:gap-8">
      {/* Left: The Form */}
      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5 }}
        className="lg:col-span-3"
      >
        <Card className="border-border/50 shadow-lg">
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Calendar className="h-5 w-5 text-restaurant-red" />
              Booking Details
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Customer Name */}
              <div className="space-y-2">
                <Label htmlFor="customerName" className="text-sm font-medium">
                  Customer Name <span className="text-restaurant-red">*</span>
                </Label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/50" />
                  <Input
                    id="customerName"
                    value={form.customerName}
                    onChange={(e) => updateField('customerName', e.target.value)}
                    placeholder="Your full name"
                    className={cn(
                      'pl-10',
                      errors.customerName && 'border-destructive focus-visible:ring-destructive/30'
                    )}
                  />
                </div>
                {errors.customerName && (
                  <motion.p
                    initial={{ opacity: 0, y: -5 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="text-xs text-destructive"
                  >
                    {errors.customerName}
                  </motion.p>
                )}
              </div>

              {/* Phone & Email Row */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Phone Number */}
                <div className="space-y-2">
                  <Label htmlFor="customerPhone" className="text-sm font-medium">
                    Phone Number <span className="text-restaurant-red">*</span>
                  </Label>
                  <div className="relative">
                    <Phone className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/50" />
                    <Input
                      id="customerPhone"
                      type="tel"
                      value={form.customerPhone}
                      onChange={(e) => updateField('customerPhone', e.target.value)}
                      placeholder="(555) 123-4567"
                      className={cn(
                        'pl-10',
                        errors.customerPhone && 'border-destructive focus-visible:ring-destructive/30'
                      )}
                    />
                  </div>
                  {errors.customerPhone && (
                    <motion.p
                      initial={{ opacity: 0, y: -5 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="text-xs text-destructive"
                    >
                      {errors.customerPhone}
                    </motion.p>
                  )}
                </div>

                {/* Email */}
                <div className="space-y-2">
                  <Label htmlFor="customerEmail" className="text-sm font-medium">
                    Email <span className="text-muted-foreground text-xs">(optional)</span>
                  </Label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/50" />
                    <Input
                      id="customerEmail"
                      type="email"
                      value={form.customerEmail}
                      onChange={(e) => updateField('customerEmail', e.target.value)}
                      placeholder="you@example.com"
                      className="pl-10"
                    />
                  </div>
                </div>
              </div>

              {/* Party Size */}
              <div className="space-y-2">
                <Label className="text-sm font-medium">
                  Party Size <span className="text-restaurant-red">*</span>
                </Label>
                <div className="flex items-center gap-3">
                  <motion.div whileTap={{ scale: 0.9 }}>
                    <Button
                      type="button"
                      variant="outline"
                      size="icon"
                      className="h-10 w-10 rounded-lg"
                      onClick={() => updateField('partySize', Math.max(1, form.partySize - 1))}
                      disabled={form.partySize <= 1}
                    >
                      <Minus className="h-4 w-4" />
                    </Button>
                  </motion.div>
                  <div className="flex items-center gap-2 min-w-[80px] justify-center">
                    <Users className="h-4 w-4 text-restaurant-red" />
                    <span className="text-xl font-bold tabular-nums">{form.partySize}</span>
                    <span className="text-sm text-muted-foreground">
                      {form.partySize === 1 ? 'guest' : 'guests'}
                    </span>
                  </div>
                  <motion.div whileTap={{ scale: 0.9 }}>
                    <Button
                      type="button"
                      variant="outline"
                      size="icon"
                      className="h-10 w-10 rounded-lg"
                      onClick={() => updateField('partySize', Math.min(20, form.partySize + 1))}
                      disabled={form.partySize >= 20}
                    >
                      <Plus className="h-4 w-4" />
                    </Button>
                  </motion.div>
                </div>
                {errors.partySize && (
                  <motion.p
                    initial={{ opacity: 0, y: -5 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="text-xs text-destructive"
                  >
                    {errors.partySize}
                  </motion.p>
                )}
              </div>

              {/* Date & Time Row */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Date Picker */}
                <div className="space-y-2">
                  <Label className="text-sm font-medium">
                    Date <span className="text-restaurant-red">*</span>
                  </Label>
                  <Popover open={calendarOpen} onOpenChange={setCalendarOpen}>
                    <PopoverTrigger asChild>
                      <Button
                        variant="outline"
                        className={cn(
                          'w-full justify-start text-left font-normal h-10',
                          !form.date && 'text-muted-foreground',
                          errors.date && 'border-destructive'
                        )}
                      >
                        <Calendar className="mr-2 h-4 w-4 text-restaurant-red" />
                        {form.date ? format(form.date, 'PPP') : 'Pick a date'}
                        <ChevronDown className="ml-auto h-4 w-4 opacity-50" />
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-auto p-0" align="start">
                      <CalendarComponent
                        mode="single"
                        selected={form.date}
                        onSelect={(date) => {
                          updateField('date', date)
                          setCalendarOpen(false)
                        }}
                        disabled={{ before: new Date() }}
                        initialFocus
                      />
                    </PopoverContent>
                  </Popover>
                  {errors.date && (
                    <motion.p
                      initial={{ opacity: 0, y: -5 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="text-xs text-destructive"
                    >
                      {errors.date}
                    </motion.p>
                  )}
                </div>

                {/* Time Picker */}
                <div className="space-y-2">
                  <Label className="text-sm font-medium">
                    Time <span className="text-restaurant-red">*</span>
                  </Label>
                  <Select
                    value={form.time}
                    onValueChange={(value) => updateField('time', value)}
                  >
                    <SelectTrigger
                      className={cn(
                        'w-full',
                        !form.time && 'text-muted-foreground',
                        errors.time && 'border-destructive'
                      )}
                    >
                      <Clock className="mr-2 h-4 w-4 text-restaurant-gold" />
                      <SelectValue placeholder="Select time" />
                    </SelectTrigger>
                    <SelectContent className="max-h-[240px]">
                      {TIME_SLOTS.map((slot) => (
                        <SelectItem key={slot.value} value={slot.value}>
                          {slot.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {errors.time && (
                    <motion.p
                      initial={{ opacity: 0, y: -5 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="text-xs text-destructive"
                    >
                      {errors.time}
                    </motion.p>
                  )}
                </div>
              </div>

              {/* Occasion */}
              <div className="space-y-2">
                <Label className="text-sm font-medium">
                  Occasion <span className="text-muted-foreground text-xs">(optional)</span>
                </Label>
                <Select
                  value={form.occasion}
                  onValueChange={(value) => updateField('occasion', value)}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select occasion" />
                  </SelectTrigger>
                  <SelectContent>
                    {OCCASIONS.map((occ) => (
                      <SelectItem key={occ.value} value={occ.value}>
                        <span className="mr-1.5">{occ.emoji}</span>
                        {occ.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Special Requests */}
              <div className="space-y-2">
                <Label htmlFor="specialRequests" className="text-sm font-medium">
                  Special Requests <span className="text-muted-foreground text-xs">(optional)</span>
                </Label>
                <Textarea
                  id="specialRequests"
                  value={form.specialRequests}
                  onChange={(e) => updateField('specialRequests', e.target.value)}
                  placeholder="Dietary needs, seating preferences, accessibility requirements..."
                  className="min-h-[80px] resize-none"
                />
              </div>

              {/* Submit Button */}
              <motion.div whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.99 }}>
                <Button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full h-12 text-base bg-restaurant-red hover:bg-restaurant-red/90 text-white gap-2 shadow-lg shadow-restaurant-red/20"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="h-5 w-5 animate-spin" />
                      Confirming...
                    </>
                  ) : (
                    <>
                      <Check className="h-5 w-5" />
                      Confirm Reservation
                    </>
                  )}
                </Button>
              </motion.div>
            </form>
          </CardContent>
        </Card>
      </motion.div>

      {/* Right: AI Concierge */}
      <motion.div
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5, delay: 0.15 }}
        className="lg:col-span-2"
      >
        <AIConciergeChat />
      </motion.div>
    </div>
  )
}
