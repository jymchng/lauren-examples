'use client'

import { useState, useEffect, useRef } from 'react'
import Link from 'next/link'
import { motion, useInView } from 'framer-motion'
import {
  Sparkles,
  UtensilsCrossed,
  MessageCircle,
  CalendarDays,
  Star,
  ArrowRight,
  Flame,
  Leaf,
  ChefHat,
  Search,
  Bot,
  Heart,
  WheatOff,
  Send,
  Clock,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import type { MenuItem } from '@/types'

// ─── Animation Variants ──────────────────────────────────────────────

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0 },
}

const fadeIn = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 },
}

const staggerContainer = {
  hidden: {},
  visible: {
    transition: {
      staggerChildren: 0.12,
    },
  },
}

const scaleIn = {
  hidden: { opacity: 0, scale: 0.9 },
  visible: { opacity: 1, scale: 1 },
}

// ─── Section Wrapper with useInView ──────────────────────────────────

function AnimatedSection({
  children,
  className,
  delay = 0,
}: {
  children: React.ReactNode
  className?: string
  delay?: number
}) {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: '-80px' })

  return (
    <motion.section
      ref={ref}
      initial="hidden"
      animate={isInView ? 'visible' : 'hidden'}
      variants={fadeUp}
      transition={{ duration: 0.6, delay, ease: 'easeOut' }}
      className={className}
    >
      {children}
    </motion.section>
  )
}

// ─── Testimonials Data ───────────────────────────────────────────────

const testimonials = [
  {
    name: 'Sarah Chen',
    avatar: 'SC',
    rating: 5,
    text: 'The AI recommended the perfect dishes for our anniversary dinner. The Peking Duck was divine, and the personalized pairing suggestions made the evening unforgettable.',
    occasion: 'Anniversary Dinner',
  },
  {
    name: 'Michael Torres',
    avatar: 'MT',
    rating: 5,
    text: 'As someone with gluten intolerance, the dietary AI agent was a game-changer. It instantly filtered safe options and even suggested modifications. Finally, stress-free dining!',
    occasion: 'Dietary Specialist',
  },
  {
    name: 'Emily Wang',
    avatar: 'EW',
    rating: 5,
    text: 'I chat with the AI every time before visiting. It knows my spice preference, my favorites, and always surprises me with new recommendations. It feels like a personal chef!',
    occasion: 'Regular Customer',
  },
]

// ─── AI Agent Data ───────────────────────────────────────────────────

const aiAgents = [
  {
    icon: ChefHat,
    name: 'Food Recommender',
    description: 'Personalized dish suggestions based on your taste profile, mood, and dining history.',
    color: 'text-restaurant-red',
    bg: 'bg-restaurant-red/10',
    border: 'border-restaurant-red/20',
  },
  {
    icon: Leaf,
    name: 'Dietary Specialist',
    description: 'Expert guidance on allergens, dietary restrictions, and nutritional information for every dish.',
    color: 'text-emerald-600',
    bg: 'bg-emerald-500/10',
    border: 'border-emerald-500/20',
  },
  {
    icon: Bot,
    name: 'Ordering Assistant',
    description: 'Seamless ordering experience with smart pairings, portion suggestions, and quick checkout.',
    color: 'text-restaurant-gold',
    bg: 'bg-restaurant-gold/10',
    border: 'border-restaurant-gold/20',
  },
]

// ─── How It Works Data ───────────────────────────────────────────────

const steps = [
  {
    number: 1,
    icon: Search,
    title: 'Browse & Discover',
    description: 'Explore our authentic Chinese menu featuring traditional flavors and modern twists.',
  },
  {
    number: 2,
    icon: MessageCircle,
    title: 'Chat with AI',
    description: 'Get personalized recommendations from our intelligent AI agents tailored to your preferences.',
  },
  {
    number: 3,
    icon: UtensilsCrossed,
    title: 'Order & Enjoy',
    description: 'Place your order seamlessly and savor a dining experience crafted just for you.',
  },
]

