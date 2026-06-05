'use client'

import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Package, UtensilsCrossed } from 'lucide-react'
import { OrderList } from '@/components/orders/order-list'
import type { Order } from '@/types'

export default function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchOrders() {
      try {
        const res = await fetch('/api/orders')
        const data = await res.json()

        if (data.success) {
          setOrders(data.data)
        } else {
          setError('Failed to load orders')
        }
      } catch (err) {
        console.error('Error fetching orders:', err)
        setError('Failed to load orders. Please try again.')
      } finally {
        setLoading(false)
      }
    }

    fetchOrders()
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
            <Package className="h-10 w-10 text-restaurant-red/50" />
          </motion.div>
          <div className="text-center">
            <p className="text-lg font-medium text-foreground">
              Loading Orders
            </p>
            <p className="text-sm text-muted-foreground mt-1">
              Fetching your order history...
            </p>
            <p className="text-xs text-muted-foreground/60 mt-0.5">
              正在加载订单...
            </p>
          </div>
          {/* Skeleton cards */}
          <div className="w-full max-w-2xl space-y-4 mt-4 px-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <div
                key={i}
                className="rounded-xl border border-border/50 overflow-hidden animate-pulse"
              >
                <div className="h-1.5 bg-muted/30" />
                <div className="p-6 space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="space-y-2">
                      <div className="h-5 bg-muted/30 rounded w-48" />
                      <div className="h-3 bg-muted/20 rounded w-64" />
                    </div>
                    <div className="h-7 bg-muted/30 rounded w-20" />
                  </div>
                  <div className="flex gap-2">
                    <div className="h-6 bg-muted/20 rounded-full w-20" />
                    <div className="h-6 bg-muted/20 rounded-full w-24" />
                    <div className="h-6 bg-muted/20 rounded-full w-16" />
                  </div>
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
          <p className="text-lg font-medium text-foreground">
            Something went wrong
          </p>
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

  return (
    <div className="min-h-screen bg-restaurant-cream/30 dark:bg-restaurant-dark/20">
      {/* Page Header */}
      <div className="bg-gradient-to-b from-restaurant-red/5 to-transparent dark:from-restaurant-red/10">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 pt-8 pb-6">
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="text-center"
          >
            <h1 className="text-3xl sm:text-4xl font-bold text-foreground tracking-tight">
              Your <span className="text-restaurant-red">Orders</span>
            </h1>
            <p className="mt-1 text-restaurant-gold font-medium text-lg">
              您的订单
            </p>
            <p className="mt-2 text-sm text-muted-foreground max-w-lg mx-auto">
              Track your current orders and revisit your order history. Active
              orders update automatically.
            </p>
          </motion.div>
        </div>
      </div>

      {/* Order List */}
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 pb-24 lg:pb-8">
        <OrderList initialOrders={orders} />
      </div>
    </div>
  )
}
