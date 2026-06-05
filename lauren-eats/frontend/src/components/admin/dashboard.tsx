'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import {
  TrendingUp,
  DollarSign,
  CalendarDays,
  Users,
  ShoppingCart,
  ChefHat,
  Leaf,
  Bot,
  Star,
  Flame,
  Clock,
  RefreshCw,
  Eye,
  Filter,
} from 'lucide-react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

// ─── Types ────────────────────────────────────────────────────────────

interface StatsData {
  totalOrders: number
  totalRevenue: number
  totalReservations: number
  totalCustomers: number
  ordersByStatus: Record<string, number>
  recentOrders: Array<{
    id: string
    orderNumber: string
    status: string
    totalAmount: number
    createdAt: string
    orderItems: Array<{ menuItem: { name: string } }>
    user: { name: string | null; email: string } | null
  }>
  popularItems: Array<{
    id: string
    name: string
    nameZh: string | null
    price: number
    image: string | null
    totalOrdered: number
  }>
  revenueChartData: Array<{
    date: string
    day: string
    revenue: number
    orders: number
  }>
}

interface OrderData {
  id: string
  orderNumber: string
  status: string
  totalAmount: number
  createdAt: string
  orderItems: Array<{ menuItem: { name: string } }>
  user: { name: string | null; email: string } | null
}

interface ReservationData {
  id: string
  customerName: string
  partySize: number
  date: string
  time: string
  status: string
  occasion: string | null
  specialRequests: string | null
}

interface MenuItemData {
  id: string
  name: string
  nameZh: string | null
  description: string
  price: number
  isAvailable: boolean
  isPopular: boolean
  image: string | null
  category: { name: string } | null
}

interface AIInsightsData {
  agentInteractions: Array<{
    agentType: string
    name: string
    color: string
    conversations: number
  }>
  commonQueries: Array<{
    category: string
    label: string
    count: number
  }>
  qualityMetrics: {
    totalConversations: number
    activeConversations: number
    endedConversations: number
    totalUserMessages: number
    totalAssistantMessages: number
    avgMessagesPerConversation: number
    avgResponseTimeMs: number
    satisfactionScore: number
    resolutionRate: number
  }
}

// ─── Status Badge Colors ──────────────────────────────────────────────

const orderStatusColors: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  confirmed: 'bg-blue-100 text-blue-800 border-blue-200',
  preparing: 'bg-orange-100 text-orange-800 border-orange-200',
  ready: 'bg-green-100 text-green-800 border-green-200',
  delivered: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  cancelled: 'bg-red-100 text-red-800 border-red-200',
}

const reservationStatusColors: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  confirmed: 'bg-blue-100 text-blue-800 border-blue-200',
  completed: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  cancelled: 'bg-red-100 text-red-800 border-red-200',
}

const orderStatusOptions = ['pending', 'confirmed', 'preparing', 'ready', 'delivered', 'cancelled']
const reservationStatusOptions = ['pending', 'confirmed', 'completed', 'cancelled']

// ─── Chart Colors (restaurant palette) ────────────────────────────────

const CHART_COLORS = ['#C41E3A', '#D4A843', '#10B981', '#F59E0B', '#8B5CF6', '#6B7280', '#EC4899']

// ─── Animation Variants ───────────────────────────────────────────────

const cardVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
}

// ─── Helper Functions ─────────────────────────────────────────────────

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount)
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatDateOnly(dateStr: string): string {
  return new Date(dateStr + 'T00:00:00').toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

// ─── Skeleton Loaders ─────────────────────────────────────────────────

function StatsSkeleton() {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <Card key={i} className="border-border/50">
          <CardContent className="p-6">
            <Skeleton className="h-4 w-24 mb-3" />
            <Skeleton className="h-8 w-20 mb-2" />
            <Skeleton className="h-3 w-16" />
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-3">
      <Skeleton className="h-10 w-full" />
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-12 w-full" />
      ))}
    </div>
  )
}

// ─── Overview Tab ─────────────────────────────────────────────────────