// ─── Floating Food Emoji Data ────────────────────────────────────────

const floatingEmojis = [
  { emoji: '🥟', x: '10%', y: '20%', delay: 0, duration: 4 },
  { emoji: '🍜', x: '80%', y: '15%', delay: 0.5, duration: 3.5 },
  { emoji: '🥢', x: '70%', y: '65%', delay: 1, duration: 4.5 },
  { emoji: '🌶️', x: '20%', y: '70%', delay: 1.5, duration: 3.8 },
  { emoji: '🦆', x: '90%', y: '40%', delay: 0.8, duration: 4.2 },
  { emoji: '🍚', x: '5%', y: '45%', delay: 1.2, duration: 3.6 },
]

// ─── Hero Component ──────────────────────────────────────────────────

function HeroSection() {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden bg-gradient-to-br from-restaurant-dark via-[#2A1510] to-[#1A0A05]">
      {/* Dramatic gradient overlays */}
      <div className="absolute inset-0">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-restaurant-red/15 rounded-full blur-[120px]" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-restaurant-gold/10 rounded-full blur-[120px]" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-restaurant-red/5 rounded-full blur-[150px]" />
      </div>

      {/* Chinese pattern overlay */}
      <div className="absolute inset-0 chinese-pattern" />

      {/* Floating food emojis */}
      {floatingEmojis.map((item, i) => (
        <motion.div
          key={i}
          className="absolute text-4xl sm:text-5xl pointer-events-none select-none opacity-20"
          style={{ left: item.x, top: item.y }}
          animate={{ y: [-10, 10, -10] }}
          transition={{
            duration: item.duration,
            delay: item.delay,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        >
          {item.emoji}
        </motion.div>
      ))}

      {/* Content */}
      <div className="relative z-10 mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-32 text-center">
        {/* Badge */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
        >
          <Badge
            variant="outline"
            className="mb-8 px-5 py-2 text-sm border-restaurant-gold/30 text-restaurant-gold bg-restaurant-gold/5 backdrop-blur-sm"
          >
            <Sparkles className="h-3.5 w-3.5 mr-2" />
            AI-Powered Dining Experience
          </Badge>
        </motion.div>

        {/* Main Headline */}
        <motion.h1
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.15 }}
          className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight text-white max-w-4xl mx-auto leading-[1.1]"
        >
          Experience Chinese Cuisine,{' '}
          <span className="bg-gradient-to-r from-restaurant-red via-restaurant-gold to-restaurant-red bg-clip-text text-transparent animate-shimmer-gold">
            Reimagined with AI
          </span>
        </motion.h1>

        {/* Subheading */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="mt-6 text-lg sm:text-xl text-white/60 max-w-2xl mx-auto leading-relaxed"
        >
          From smart recommendations to seamless ordering — our AI agents craft
          a dining experience uniquely tailored to your taste.
        </motion.p>

        {/* CTA Buttons */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.45 }}
          className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4"
        >
          <Link href="/menu">
            <Button
              size="lg"
              className="bg-restaurant-red hover:bg-restaurant-red/90 text-white gap-2 shadow-lg shadow-restaurant-red/25 px-8 h-12 text-base"
            >
              <UtensilsCrossed className="h-5 w-5" />
              Start Ordering
            </Button>
          </Link>
          <Link href="/chat">
            <Button
              size="lg"
              className="bg-gradient-to-r from-restaurant-gold to-[#E8C55A] hover:from-restaurant-gold/90 hover:to-[#E8C55A]/90 text-restaurant-dark gap-2 shadow-lg shadow-restaurant-gold/20 px-8 h-12 text-base"
            >
              <MessageCircle className="h-5 w-5" />
              Chat with AI
            </Button>
          </Link>
        </motion.div>

        {/* AI Chat Bubble Preview */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.7 }}
          className="mt-16 max-w-lg mx-auto"
        >
          <div className="relative bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-5 shadow-2xl">
            {/* Chat header */}
            <div className="flex items-center gap-2 mb-4 pb-3 border-b border-white/10">
              <div className="w-8 h-8 rounded-full bg-restaurant-red flex items-center justify-center">
                <Sparkles className="h-4 w-4 text-white" />
              </div>
              <div className="text-left">
                <p className="text-sm font-semibold text-white">Lauren AI</p>
                <p className="text-[10px] text-restaurant-gold">Food Recommender</p>
              </div>
              <div className="ml-auto flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-[10px] text-emerald-400">Online</span>
              </div>
            </div>

            {/* Sample messages */}
            <div className="space-y-3">
              <div className="flex justify-end">
                <div className="bg-restaurant-red/20 text-white/90 text-sm rounded-2xl rounded-br-md px-4 py-2 max-w-[80%]">
                  I&apos;m craving something spicy but not too heavy. Any suggestions?
                </div>
              </div>
              <div className="flex justify-start">
                <div className="bg-white/10 text-white/80 text-sm rounded-2xl rounded-bl-md px-4 py-2.5 max-w-[85%]">
                  I&apos;d recommend our{' '}
                  <span className="text-restaurant-gold font-medium">Kung Pao Chicken</span>{' '}
                  — it&apos;s our signature Sichuan dish with the perfect balance of heat and flavor.
                  Pair it with{' '}
                  <span className="text-restaurant-gold font-medium">Dry-Fried Green Beans</span>{' '}
                  for a satisfying meal! 🌶️
                </div>
              </div>
            </div>

            {/* Chat input mockup */}
            <div className="mt-4 flex items-center gap-2 bg-white/5 rounded-xl px-3 py-2">
              <span className="text-xs text-white/30 flex-1 text-left">Ask about our menu...</span>
              <div className="w-7 h-7 rounded-lg bg-restaurant-red/80 flex items-center justify-center">
                <Send className="h-3.5 w-3.5 text-white" />
              </div>
            </div>
          </div>
        </motion.div>

        {/* Scroll indicator */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.5, duration: 0.8 }}
          className="mt-12"
        >
          <motion.div
            animate={{ y: [0, 8, 0] }}
            transition={{ repeat: Infinity, duration: 2, ease: 'easeInOut' }}
            className="w-6 h-10 rounded-full border-2 border-white/20 flex items-start justify-center pt-1.5 mx-auto"
          >
            <div className="w-1.5 h-1.5 rounded-full bg-white/30" />
          </motion.div>
        </motion.div>
      </div>
    </section>
  )
}

