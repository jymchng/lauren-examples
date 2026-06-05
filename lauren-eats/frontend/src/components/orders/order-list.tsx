'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import Link from 'next/link'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Package,
  UtensilsCrossed,
  RefreshCw,
  Filter,
  ShoppingBag,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { OrderCard } from '@/components/orders/order-card'
import type { Order, OrderStatus } from '@/types'

// ─── Filter Options ──────────────────────────────────────────────────

type FilterStatus = 'all' | OrderStatus

const filterOptions: { key: FilterStatus; label: string; labelZh: string }[] = [
  { key: 'all', label: 'All', labelZh: '全部' },
  { key: 'pending', label: 'Pending', labelZh: '待确认' },
  { key: 'confirmed', label: 'Confirmed', labelZh: '已确认' },
  { key: 'preparing', label: 'Preparing', labelZh: '制作中' },
  { key: 'ready', label: 'Ready', labelZh: '已备好' },
  { key: 'delivered', label: 'Delivered', labelZh: '已送达' },
  { key: 'cancelled', label: 'Cancelled', labelZh: '已取消' },
]

const filterColors: Record<FilterStatus, string> = {
  all: 'bg-muted/50 text-muted-foreground hover:bg-muted border-border/50',
  pending: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30',
  confirmed: 'bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-500/30',
  preparing: 'bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/30',
  ready: 'bg-green-500/10 text-green-600 dark:text-green-400 border-green-500/30',
  delivered: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30',
  cancelled: 'bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/30',
}

const activeFilterColors: Record<FilterStatus, string> = {
  all: 'bg-restaurant-red text-restaurant-red-foreground shadow-md shadow-restaurant-red/20',
  pending: 'bg-amber-500 text-white shadow-md shadow-amber-500/20',
  confirmed: 'bg-sky-500 text-white shadow-md shadow-sky-500/20',
  preparing: 'bg-orange-500 text-white shadow-md shadow-orange-500/20',
  ready: 'bg-green-500 text-white shadow-md shadow-green-500/20',
  delivered: 'bg-emerald-500 text-white shadow-md shadow-emerald-500/20',
  cancelled: 'bg-red-500 text-white shadow-md shadow-red-500/20',
}

// ─── Component ───────────────────────────────────────────────────────

interface OrderListProps {
  initialOrders: Order[]
}

