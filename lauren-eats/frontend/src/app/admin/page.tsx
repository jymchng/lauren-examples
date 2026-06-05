'use client'

import { motion } from 'framer-motion'
import { UtensilsCrossed, Sparkles, ArrowLeft } from 'lucide-react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import AdminDashboard from '@/components/admin/dashboard'

export default function AdminPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-background/80 backdrop-blur-xl border-b border-border/50">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-4">
              <Link href="/">
                <Button variant="ghost" size="icon" className="h-9 w-9 shrink-0">
                  <ArrowLeft className="h-4 w-4" />
                </Button>
              </Link>
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-restaurant-red to-restaurant-red/80 flex items-center justify-center shadow-md shadow-restaurant-red/20">
                  <UtensilsCrossed className="h-4 w-4 text-white" />
                </div>
                <div>
                  <h1 className="text-lg font-bold text-foreground leading-tight">Dashboard</h1>
                  <p className="text-xs text-muted-foreground">Lauren Eats Admin</p>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Badge variant="outline" className="border-restaurant-gold/30 text-restaurant-gold gap-1">
                <Sparkles className="h-3 w-3" />
                Admin
              </Badge>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >
          <AdminDashboard />
        </motion.div>
      </main>

      {/* Footer */}
      <footer className="border-t border-border/50 mt-auto">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-4">
          <p className="text-xs text-muted-foreground text-center">
            Lauren Eats Admin Dashboard &middot; AI-Powered Restaurant Management
          </p>
        </div>
      </footer>
    </div>
  )
}