// ─── Featured Dishes Component ───────────────────────────────────────

function FeaturedDishesSection() {
  const [dishes, setDishes] = useState<MenuItem[]>([])
  const [loading, setLoading] = useState(true)
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: '-100px' })

  useEffect(() => {
    async function fetchDishes() {
      try {
        const res = await fetch('/api/menu?isPopular=true')
        const data = await res.json()
        if (data.success && data.data) {
          setDishes(data.data.slice(0, 6))
        }
      } catch {
        // silently fail, will show fallback
      } finally {
        setLoading(false)
      }
    }
    fetchDishes()
  }, [])

  const gradients = [
    'from-restaurant-red/25 via-restaurant-gold/10 to-restaurant-red/5',
    'from-restaurant-gold/20 via-restaurant-red/10 to-restaurant-gold/5',
    'from-emerald-500/15 via-restaurant-gold/10 to-restaurant-red/5',
    'from-restaurant-red/20 via-emerald-500/10 to-restaurant-gold/5',
    'from-restaurant-gold/15 via-restaurant-red/15 to-restaurant-red/5',
    'from-restaurant-red/15 via-restaurant-gold/15 to-emerald-500/5',
  ]

  return (
    <section ref={ref} className="py-24 bg-restaurant-cream/40 dark:bg-restaurant-dark/40">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <motion.div
          initial="hidden"
          animate={isInView ? 'visible' : 'hidden'}
          variants={fadeUp}
          transition={{ duration: 0.6 }}
          className="text-center mb-14"
        >
          <Badge variant="outline" className="mb-4 border-restaurant-gold/40 text-restaurant-gold">
            <Flame className="h-3 w-3 mr-1" />
            Chef&apos;s Picks
          </Badge>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight">
            Featured <span className="text-restaurant-red">Dishes</span>
          </h2>
          <p className="mt-4 text-muted-foreground max-w-xl mx-auto text-lg">
            Curated by our master chefs and refined by AI — every dish tells a story
            of heritage and innovation.
          </p>
        </motion.div>

        {/* Dish Cards Grid */}
        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {Array.from({ length: 6 }).map((_, i) => (
              <Card key={i} className="overflow-hidden border-border/50">
                <div className="h-44 bg-muted animate-pulse" />
                <CardContent className="p-5">
                  <div className="h-5 w-3/4 bg-muted rounded animate-pulse mb-3" />
                  <div className="h-4 w-1/2 bg-muted rounded animate-pulse" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <motion.div
            initial="hidden"
            animate={isInView ? 'visible' : 'hidden'}
            variants={staggerContainer}
            className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6"
          >
            {dishes.map((dish, i) => (
              <motion.div key={dish.id} variants={fadeUp} transition={{ duration: 0.5 }}>
                <Card className="h-full overflow-hidden border-border/50 hover:border-restaurant-red/20 hover:shadow-xl transition-all duration-300 group cursor-pointer">
                  {/* Dish Image Placeholder */}
                  <div className={cn(
                    'h-44 bg-gradient-to-br flex items-center justify-center relative overflow-hidden',
                    gradients[i % gradients.length]
                  )}>
                    <div className="absolute inset-0 chinese-pattern" />
                    <span className="text-6xl group-hover:scale-110 transition-transform duration-300 drop-shadow-lg">
                      {dish.image || '🍽️'}
                    </span>
                    {/* Popular badge */}
                    {dish.isPopular && (
                      <Badge className="absolute top-3 right-3 bg-restaurant-red text-white border-0 text-[10px] gap-1">
                        <Star className="h-2.5 w-2.5 fill-white" />
                        Popular
                      </Badge>
                    )}
                  </div>

                  <CardContent className="p-5">
                    {/* Name & Chinese name */}
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <div>
                        <h3 className="font-semibold text-foreground leading-tight">{dish.name}</h3>
                        {dish.nameZh && (
                          <p className="text-xs text-restaurant-gold mt-0.5">{dish.nameZh}</p>
                        )}
                      </div>
                      <span className="text-lg font-bold text-restaurant-red whitespace-nowrap">
                        ${dish.price.toFixed(2)}
                      </span>
                    </div>

                    {/* Spicy & Dietary badges */}
                    <div className="flex items-center gap-2 mt-3 flex-wrap">
                      {dish.spicyLevel > 0 && (
                        <Badge variant="outline" className="gap-1 text-[10px] border-restaurant-red/30 text-restaurant-red">
                          <Flame className="h-2.5 w-2.5 fill-restaurant-red" />
                          {dish.spicyLevel <= 2 ? 'Mild' : dish.spicyLevel <= 3 ? 'Spicy' : 'Hot'}
                        </Badge>
                      )}
                      {dish.isVegetarian && (
                        <Badge variant="outline" className="gap-1 text-[10px] border-emerald-500/30 text-emerald-600">
                          <Leaf className="h-2.5 w-2.5" />
                          Veggie
                        </Badge>
                      )}
                      {dish.isVegan && (
                        <Badge variant="outline" className="gap-1 text-[10px] border-emerald-500/30 text-emerald-600">
                          <Leaf className="h-2.5 w-2.5 fill-emerald-600" />
                          Vegan
                        </Badge>
                      )}
                      {dish.isGlutenFree && (
                        <Badge variant="outline" className="gap-1 text-[10px] border-amber-500/30 text-amber-600">
                          <WheatOff className="h-2.5 w-2.5" />
                          GF
                        </Badge>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </motion.div>
        )}

        {/* View Full Menu CTA */}
        <motion.div
          initial="hidden"
          animate={isInView ? 'visible' : 'hidden'}
          variants={fadeUp}
          transition={{ duration: 0.5, delay: 0.4 }}
          className="mt-12 text-center"
        >
          <Link href="/menu">
            <Button
              size="lg"
              variant="outline"
              className="gap-2 border-restaurant-red/30 text-restaurant-red hover:bg-restaurant-red/10 hover:text-restaurant-red h-11 px-8"
            >
              View Full Menu
              <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
        </motion.div>
      </div>
    </section>
  )
}

// ─── AI Assistant CTA Component ──────────────────────────────────────

function AIAssistantSection() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: '-100px' })

  return (
    <section ref={ref} className="py-24 bg-background">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-center">
          {/* Left: Description */}
          <motion.div
            initial="hidden"
            animate={isInView ? 'visible' : 'hidden'}
            variants={staggerContainer}
          >
            <motion.div variants={fadeUp} transition={{ duration: 0.5 }}>
              <Badge variant="outline" className="mb-4 border-restaurant-red/30 text-restaurant-red">
                <Sparkles className="h-3 w-3 mr-1" />
                AI Assistant
              </Badge>
              <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight mb-6">
                Your Personal{' '}
                <span className="text-restaurant-red">AI Dining</span>{' '}
                Concierge
              </h2>
              <p className="text-lg text-muted-foreground leading-relaxed mb-8">
                Our intelligent AI agents understand your preferences, dietary needs,
                and cravings — delivering personalized recommendations that make every
                meal extraordinary.
              </p>
            </motion.div>

            {/* Agent Cards */}
            <div className="space-y-4">
              {aiAgents.map((agent) => {
                const Icon = agent.icon
                return (
                  <motion.div
                    key={agent.name}
                    variants={fadeUp}
                    transition={{ duration: 0.5 }}
                  >
                    <Card className={cn(
                      'border hover:shadow-md transition-all duration-300 group cursor-pointer',
                      agent.border
                    )}>
                      <CardContent className="p-4 flex items-start gap-4">
                        <div className={cn(
                          'inline-flex items-center justify-center w-11 h-11 rounded-xl shrink-0 group-hover:scale-110 transition-transform',
                          agent.bg, agent.color
                        )}>
                          <Icon className="h-5 w-5" />
                        </div>
                        <div>
                          <h3 className="font-semibold text-foreground mb-0.5">{agent.name}</h3>
                          <p className="text-sm text-muted-foreground leading-relaxed">
                            {agent.description}
                          </p>
                        </div>
                      </CardContent>
                    </Card>
                  </motion.div>
                )
              })}
            </div>

            <motion.div variants={fadeUp} transition={{ duration: 0.5 }} className="mt-8">
              <Link href="/chat">
                <Button
                  size="lg"
                  className="bg-restaurant-red hover:bg-restaurant-red/90 text-white gap-2 shadow-lg shadow-restaurant-red/20 px-8 h-12"
                >
                  <Sparkles className="h-4 w-4" />
                  Try AI Assistant
                </Button>
              </Link>
            </motion.div>
          </motion.div>

          {/* Right: Animated Chat Mockup */}
          <motion.div
            initial="hidden"
            animate={isInView ? 'visible' : 'hidden'}
            variants={scaleIn}
            transition={{ duration: 0.7, delay: 0.2 }}
            className="relative"
          >
            {/* Pulsing glow */}
            <div className="absolute inset-0 -m-8 bg-restaurant-red/5 rounded-3xl blur-2xl animate-pulse-glow" />

            <div className="relative bg-gradient-to-br from-restaurant-dark to-[#2A1510] rounded-2xl border border-white/10 p-6 shadow-2xl">
              {/* Chat header */}
              <div className="flex items-center gap-3 mb-6 pb-4 border-b border-white/10">
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-restaurant-red to-restaurant-gold flex items-center justify-center">
                  <Sparkles className="h-5 w-5 text-white" />
                </div>
                <div>
                  <p className="font-semibold text-white">Lauren AI Concierge</p>
                  <div className="flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                    <span className="text-xs text-emerald-400">3 agents active</span>
                  </div>
                </div>
              </div>

              {/* Animated chat messages */}
              <div className="space-y-4">
                <div className="flex justify-end">
                  <div className="bg-restaurant-red/20 text-white/90 text-sm rounded-2xl rounded-br-md px-4 py-2.5 max-w-[80%]">
                    Can you recommend something for a date night? 🌹
                  </div>
                </div>

                <div className="flex justify-start gap-2">
                  <div className="w-7 h-7 rounded-full bg-restaurant-gold/20 flex items-center justify-center shrink-0 mt-1">
                    <ChefHat className="h-3.5 w-3.5 text-restaurant-gold" />
                  </div>
                  <div className="bg-white/8 text-white/80 text-sm rounded-2xl rounded-bl-md px-4 py-2.5 max-w-[85%]">
                    For a romantic evening, I&apos;d suggest starting with our{' '}
                    <span className="text-restaurant-gold font-medium">Har Gow</span>,
                    followed by the{' '}
                    <span className="text-restaurant-gold font-medium">Crispy Peking Duck</span>{' '}
                    — perfect for sharing! Pair it with a pot of Jasmine tea. 🍵
                  </div>
                </div>

                <div className="flex justify-start gap-2">
                  <div className="w-7 h-7 rounded-full bg-emerald-500/20 flex items-center justify-center shrink-0 mt-1">
                    <Leaf className="h-3.5 w-3.5 text-emerald-400" />
                  </div>
                  <div className="bg-white/8 text-white/80 text-sm rounded-2xl rounded-bl-md px-4 py-2.5 max-w-[85%]">
                    Just a note — the Peking Duck contains wheat and soy.
                    If you need gluten-free options, I can suggest alternatives! 🌿
                  </div>
                </div>

                <div className="flex justify-end">
                  <div className="bg-restaurant-red/20 text-white/90 text-sm rounded-2xl rounded-br-md px-4 py-2.5 max-w-[80%]">
                    That sounds perfect! Let&apos;s go with that. 😍
                  </div>
                </div>

                <div className="flex justify-start gap-2">
                  <div className="w-7 h-7 rounded-full bg-restaurant-gold/20 flex items-center justify-center shrink-0 mt-1">
                    <Bot className="h-3.5 w-3.5 text-restaurant-gold" />
                  </div>
                  <div className="bg-gradient-to-r from-restaurant-red/15 to-restaurant-gold/10 text-white/80 text-sm rounded-2xl rounded-bl-md px-4 py-2.5 max-w-[85%] border border-restaurant-gold/20">
                    <span className="text-restaurant-gold font-medium">Order placed!</span>{' '}
                    Your Peking Duck and Har Gow will be ready in ~45 min.
                    I&apos;ve also added complimentary sesame balls for your date night. 🎉
                  </div>
                </div>
              </div>

              {/* Input mockup */}
              <div className="mt-5 flex items-center gap-2 bg-white/5 rounded-xl px-4 py-3 border border-white/5">
                <span className="text-sm text-white/25 flex-1 text-left">Ask Lauren anything...</span>
                <div className="w-8 h-8 rounded-lg bg-gradient-to-r from-restaurant-red to-restaurant-gold flex items-center justify-center">
                  <Send className="h-4 w-4 text-white" />
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  )
}

// ─── How It Works Component ──────────────────────────────────────────

function HowItWorksSection() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: '-100px' })

  return (
    <section ref={ref} className="py-24 bg-restaurant-cream/40 dark:bg-restaurant-dark/40">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <motion.div
          initial="hidden"
          animate={isInView ? 'visible' : 'hidden'}
          variants={fadeUp}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <Badge variant="outline" className="mb-4 border-restaurant-gold/40 text-restaurant-gold">
            <Clock className="h-3 w-3 mr-1" />
            How It Works
          </Badge>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight">
            Three Simple <span className="text-restaurant-gold">Steps</span>
          </h2>
          <p className="mt-4 text-muted-foreground max-w-xl mx-auto text-lg">
            From discovery to delight — your AI-powered dining journey.
          </p>
        </motion.div>

        {/* Steps */}
        <div className="relative">
          {/* Connecting line (desktop) */}
          <div className="hidden lg:block absolute top-1/2 left-[16.7%] right-[16.7%] h-0.5 bg-gradient-to-r from-restaurant-red/20 via-restaurant-gold/30 to-restaurant-red/20 -translate-y-1/2" />

          <motion.div
            initial="hidden"
            animate={isInView ? 'visible' : 'hidden'}
            variants={staggerContainer}
            className="grid grid-cols-1 lg:grid-cols-3 gap-8 lg:gap-12"
          >
            {steps.map((step) => {
              const Icon = step.icon
              return (
                <motion.div
                  key={step.number}
                  variants={fadeUp}
                  transition={{ duration: 0.5 }}
                  className="relative text-center"
                >
                  <div className="flex flex-col items-center">
                    {/* Numbered circle */}
                    <div className="relative mb-6">
                      <div className="w-20 h-20 rounded-full bg-gradient-to-br from-restaurant-red to-restaurant-red/80 flex items-center justify-center shadow-lg shadow-restaurant-red/20">
                        <Icon className="h-8 w-8 text-white" />
                      </div>
                      <div className="absolute -top-1 -right-1 w-7 h-7 rounded-full bg-restaurant-gold text-restaurant-dark flex items-center justify-center text-xs font-bold shadow-md">
                        {step.number}
                      </div>
                    </div>

                    {/* Title & Description */}
                    <h3 className="text-xl font-bold text-foreground mb-2">{step.title}</h3>
                    <p className="text-muted-foreground leading-relaxed max-w-xs">
                      {step.description}
                    </p>
                  </div>
                </motion.div>
              )
            })}
          </motion.div>
        </div>
      </div>
    </section>
  )
}

