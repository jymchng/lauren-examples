'use client'

import { motion } from 'framer-motion'
import { CalendarDays, Sparkles } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { ReservationForm } from '@/components/reservation/reservation-form'

export default function ReservationPage() {
  return (
    <div className="relative min-h-[calc(100vh-4rem)]">
      {/* Background with subtle Chinese pattern */}
      <div className="absolute inset-0 bg-gradient-to-b from-restaurant-cream/30 via-background to-background dark:from-restaurant-dark/20" />
      <div className="absolute inset-0 chinese-pattern" />

      {/* Decorative gradient orbs */}
      <div className="absolute top-0 left-1/4 w-72 h-72 bg-restaurant-red/8 rounded-full blur-[100px]" />
      <div className="absolute bottom-1/4 right-1/6 w-64 h-64 bg-restaurant-gold/8 rounded-full blur-[100px]" />

      {/* Content */}
      <div className="relative z-10 mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8 sm:py-12">
        {/* Page Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="text-center mb-8 sm:mb-10"
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.4 }}
          >
            <Badge
              variant="outline"
              className="mb-4 px-4 py-1.5 text-sm border-restaurant-gold/30 text-restaurant-gold bg-restaurant-gold/5"
            >
              <Sparkles className="h-3.5 w-3.5 mr-1.5" />
              AI-Powered Booking
            </Badge>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
          >
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight text-foreground">
              Reserve a <span className="text-restaurant-red">Table</span>
            </h1>
            <p className="mt-1 text-restaurant-gold font-medium text-lg tracking-widest">
              预订座位
            </p>
          </motion.div>

          <motion.p
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="mt-4 text-muted-foreground max-w-xl mx-auto text-base leading-relaxed"
          >
            Experience the art of Chinese dining in an ambiance where tradition
            meets innovation. Let our AI concierge help you find the perfect
            table for any occasion.
          </motion.p>
        </motion.div>

        {/* Quick Info Badges */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.35 }}
          className="flex flex-wrap items-center justify-center gap-3 mb-8 sm:mb-10"
        >
          <Badge variant="secondary" className="gap-1.5 py-1.5 px-3 text-xs">
            <CalendarDays className="h-3 w-3 text-restaurant-red" />
            Table Booking
          </Badge>
          <Badge variant="secondary" className="gap-1.5 py-1.5 px-3 text-xs">
            🕐 Lunch: 11 AM – 3 PM
          </Badge>
          <Badge variant="secondary" className="gap-1.5 py-1.5 px-3 text-xs">
            🌙 Dinner: 5 PM – 10 PM
          </Badge>
          <Badge variant="secondary" className="gap-1.5 py-1.5 px-3 text-xs">
            👥 Up to 20 guests
          </Badge>
        </motion.div>

        {/* Reservation Form + AI Concierge */}
        <ReservationForm />
      </div>
    </div>
  )
}