export function OrderList({ initialOrders }: OrderListProps) {
  const [orders, setOrders] = useState<Order[]>(initialOrders)
  const [activeFilter, setActiveFilter] = useState<FilterStatus>('all')
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date())
  const refreshTimerRef = useRef<ReturnType<typeof setInterval>>()

  // Check for active orders (need auto-refresh)
  const hasActiveOrders = orders.some(
    (o) => !['delivered', 'cancelled'].includes(o.status)
  )

  // Fetch orders
  const fetchOrders = useCallback(async () => {
    try {
      setIsRefreshing(true)
      const res = await fetch('/api/orders')
      const data = await res.json()
      if (data.success) {
        setOrders(data.data)
        setLastRefreshed(new Date())
      }
    } catch (err) {
      console.error('Error fetching orders:', err)
    } finally {
      setIsRefreshing(false)
    }
  }, [])

  // Auto-refresh every 30 seconds for active orders
  useEffect(() => {
    if (hasActiveOrders) {
      refreshTimerRef.current = setInterval(() => {
        fetchOrders()
      }, 30000)
    }

    return () => {
      if (refreshTimerRef.current) {
        clearInterval(refreshTimerRef.current)
      }
    }
  }, [hasActiveOrders, fetchOrders])

  // Filter orders
  const filteredOrders =
    activeFilter === 'all'
      ? orders
      : orders.filter((o) => o.status === activeFilter)

  // Group orders by status category
  const activeOrders = filteredOrders.filter(
    (o) => !['delivered', 'cancelled'].includes(o.status)
  )
  const pastOrders = filteredOrders.filter(
    (o) => ['delivered', 'cancelled'].includes(o.status)
  )

  // Status count badges
  const statusCounts = orders.reduce(
    (acc, order) => {
      acc[order.status] = (acc[order.status] || 0) + 1
      return acc
    },
    {} as Record<string, number>
  )

  return (
    <div>
      {/* Filter Bar */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.1 }}
        className="sticky top-16 z-30 bg-background/80 backdrop-blur-xl -mx-4 sm:-mx-6 lg:-mx-8 px-4 sm:px-6 lg:px-8 py-3 border-b border-border/50"
      >
        <div className="flex items-center gap-3">
          <Filter className="h-4 w-4 text-muted-foreground shrink-0" />

          {/* Filter Pills */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none">
            {filterOptions.map((option) => {
              const isActive = activeFilter === option.key
              const count =
                option.key === 'all'
                  ? orders.length
                  : statusCounts[option.key] || 0

              return (
                <motion.button
                  key={option.key}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => setActiveFilter(option.key)}
                  className={`
                    inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-all shrink-0 border
                    ${isActive ? activeFilterColors[option.key] : filterColors[option.key]}
                  `}
                >
                  {option.label}
                  <span
                    className={`text-[10px] ${
                      isActive ? 'opacity-80' : 'text-muted-foreground/60'
                    }`}
                  >
                    {option.labelZh}
                  </span>
                  {count > 0 && (
                    <Badge
                      className={`h-4 min-w-[16px] flex items-center justify-center text-[9px] p-0 border-0 ${
                        isActive
                          ? 'bg-white/20 text-white'
                          : 'bg-foreground/5 text-muted-foreground'
                      }`}
                    >
                      {count}
                    </Badge>
                  )}
                </motion.button>
              )
            })}
          </div>

          {/* Manual Refresh */}
          <motion.div whileTap={{ scale: 0.95 }} className="shrink-0">
            <Button
              variant="ghost"
              size="icon"
              onClick={fetchOrders}
              disabled={isRefreshing}
              className="h-8 w-8"
              aria-label="Refresh orders"
            >
              <RefreshCw
                className={`h-3.5 w-3.5 ${
                  isRefreshing ? 'animate-spin' : ''
                }`}
              />
            </Button>
          </motion.div>
        </div>

        {/* Last refreshed info */}
        {hasActiveOrders && (
          <p className="text-[10px] text-muted-foreground/60 mt-1.5 flex items-center gap-1">
            <span className="relative flex h-1.5 w-1.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-restaurant-gold opacity-75" />
              <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-restaurant-gold" />
            </span>
            Auto-refreshing every 30s · Last updated{' '}
            {lastRefreshed.toLocaleTimeString()}
          </p>
        )}
      </motion.div>

      {/* Order Content */}
      <div className="mt-6 space-y-8">
        {/* Active Orders Section */}
        {activeOrders.length > 0 && (
          <section>
            <div className="flex items-center gap-2 mb-4">
              <div className="flex items-center justify-center w-6 h-6 rounded-md bg-restaurant-red/10">
                <Package className="h-3.5 w-3.5 text-restaurant-red" />
              </div>
              <h2 className="text-sm font-semibold text-foreground">
                Active Orders
              </h2>
              <span className="text-xs text-muted-foreground">进行中的订单</span>
              <Badge className="bg-restaurant-red/10 text-restaurant-red border-restaurant-red/20 text-[10px] border-0">
                {activeOrders.length}
              </Badge>
            </div>
            <div className="space-y-4">
              <AnimatePresence mode="popLayout">
                {activeOrders.map((order) => (
                  <OrderCard key={order.id} order={order} />
                ))}
              </AnimatePresence>
            </div>
          </section>
        )}

        {/* Past Orders Section */}
        {pastOrders.length > 0 && (
          <section>
            <div className="flex items-center gap-2 mb-4">
              <div className="flex items-center justify-center w-6 h-6 rounded-md bg-muted/50">
                <ShoppingBag className="h-3.5 w-3.5 text-muted-foreground" />
              </div>
              <h2 className="text-sm font-semibold text-foreground">
                Past Orders
              </h2>
              <span className="text-xs text-muted-foreground">历史订单</span>
              <Badge className="bg-muted/50 text-muted-foreground border-border/50 text-[10px]">
                {pastOrders.length}
              </Badge>
            </div>
            <div className="space-y-4">
              <AnimatePresence mode="popLayout">
                {pastOrders.map((order) => (
                  <OrderCard key={order.id} order={order} />
                ))}
              </AnimatePresence>
            </div>
          </section>
        )}

        {/* Empty State */}
        {filteredOrders.length === 0 && orders.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-col items-center justify-center py-16 text-center"
          >
            <div className="w-16 h-16 rounded-full bg-muted/50 flex items-center justify-center mb-4">
              <Filter className="h-7 w-7 text-muted-foreground/30" />
            </div>
            <p className="text-lg font-medium text-foreground">
              No orders with this status
            </p>
            <p className="text-sm text-muted-foreground mt-1">
              没有此状态的订单
            </p>
            <Button
              variant="outline"
              onClick={() => setActiveFilter('all')}
              className="mt-4 gap-2 border-restaurant-red/30 text-restaurant-red hover:bg-restaurant-red/10"
            >
              View All Orders
            </Button>
          </motion.div>
        )}

        {/* No Orders at All */}
        {orders.length === 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-col items-center justify-center py-20 text-center"
          >
            <motion.div
              animate={{ y: [0, -8, 0] }}
              transition={{
                repeat: Infinity,
                duration: 3,
                ease: 'easeInOut',
              }}
              className="w-20 h-20 rounded-full bg-restaurant-red/5 flex items-center justify-center mb-6"
            >
              <UtensilsCrossed className="h-9 w-9 text-restaurant-red/40" />
            </motion.div>
            <h3 className="text-xl font-bold text-foreground">
              No orders yet
            </h3>
            <p className="text-sm text-muted-foreground mt-2 max-w-sm">
              You haven&apos;t placed any orders yet. Explore our menu and
              discover authentic Chinese cuisine!
            </p>
            <p className="text-xs text-muted-foreground/60 mt-1">
              您还没有下过订单，来探索我们的菜单吧！
            </p>
            <Link href="/menu">
              <motion.div
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
              >
                <Button className="mt-6 bg-restaurant-red hover:bg-restaurant-red/90 text-restaurant-red-foreground gap-2 shadow-md shadow-restaurant-red/20">
                  <UtensilsCrossed className="h-4 w-4" />
                  Start Ordering
                </Button>
              </motion.div>
            </Link>
          </motion.div>
        )}
      </div>
    </div>
  )
}
