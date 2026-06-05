'use client'

import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { UtensilsCrossed } from 'lucide-react'
import { MenuPageClient } from '@/components/menu/menu-page-client'
import type { Category, MenuItem } from '@/types'

export default function MenuPage() {
  const [categories, setCategories] = useState<Category[]>([])
  const [menuItems, setMenuItems] = useState<MenuItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchData() {
      try {
        const [catRes, menuRes] = await Promise.all([
          fetch('/api/categories'),
          fetch('/api/menu?limit=50'), // Load first page with generous limit
        ])

        const catData = await catRes.json()
        const menuData = await menuRes.json()

        if (catData.success) {
          setCategories(catData.data)
        } else {
          setError('Failed to load categories')
        }

        if (menuData.success) {
          setMenuItems(menuData.data)
        } else {
          setError('Failed to load menu items')
        }
      } catch (err) {
        console.error('Error fetching menu data:', err)
        setError('Failed to load menu. Please try again.')
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  if (loading) {
    return (
      <div className="min-h-screen bg-restaurant-cream/30 dark:bg-restaurant-dark/20 flex items-center justify-center">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex flex-col items-center gap-4"
        >
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ repeat: Infinity, duration: 2, ease: 'linear' }}
          >
            <UtensilsCrossed className="h-10 w-10 text-restaurant-red/50" />
          </motion.div>
          <div className="text-center">
            <p className="text-lg font-medium text-foreground">Loading Menu</p>
            <p className="text-sm text-muted-foreground mt-1">Preparing your dining experience...</p>
          </div>
          {/* Skeleton grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-4 w-full max-w-5xl px-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <div
                key={i}
                className="rounded-xl border border-border/50 overflow-hidden animate-pulse"
              >
                <div className="h-40 bg-muted/30" />
                <div className="p-4 space-y-3">
                  <div className="h-4 bg-muted/30 rounded w-3/4" />
                  <div className="h-3 bg-muted/20 rounded w-1/2" />
                  <div className="h-3 bg-muted/20 rounded w-full" />
                  <div className="h-8 bg-muted/20 rounded" />
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-restaurant-cream/30 dark:bg-restaurant-dark/20 flex items-center justify-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center max-w-md px-4"
        >
          <div className="w-16 h-16 rounded-full bg-restaurant-red/10 flex items-center justify-center mx-auto mb-4">
            <span className="text-2xl">😔</span>
          </div>
          <p className="text-lg font-medium text-foreground">Something went wrong</p>
          <p className="text-sm text-muted-foreground mt-1">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 text-sm text-restaurant-red hover:underline"
          >
            Try again
          </button>
        </motion.div>
      </div>
    )
  }

  return <MenuPageClient categories={categories} initialItems={menuItems} />
}