// ─── Testimonials Component ──────────────────────────────────────────

function TestimonialsSection() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: '-100px' })

  return (
    <section ref={ref} className="py-24 bg-background">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <motion.div
          initial="hidden"
          animate={isInView ? 'visible' : 'hidden'}
          variants={fadeUp}
          transition={{ duration: 0.6 }}
          className="text-center mb-14"
        >
          <Badge variant="outline" className="mb-4 border-restaurant-red/30 text-restaurant-red">
            <Heart className="h-3 w-3 mr-1" />
            Testimonials
          </Badge>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight">
            Loved by <span className="text-restaurant-red">Food Lovers</span>
          </h2>
          <p className="mt-4 text-muted-foreground max-w-xl mx-auto text-lg">
            See what our guests are saying about their AI-powered dining experience.
          </p>
        </motion.div>

        {/* Testimonial Cards */}
        <motion.div
          initial="hidden"
          animate={isInView ? 'visible' : 'hidden'}
          variants={staggerContainer}
          className="grid grid-cols-1 md:grid-cols-3 gap-6"
        >
          {testimonials.map((testimonial, i) => (
            <motion.div
              key={testimonial.name}
              variants={fadeUp}
              transition={{ duration: 0.5, delay: i * 0.1 }}
            >
              <Card className="h-full border-border/50 hover:border-restaurant-red/20 hover:shadow-lg transition-all duration-300 group">
                <CardContent className="p-6">
                  {/* Stars */}
                  <div className="flex items-center gap-0.5 mb-4">
                    {Array.from({ length: testimonial.rating }).map((_, j) => (
                      <Star
                        key={j}
                        className="h-4 w-4 text-restaurant-gold fill-restaurant-gold"
                      />
                    ))}
                  </div>

                  {/* Quote */}
                  <p className="text-foreground/80 leading-relaxed mb-6 text-sm">
                    &ldquo;{testimonial.text}&rdquo;
                  </p>

                  {/* Author */}
                  <div className="flex items-center gap-3 pt-4 border-t border-border/50">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-restaurant-red to-restaurant-gold flex items-center justify-center text-white text-sm font-bold">
                      {testimonial.avatar}
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-foreground">{testimonial.name}</p>
                      <p className="text-xs text-muted-foreground">{testimonial.occasion}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  )
}

// ─── Reservation CTA Component ───────────────────────────────────────

function ReservationCTASection() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: '-100px' })

  return (
    <section ref={ref} className="py-24">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <motion.div
          initial="hidden"
          animate={isInView ? 'visible' : 'hidden'}
          variants={scaleIn}
          transition={{ duration: 0.6 }}
          className="relative rounded-3xl overflow-hidden"
        >
          {/* Background */}
          <div className="absolute inset-0 bg-gradient-to-br from-restaurant-red via-[#9A1830] to-restaurant-dark" />
          <div className="absolute inset-0 chinese-pattern" />

          {/* Decorative glow */}
          <div className="absolute top-0 right-0 w-72 h-72 bg-restaurant-gold/10 rounded-full blur-[100px]" />
          <div className="absolute bottom-0 left-0 w-72 h-72 bg-restaurant-red/20 rounded-full blur-[100px]" />

          {/* Content */}
          <div className="relative px-8 py-16 sm:px-16 sm:py-20 text-center">
            <motion.div
              initial="hidden"
              animate={isInView ? 'visible' : 'hidden'}
              variants={staggerContainer}
            >
              <motion.div variants={fadeUp} transition={{ duration: 0.5 }}>
                <CalendarDays className="h-10 w-10 text-restaurant-gold mx-auto mb-6" />
              </motion.div>

              <motion.h2
                variants={fadeUp}
                transition={{ duration: 0.5, delay: 0.1 }}
                className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-4"
              >
                Reserve Your Table
              </motion.h2>

              <motion.p
                variants={fadeUp}
                transition={{ duration: 0.5, delay: 0.2 }}
                className="text-white/60 max-w-lg mx-auto mb-10 text-lg leading-relaxed"
              >
                Experience the perfect blend of traditional Chinese cuisine and
                AI-powered hospitality. Book your table and let us craft an
                unforgettable evening.
              </motion.p>

              <motion.div
                variants={fadeUp}
                transition={{ duration: 0.5, delay: 0.3 }}
                className="flex flex-col sm:flex-row items-center justify-center gap-4"
              >
                <Link href="/reservation">
                  <Button
                    size="lg"
                    className="bg-white text-restaurant-red hover:bg-white/90 gap-2 shadow-lg px-8 h-12 text-base"
                  >
                    <CalendarDays className="h-5 w-5" />
                    Make a Reservation
                  </Button>
                </Link>
                <Link href="/chat">
                  <Button
                    size="lg"
                    variant="outline"
                    className="border-white/20 text-white hover:bg-white/10 gap-2 h-12 px-8 text-base"
                  >
                    <MessageCircle className="h-5 w-5" />
                    Ask Our AI
                  </Button>
                </Link>
              </motion.div>

              {/* Decorative elements */}
              <motion.div
                variants={fadeIn}
                transition={{ duration: 0.8, delay: 0.5 }}
                className="mt-12 flex items-center justify-center gap-6 text-white/30"
              >
                <span className="text-3xl">🥟</span>
                <span className="text-3xl">🥢</span>
                <span className="text-3xl">🍜</span>
                <span className="text-3xl">🦆</span>
                <span className="text-3xl">🌶️</span>
              </motion.div>
            </motion.div>
          </div>
        </motion.div>
      </div>
    </section>
  )
}

// ─── Main Page Component ─────────────────────────────────────────────

export default function Home() {
  return (
    <div className="flex flex-col">
      <HeroSection />
      <FeaturedDishesSection />
      <AIAssistantSection />
      <HowItWorksSection />
      <TestimonialsSection />
      <ReservationCTASection />
    </div>
  )
}