function OverviewTab({ stats, loading }: { stats: StatsData | null; loading: boolean }) {
  if (loading || !stats) {
    return (
      <div className="space-y-6">
        <StatsSkeleton />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card className="border-border/50"><CardContent className="p-6"><Skeleton className="h-64 w-full" /></CardContent></Card>
          <Card className="border-border/50"><CardContent className="p-6"><Skeleton className="h-64 w-full" /></CardContent></Card>
        </div>
      </div>
    )
  }

  const statCards = [
    {
      title: 'Total Orders',
      value: stats.totalOrders.toLocaleString(),
      icon: ShoppingCart,
      trend: '+12.5%',
      trendUp: true,
      color: 'text-restaurant-red',
      bg: 'bg-restaurant-red/10',
      border: 'border-restaurant-red/20',
    },
    {
      title: 'Total Revenue',
      value: formatCurrency(stats.totalRevenue),
      icon: DollarSign,
      trend: '+8.2%',
      trendUp: true,
      color: 'text-emerald-600',
      bg: 'bg-emerald-500/10',
      border: 'border-emerald-500/20',
    },
    {
      title: 'Total Reservations',
      value: stats.totalReservations.toLocaleString(),
      icon: CalendarDays,
      trend: '+5.1%',
      trendUp: true,
      color: 'text-restaurant-gold',
      bg: 'bg-restaurant-gold/10',
      border: 'border-restaurant-gold/20',
    },
    {
      title: 'Total Customers',
      value: stats.totalCustomers.toLocaleString(),
      icon: Users,
      trend: '+3.8%',
      trendUp: true,
      color: 'text-purple-600',
      bg: 'bg-purple-500/10',
      border: 'border-purple-500/20',
    },
  ]

  return (
    <div className="space-y-6">
      {/* Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((card, i) => {
          const Icon = card.icon
          return (
            <motion.div
              key={card.title}
              variants={cardVariants}
              initial="hidden"
              animate="visible"
              transition={{ duration: 0.4, delay: i * 0.1 }}
            >
              <Card className={cn('border hover:shadow-md transition-all duration-300', card.border)}>
                <CardContent className="p-4 sm:p-6">
                  <div className="flex items-center justify-between mb-3">
                    <p className="text-xs sm:text-sm font-medium text-muted-foreground">{card.title}</p>
                    <div className={cn('inline-flex items-center justify-center w-8 h-8 sm:w-10 sm:h-10 rounded-xl', card.bg, card.color)}>
                      <Icon className="h-4 w-4 sm:h-5 sm:w-5" />
                    </div>
                  </div>
                  <div className="flex items-end gap-2">
                    <p className="text-xl sm:text-2xl lg:text-3xl font-bold text-foreground">{card.value}</p>
                  </div>
                  <div className="flex items-center gap-1 mt-2">
                    <TrendingUp className={cn('h-3 w-3', card.trendUp ? 'text-emerald-500' : 'text-red-500')} />
                    <span className={cn('text-xs font-medium', card.trendUp ? 'text-emerald-600' : 'text-red-600')}>
                      {card.trend}
                    </span>
                    <span className="text-xs text-muted-foreground">vs last week</span>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Revenue Chart */}
        <motion.div
          variants={cardVariants}
          initial="hidden"
          animate="visible"
          transition={{ duration: 0.4, delay: 0.4 }}
        >
          <Card className="border-border/50">
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-semibold">Revenue — Last 7 Days</CardTitle>
              <CardDescription>Daily revenue from non-cancelled orders</CardDescription>
            </CardHeader>
            <CardContent className="pt-0">
              <div className="h-[280px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={stats.revenueChartData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="oklch(0.922 0 0 / 50%)" />
                    <XAxis
                      dataKey="day"
                      tick={{ fontSize: 12, fill: 'oklch(0.556 0 0)' }}
                      axisLine={{ stroke: 'oklch(0.922 0 0)' }}
                      tickLine={false}
                    />
                    <YAxis
                      tick={{ fontSize: 12, fill: 'oklch(0.556 0 0)' }}
                      axisLine={false}
                      tickLine={false}
                      tickFormatter={(v: number) => `$${v}`}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'oklch(1 0 0)',
                        border: '1px solid oklch(0.922 0 0)',
                        borderRadius: '8px',
                        fontSize: '12px',
                        boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
                      }}
                      formatter={(value: number) => [formatCurrency(value), 'Revenue']}
                    />
                    <Bar dataKey="revenue" radius={[6, 6, 0, 0]} maxBarSize={48}>
                      {stats.revenueChartData.map((_, index) => (
                        <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Orders by Status */}
        <motion.div
          variants={cardVariants}
          initial="hidden"
          animate="visible"
          transition={{ duration: 0.4, delay: 0.5 }}
        >
          <Card className="border-border/50">
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-semibold">Orders by Status</CardTitle>
              <CardDescription>Current distribution of order statuses</CardDescription>
            </CardHeader>
            <CardContent className="pt-0">
              <div className="space-y-3 mt-2">
                {orderStatusOptions.map((status) => {
                  const count = stats.ordersByStatus[status] || 0
                  const total = Object.values(stats.ordersByStatus).reduce((a, b) => a + b, 0) || 1
                  const percentage = Math.round((count / total) * 100)
                  const colorMap: Record<string, string> = {
                    pending: 'bg-yellow-400',
                    confirmed: 'bg-blue-400',
                    preparing: 'bg-orange-400',
                    ready: 'bg-green-400',
                    delivered: 'bg-emerald-400',
                    cancelled: 'bg-red-400',
                  }
                  return (
                    <div key={status} className="space-y-1.5">
                      <div className="flex items-center justify-between text-sm">
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className={cn('text-[10px] capitalize', orderStatusColors[status])}>
                            {status}
                          </Badge>
                        </div>
                        <span className="text-muted-foreground text-xs">
                          {count} ({percentage}%)
                        </span>
                      </div>
                      <div className="h-2 rounded-full bg-muted overflow-hidden">
                        <div
                          className={cn('h-full rounded-full transition-all duration-500', colorMap[status])}
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Popular Items */}
        <motion.div
          variants={cardVariants}
          initial="hidden"
          animate="visible"
          transition={{ duration: 0.4, delay: 0.6 }}
        >
          <Card className="border-border/50">
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <Flame className="h-4 w-4 text-restaurant-red" />
                Popular Items
              </CardTitle>
              <CardDescription>Top 5 dishes by order count</CardDescription>
            </CardHeader>
            <CardContent className="pt-0">
              <div className="space-y-3">
                {stats.popularItems.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-8">No order data yet</p>
                ) : (
                  stats.popularItems.map((item, i) => (
                    <div key={item.id} className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/50 transition-colors">
                      <div className={cn(
                        'w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold shrink-0',
                        i === 0 ? 'bg-restaurant-red/10 text-restaurant-red' :
                        i === 1 ? 'bg-restaurant-gold/10 text-restaurant-gold' :
                        'bg-muted text-muted-foreground'
                      )}>
                        {i + 1}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-medium truncate">{item.name}</p>
                          {item.nameZh && (
                            <span className="text-xs text-restaurant-gold">{item.nameZh}</span>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground">{formatCurrency(item.price)}</p>
                      </div>
                      <Badge variant="outline" className="text-[10px] shrink-0">
                        {item.totalOrdered} ordered
                      </Badge>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Recent Orders */}
        <motion.div
          variants={cardVariants}
          initial="hidden"
          animate="visible"
          transition={{ duration: 0.4, delay: 0.7 }}
        >
          <Card className="border-border/50">
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <Clock className="h-4 w-4 text-restaurant-gold" />
                Recent Orders
              </CardTitle>
              <CardDescription>Last 10 orders</CardDescription>
            </CardHeader>
            <CardContent className="pt-0">
              <div className="max-h-80 overflow-y-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="text-[11px]">Order #</TableHead>
                      <TableHead className="text-[11px]">Items</TableHead>
                      <TableHead className="text-[11px]">Total</TableHead>
                      <TableHead className="text-[11px]">Status</TableHead>
                      <TableHead className="text-[11px]">Date</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {stats.recentOrders.map((order) => (
                      <TableRow key={order.id} className="hover:bg-muted/30">
                        <TableCell className="text-xs font-mono">{order.orderNumber.slice(-8)}</TableCell>
                        <TableCell className="text-xs">{order.orderItems.length} items</TableCell>
                        <TableCell className="text-xs font-medium">{formatCurrency(order.totalAmount)}</TableCell>
                        <TableCell>
                          <Badge variant="outline" className={cn('text-[10px] capitalize', orderStatusColors[order.status] || '')}>
                            {order.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground">{formatDate(order.createdAt)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  )
}

// ─── Orders Tab ───────────────────────────────────────────────────────

function OrdersTab() {
  const [orders, setOrders] = useState<OrderData[]>([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState<string>('all')

  const fetchOrders = useCallback(async () => {
    setLoading(true)
    try {
      const url = statusFilter === 'all' ? '/api/orders' : `/api/orders?status=${statusFilter}`
      const res = await fetch(url)
      const data = await res.json()
      if (data.success) {
        setOrders(data.data)
      }
    } catch (err) {
      console.error('Error fetching orders:', err)
    } finally {
      setLoading(false)
    }
  }, [statusFilter])

  useEffect(() => {
    fetchOrders()
  }, [fetchOrders])

  const updateOrderStatus = async (orderId: string, newStatus: string) => {
    try {
      const res = await fetch(`/api/orders/${orderId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      })
      const data = await res.json()
      if (data.success) {
        setOrders(prev => prev.map(o => o.id === orderId ? { ...o, status: newStatus } : o))
      }
    } catch (err) {
      console.error('Error updating order status:', err)
    }
  }

  return (
    <div className="space-y-4">
      {/* Filter bar */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium">Filter:</span>
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[160px] h-9">
            <SelectValue placeholder="All statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Statuses</SelectItem>
            {orderStatusOptions.map(s => (
              <SelectItem key={s} value={s} className="capitalize">{s}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button variant="outline" size="sm" onClick={fetchOrders} className="h-9 gap-1.5">
          <RefreshCw className="h-3.5 w-3.5" />
          Refresh
        </Button>
        <Badge variant="outline" className="text-xs">{orders.length} orders</Badge>
      </div>

      {/* Orders Table */}
      {loading ? (
        <TableSkeleton rows={8} />
      ) : orders.length === 0 ? (
        <Card className="border-border/50">
          <CardContent className="py-16 text-center">
            <ShoppingCart className="h-12 w-12 text-muted-foreground/30 mx-auto mb-4" />
            <p className="text-muted-foreground">No orders found</p>
          </CardContent>
        </Card>
      ) : (
        <Card className="border-border/50">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Order #</TableHead>
                  <TableHead>Customer</TableHead>
                  <TableHead>Items</TableHead>
                  <TableHead>Total</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {orders.map((order) => (
                  <TableRow key={order.id} className="hover:bg-muted/30">
                    <TableCell className="font-mono text-sm">{order.orderNumber.slice(-8)}</TableCell>
                    <TableCell className="text-sm">
                      {order.user?.name || order.user?.email || 'Walk-in'}
                    </TableCell>
                    <TableCell className="text-sm">{order.orderItems.length} items</TableCell>
                    <TableCell className="text-sm font-medium">{formatCurrency(order.totalAmount)}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className={cn('text-[10px] capitalize', orderStatusColors[order.status] || '')}>
                        {order.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">{formatDate(order.createdAt)}</TableCell>
                    <TableCell className="text-right">
                      <Select
                        value={order.status}
                        onValueChange={(val) => updateOrderStatus(order.id, val)}
                      >
                        <SelectTrigger className="w-[130px] h-8 text-xs">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {orderStatusOptions.map(s => (
                            <SelectItem key={s} value={s} className="capitalize text-xs">{s}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </Card>
      )}
    </div>
  )
}

// ─── Reservations Tab ─────────────────────────────────────────────────

function ReservationsTab() {
  const [reservations, setReservations] = useState<ReservationData[]>([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [dateFilter, setDateFilter] = useState<string>('')

  const fetchReservations = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (statusFilter !== 'all') params.set('status', statusFilter)
      if (dateFilter) params.set('date', dateFilter)
      const qs = params.toString()
      const url = `/api/reservations${qs ? `?${qs}` : ''}`
      const res = await fetch(url)
      const data = await res.json()
      if (data.success) {
        setReservations(data.data)
      }
    } catch (err) {
      console.error('Error fetching reservations:', err)
    } finally {
      setLoading(false)
    }
  }, [statusFilter, dateFilter])

  useEffect(() => {
    fetchReservations()
  }, [fetchReservations])

  const updateReservationStatus = async (reservationId: string, newStatus: string) => {
    try {
      const res = await fetch(`/api/reservations/${reservationId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      })
      const data = await res.json()
      if (data.success) {
        setReservations(prev => prev.map(r => r.id === reservationId ? { ...r, status: newStatus } : r))
      }
    } catch (err) {
      console.error('Error updating reservation status:', err)
    }
  }

  return (
    <div className="space-y-4">
      {/* Filter bar */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium">Filter:</span>
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[160px] h-9">
            <SelectValue placeholder="All statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Statuses</SelectItem>
            {reservationStatusOptions.map(s => (
              <SelectItem key={s} value={s} className="capitalize">{s}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <input
          type="date"
          value={dateFilter}
          onChange={(e) => setDateFilter(e.target.value)}
          className="h-9 rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
        />
        <Button variant="outline" size="sm" onClick={fetchReservations} className="h-9 gap-1.5">
          <RefreshCw className="h-3.5 w-3.5" />
          Refresh
        </Button>
        <Badge variant="outline" className="text-xs">{reservations.length} reservations</Badge>
      </div>

      {/* Reservations Table */}
      {loading ? (
        <TableSkeleton rows={6} />
      ) : reservations.length === 0 ? (
        <Card className="border-border/50">
          <CardContent className="py-16 text-center">
            <CalendarDays className="h-12 w-12 text-muted-foreground/30 mx-auto mb-4" />
            <p className="text-muted-foreground">No reservations found</p>
          </CardContent>
        </Card>
      ) : (
        <Card className="border-border/50">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Party Size</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead>Time</TableHead>
                  <TableHead>Occasion</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {reservations.map((res) => (
                  <TableRow key={res.id} className="hover:bg-muted/30">
                    <TableCell className="text-sm font-medium">{res.customerName}</TableCell>
                    <TableCell className="text-sm">
                      <Badge variant="outline" className="text-[10px]">
                        <Users className="h-3 w-3 mr-1" />
                        {res.partySize}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm">{formatDateOnly(res.date)}</TableCell>
                    <TableCell className="text-sm">{res.time}</TableCell>
                    <TableCell className="text-sm">
                      {res.occasion ? (
                        <Badge variant="outline" className="text-[10px] capitalize">{res.occasion}</Badge>
                      ) : (
                        <span className="text-muted-foreground text-xs">—</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className={cn('text-[10px] capitalize', reservationStatusColors[res.status] || '')}>
                        {res.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <Select
                        value={res.status}
                        onValueChange={(val) => updateReservationStatus(res.id, val)}
                      >
                        <SelectTrigger className="w-[130px] h-8 text-xs">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {reservationStatusOptions.map(s => (
                            <SelectItem key={s} value={s} className="capitalize text-xs">{s}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </Card>
      )}
    </div>
  )
}

// ─── Menu Tab ─────────────────────────────────────────────────────────

function MenuTab() {
  const [menuItems, setMenuItems] = useState<MenuItemData[]>([])
  const [loading, setLoading] = useState(true)

  const fetchMenuItems = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/menu')
      const data = await res.json()
      if (data.success) {
        setMenuItems(data.data)
      }
    } catch (err) {
      console.error('Error fetching menu items:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchMenuItems()
  }, [fetchMenuItems])

  const toggleField = async (itemId: string, field: 'isAvailable' | 'isPopular', value: boolean) => {
    try {
      const res = await fetch(`/api/menu/${itemId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ [field]: value }),
      })
      const data = await res.json()
      if (data.success) {
        setMenuItems(prev => prev.map(item =>
          item.id === itemId ? { ...item, [field]: value } : item
        ))
      }
    } catch (err) {
      console.error(`Error toggling ${field}:`, err)
    }
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <Badge variant="outline" className="text-xs">{menuItems.length} items</Badge>
        <Button variant="outline" size="sm" onClick={fetchMenuItems} className="h-9 gap-1.5">
          <RefreshCw className="h-3.5 w-3.5" />
          Refresh
        </Button>
      </div>

      {/* Menu Items Table */}
      {loading ? (
        <TableSkeleton rows={10} />
      ) : menuItems.length === 0 ? (
        <Card className="border-border/50">
          <CardContent className="py-16 text-center">
            <ChefHat className="h-12 w-12 text-muted-foreground/30 mx-auto mb-4" />
            <p className="text-muted-foreground">No menu items found</p>
          </CardContent>
        </Card>
      ) : (
        <Card className="border-border/50">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Item</TableHead>
                  <TableHead>Category</TableHead>
                  <TableHead>Price</TableHead>
                  <TableHead>Available</TableHead>
                  <TableHead>Popular</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {menuItems.map((item) => (
                  <TableRow key={item.id} className="hover:bg-muted/30">
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-restaurant-red/5 border border-restaurant-red/10 flex items-center justify-center text-lg shrink-0">
                          {item.image || '🍽️'}
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <p className="text-sm font-medium">{item.name}</p>
                            {item.nameZh && (
                              <span className="text-xs text-restaurant-gold">{item.nameZh}</span>
                            )}
                          </div>
                          <p className="text-xs text-muted-foreground line-clamp-1 max-w-[200px]">{item.description}</p>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {item.category?.name || '—'}
                    </TableCell>
                    <TableCell className="text-sm font-medium">{formatCurrency(item.price)}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Switch
                          checked={item.isAvailable}
                          onCheckedChange={(checked) => toggleField(item.id, 'isAvailable', checked)}
                        />
                        <span className={cn('text-xs', item.isAvailable ? 'text-emerald-600' : 'text-muted-foreground')}>
                          {item.isAvailable ? 'Yes' : 'No'}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Switch
                          checked={item.isPopular}
                          onCheckedChange={(checked) => toggleField(item.id, 'isPopular', checked)}
                        />
                        {item.isPopular ? (
                          <Star className="h-3.5 w-3.5 text-restaurant-gold fill-restaurant-gold" />
                        ) : (
                          <Star className="h-3.5 w-3.5 text-muted-foreground/30" />
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </Card>
      )}
    </div>
  )
}

// ─── AI Insights Tab ──────────────────────────────────────────────────

function AIInsightsTab() {
  const [insights, setInsights] = useState<AIInsightsData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchInsights() {
      try {
        const res = await fetch('/api/admin/ai-insights')
        const data = await res.json()
        if (data.success) {
          setInsights(data.data)
        }
      } catch (err) {
        console.error('Error fetching AI insights:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchInsights()
  }, [])

  if (loading) {
    return (
      <div className="space-y-6">
        <StatsSkeleton />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card className="border-border/50"><CardContent className="p-6"><Skeleton className="h-64 w-full" /></CardContent></Card>
          <Card className="border-border/50"><CardContent className="p-6"><Skeleton className="h-64 w-full" /></CardContent></Card>
        </div>
      </div>
    )
  }

  if (!insights) {
    return (
      <Card className="border-border/50">
        <CardContent className="py-16 text-center">
          <Bot className="h-12 w-12 text-muted-foreground/30 mx-auto mb-4" />
          <p className="text-muted-foreground">Failed to load AI insights</p>
        </CardContent>
      </Card>
    )
  }

  const metrics = insights.qualityMetrics

  return (
    <div className="space-y-6">
      {/* Quality Metric Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { title: 'Total Conversations', value: metrics.totalConversations, icon: Bot, color: 'text-restaurant-red', bg: 'bg-restaurant-red/10', border: 'border-restaurant-red/20' },
          { title: 'Avg Response Time', value: `${(metrics.avgResponseTimeMs / 1000).toFixed(1)}s`, icon: Clock, color: 'text-restaurant-gold', bg: 'bg-restaurant-gold/10', border: 'border-restaurant-gold/20' },
          { title: 'Satisfaction', value: `${metrics.satisfactionScore}/5.0`, icon: Star, color: 'text-emerald-600', bg: 'bg-emerald-500/10', border: 'border-emerald-500/20' },
          { title: 'Resolution Rate', value: `${metrics.resolutionRate}%`, icon: Eye, color: 'text-purple-600', bg: 'bg-purple-500/10', border: 'border-purple-500/20' },
        ].map((card, i) => {
          const Icon = card.icon
          return (
            <motion.div
              key={card.title}
              variants={cardVariants}
              initial="hidden"
              animate="visible"
              transition={{ duration: 0.4, delay: i * 0.1 }}
            >
              <Card className={cn('border hover:shadow-md transition-all duration-300', card.border)}>
                <CardContent className="p-4 sm:p-6">
                  <div className="flex items-center justify-between mb-3">
                    <p className="text-xs sm:text-sm font-medium text-muted-foreground">{card.title}</p>
                    <div className={cn('inline-flex items-center justify-center w-8 h-8 sm:w-10 sm:h-10 rounded-xl', card.bg, card.color)}>
                      <Icon className="h-4 w-4 sm:h-5 sm:w-5" />
                    </div>
                  </div>
                  <p className="text-xl sm:text-2xl lg:text-3xl font-bold text-foreground">{card.value}</p>
                </CardContent>
              </Card>
            </motion.div>
          )
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Agent Interactions */}
        <motion.div
          variants={cardVariants}
          initial="hidden"
          animate="visible"
          transition={{ duration: 0.4, delay: 0.4 }}
        >
          <Card className="border-border/50">
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <Bot className="h-4 w-4 text-restaurant-red" />
                Agent Interactions
              </CardTitle>
              <CardDescription>Conversations per AI agent</CardDescription>
            </CardHeader>
            <CardContent className="pt-0">
              <div className="h-[260px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={insights.agentInteractions} layout="vertical" margin={{ top: 5, right: 20, left: 80, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="oklch(0.922 0 0 / 50%)" horizontal={false} />
                    <XAxis type="number" tick={{ fontSize: 11, fill: 'oklch(0.556 0 0)' }} />
                    <YAxis
                      type="category"
                      dataKey="name"
                      tick={{ fontSize: 11, fill: 'oklch(0.556 0 0)' }}
                      width={75}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'oklch(1 0 0)',
                        border: '1px solid oklch(0.922 0 0)',
                        borderRadius: '8px',
                        fontSize: '12px',
                        boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
                      }}
                      formatter={(value: number) => [`${value} conversations`, 'Count']}
                    />
                    <Bar dataKey="conversations" radius={[0, 6, 6, 0]} maxBarSize={28}>
                      {insights.agentInteractions.map((agent, index) => (
                        <Cell key={`cell-${index}`} fill={agent.color} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Common Queries */}
        <motion.div
          variants={cardVariants}
          initial="hidden"
          animate="visible"
          transition={{ duration: 0.4, delay: 0.5 }}
        >
          <Card className="border-border/50">
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <Eye className="h-4 w-4 text-restaurant-gold" />
                Common User Queries
              </CardTitle>
              <CardDescription>Most frequent query categories</CardDescription>
            </CardHeader>
            <CardContent className="pt-0">
              <div className="space-y-3 mt-2">
                {insights.commonQueries.map((query, i) => {
                  const maxCount = Math.max(...insights.commonQueries.map(q => q.count), 1)
                  const percentage = Math.round((query.count / maxCount) * 100)
                  return (
                    <div key={query.category} className="space-y-1.5">
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-medium">{query.label}</span>
                        <span className="text-muted-foreground text-xs">{query.count} queries</span>
                      </div>
                      <div className="h-2 rounded-full bg-muted overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all duration-500"
                          style={{
                            width: `${percentage}%`,
                            backgroundColor: CHART_COLORS[i % CHART_COLORS.length],
                          }}
                        />
                      </div>
                    </div>
                  )
                })}
                {insights.commonQueries.length === 0 && (
                  <p className="text-sm text-muted-foreground text-center py-6">No query data yet</p>
                )}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Detailed Metrics */}
      <motion.div
        variants={cardVariants}
        initial="hidden"
        animate="visible"
        transition={{ duration: 0.4, delay: 0.6 }}
      >
        <Card className="border-border/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-semibold">Detailed Agent Metrics</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="p-4 rounded-xl bg-restaurant-red/5 border border-restaurant-red/10">
                <p className="text-xs text-muted-foreground mb-1">Active Conversations</p>
                <p className="text-xl font-bold text-restaurant-red">{metrics.activeConversations}</p>
              </div>
              <div className="p-4 rounded-xl bg-restaurant-gold/5 border border-restaurant-gold/10">
                <p className="text-xs text-muted-foreground mb-1">User Messages</p>
                <p className="text-xl font-bold text-restaurant-gold">{metrics.totalUserMessages}</p>
              </div>
              <div className="p-4 rounded-xl bg-emerald-500/5 border border-emerald-500/10">
                <p className="text-xs text-muted-foreground mb-1">Agent Responses</p>
                <p className="text-xl font-bold text-emerald-600">{metrics.totalAssistantMessages}</p>
              </div>
              <div className="p-4 rounded-xl bg-purple-500/5 border border-purple-500/10">
                <p className="text-xs text-muted-foreground mb-1">Avg Msgs / Conv</p>
                <p className="text-xl font-bold text-purple-600">{metrics.avgMessagesPerConversation}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  )
}

// ─── Main Dashboard Component ─────────────────────────────────────────

export default function AdminDashboard() {
  const [stats, setStats] = useState<StatsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('overview')

  useEffect(() => {
    async function fetchStats() {
      try {
        const res = await fetch('/api/admin/stats')
        const data = await res.json()
        if (data.success) {
          setStats(data.data)
        }
      } catch (err) {
        console.error('Error fetching admin stats:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchStats()
  }, [])

  return (
    <div className="space-y-6">
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-5 h-auto p-1 bg-muted/50">
          <TabsTrigger value="overview" className="text-xs sm:text-sm py-2 data-[state=active]:bg-background data-[state=active]:shadow-sm">
            <TrendingUp className="h-3.5 w-3.5 mr-1.5 hidden sm:inline" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="orders" className="text-xs sm:text-sm py-2 data-[state=active]:bg-background data-[state=active]:shadow-sm">
            <ShoppingCart className="h-3.5 w-3.5 mr-1.5 hidden sm:inline" />
            Orders
          </TabsTrigger>
          <TabsTrigger value="reservations" className="text-xs sm:text-sm py-2 data-[state=active]:bg-background data-[state=active]:shadow-sm">
            <CalendarDays className="h-3.5 w-3.5 mr-1.5 hidden sm:inline" />
            Reservations
          </TabsTrigger>
          <TabsTrigger value="menu" className="text-xs sm:text-sm py-2 data-[state=active]:bg-background data-[state=active]:shadow-sm">
            <ChefHat className="h-3.5 w-3.5 mr-1.5 hidden sm:inline" />
            Menu
          </TabsTrigger>
          <TabsTrigger value="ai-insights" className="text-xs sm:text-sm py-2 data-[state=active]:bg-background data-[state=active]:shadow-sm">
            <Bot className="h-3.5 w-3.5 mr-1.5 hidden sm:inline" />
            AI Insights
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-6">
          <OverviewTab stats={stats} loading={loading} />
        </TabsContent>
        <TabsContent value="orders" className="mt-6">
          <OrdersTab />
        </TabsContent>
        <TabsContent value="reservations" className="mt-6">
          <ReservationsTab />
        </TabsContent>
        <TabsContent value="menu" className="mt-6">
          <MenuTab />
        </TabsContent>
        <TabsContent value="ai-insights" className="mt-6">
          <AIInsightsTab />
        </TabsContent>
      </Tabs>
    </div>
  )
}
