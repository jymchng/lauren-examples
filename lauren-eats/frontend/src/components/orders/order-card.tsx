'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { format } from 'date-fns'
import {
  Package,
  Clock,
  CheckCircle,
  XCircle,
  ChevronDown,
  ChevronUp,
  UtensilsCrossed,
  ShoppingBag,
  Truck,
  Loader2,
} from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import type { Order, OrderStatus } from '@/types'

// ─── Status Configuration ────────────────────────────────────────────

const statusConfig: Record<
  OrderStatus,
  {
    label: string
    labelZh: string
    color: string
    bgColor: string
    borderColor: string
    textColor: string
    icon: typeof Clock
  }
> = {
  pending: {
    label: 'Pending',
    labelZh: '待确认',
    color: 'bg-amber-500',
    bgColor: 'bg-amber-500/10',
    borderColor: 'border-amber-500/30',
    textColor: 'text-amber-600 dark:text-amber-400',
    icon: Clock,
  },
  confirmed: {
    label: 'Confirmed',
    labelZh: '已确认',
    color: 'bg-sky-500',
    bgColor: 'bg-sky-500/10',
    borderColor: 'border-sky-500/30',
    textColor: 'text-sky-600 dark:text-sky-400',
    icon: CheckCircle,
  },
  preparing: {
    label: 'Preparing',
    labelZh: '制作中',
    color: 'bg-orange-500',
    bgColor: 'bg-orange-500/10',
    borderColor: 'border-orange-500/30',
    textColor: 'text-orange-600 dark:text-orange-400',
    icon: Loader2,
  },
  ready: {
    label: 'Ready',
    labelZh: '已备好',
    color: 'bg-green-500',
    bgColor: 'bg-green-500/10',
    borderColor: 'border-green-500/30',
    textColor: 'text-green-600 dark:text-green-400',
    icon: Package,
  },
  delivered: {
    label: 'Delivered',
    labelZh: '已送达',
    color: 'bg-emerald-500',
    bgColor: 'bg-emerald-500/10',
    borderColor: 'border-emerald-500/30',
    textColor: 'text-emerald-600 dark:text-emerald-400',
    icon: CheckCircle,
  },
  cancelled: {
    label: 'Cancelled',
    labelZh: '已取消',
    color: 'bg-red-500',
    bgColor: 'bg-red-500/10',
    borderColor: 'border-red-500/30',
    textColor: 'text-red-600 dark:text-red-400',
    icon: XCircle,
  },
}

// ─── Order Type Configuration ────────────────────────────────────────

const orderTypeConfig: Record<
  string,
  { label: string; labelZh: string; icon: typeof UtensilsCrossed }
> = {
  dine_in: {
    label: 'Dine-in',
    labelZh: '堂食',
    icon: UtensilsCrossed,
  },
  takeout: {
    label: 'Takeout',
    labelZh: '外带',
    icon: ShoppingBag,
  },
  delivery: {
    label: 'Delivery',
    labelZh: '外卖',
    icon: Truck,
  },
}

// ─── Status Timeline Steps ───────────────────────────────────────────

const timelineSteps: { key: OrderStatus; label: string; labelZh: string }[] = [
  { key: 'pending', label: 'Pending', labelZh: '待确认' },
  { key: 'confirmed', label: 'Confirmed', labelZh: '已确认' },
  { key: 'preparing', label: 'Preparing', labelZh: '制作中' },
  { key: 'ready', label: 'Ready', labelZh: '已备好' },
  { key: 'delivered', label: 'Delivered', labelZh: '已送达' },
]

// ─── Component ───────────────────────────────────────────────────────

interface OrderCardProps {
  order: Order
}

export function OrderCard({ order }: OrderCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  const status = statusConfig[order.status]
  const typeInfo = orderTypeConfig[order.type] || orderTypeConfig.dine_in
  const StatusIcon = status.icon
  const TypeIcon = typeInfo.icon

  const isActive = !['delivered', 'cancelled'].includes(order.status)

  // Determine timeline progress
  const currentStepIndex = timelineSteps.findIndex(
    (step) => step.key === order.status
  )
  const isCancelled = order.status === 'cancelled'
  const cancelledStepIndex = timelineSteps.findIndex(
    (step) => step.key === 'pending'
  )

  const orderDate = new Date(order.createdAt)

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.3 }}
    >
      <Card className="overflow-hidden border-border/50 hover:shadow-lg transition-shadow duration-300">
        {/* Status Indicator Bar */}
        <div className={`h-1.5 w-full ${status.color}`} />

        <CardContent className="p-0">
          {/* Header Section */}
          <div className="p-4 sm:p-6">
            <div className="flex items-start justify-between gap-3">
              {/* Order Number & Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <h3 className="text-lg sm:text-xl font-bold text-foreground tracking-tight">
                    {order.orderNumber}
                  </h3>
                  <Badge
                    className={`${status.bgColor} ${status.textColor} ${status.borderColor} border gap-1 text-xs font-medium`}
                  >
                    <StatusIcon
                      className={`h-3 w-3 ${
                        order.status === 'preparing'
                          ? 'animate-spin'
                          : ''
                      }`}
                    />
                    {status.label}
                    <span className="opacity-60">· {status.labelZh}</span>
                  </Badge>
                </div>
                <div className="flex items-center gap-3 mt-1.5 text-sm text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <Clock className="h-3.5 w-3.5" />
                    {format(orderDate, 'MMM d, h:mm a')}
                  </span>
                  <span className="flex items-center gap-1">
                    <TypeIcon className="h-3.5 w-3.5" />
                    {typeInfo.label}
                    <span className="opacity-60">· {typeInfo.labelZh}</span>
                  </span>
                  {order.tableNumber && (
                    <span className="flex items-center gap-1 text-restaurant-gold">
                      <UtensilsCrossed className="h-3.5 w-3.5" />
                      Table {order.tableNumber}
                    </span>
                  )}
                </div>
              </div>

              {/* Total Amount */}
              <div className="text-right shrink-0">
                <p className="text-2xl font-bold text-restaurant-red">
                  ${order.totalAmount.toFixed(2)}
                </p>
                <p className="text-xs text-muted-foreground">
                  {order.orderItems.length}{' '}
                  {order.orderItems.length === 1 ? 'item' : 'items'}
                </p>
              </div>
            </div>

            {/* Items Preview (collapsed) */}
            <div className="mt-3 flex items-center gap-2 flex-wrap">
              {order.orderItems.slice(0, 3).map((item) => (
                <span
                  key={item.id}
                  className="inline-flex items-center gap-1 text-xs bg-muted/60 text-muted-foreground rounded-full px-2.5 py-1"
                >
                  <span className="font-medium text-foreground">
                    {item.quantity}x
                  </span>
                  {item.menuItem?.name || 'Item'}
                </span>
              ))}
              {order.orderItems.length > 3 && (
                <span className="text-xs text-muted-foreground">
                  +{order.orderItems.length - 3} more
                </span>
              )}
            </div>

            {/* Expand Button */}
            <div className="mt-3 flex items-center justify-between">
              {isActive && (
                <span className="flex items-center gap-1.5 text-xs text-restaurant-gold">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-restaurant-gold opacity-75" />
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-restaurant-gold" />
                  </span>
                  Live tracking
                </span>
              )}
              {!isActive && <span />}

              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsExpanded(!isExpanded)}
                className="gap-1 text-xs text-muted-foreground hover:text-foreground"
              >
                {isExpanded ? 'Less' : 'Details'}
                {isExpanded ? (
                  <ChevronUp className="h-3.5 w-3.5" />
                ) : (
                  <ChevronDown className="h-3.5 w-3.5" />
                )}
              </Button>
            </div>
          </div>

          {/* Expanded Details */}
          <AnimatePresence>
            {isExpanded && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.3, ease: 'easeInOut' }}
                className="overflow-hidden"
              >
                <div className="border-t border-border/50">
                  {/* Status Timeline */}
                  <div className="p-4 sm:p-6 bg-muted/20">
                    <h4 className="text-sm font-semibold text-foreground mb-4">
                      Order Progress 订单进度
                    </h4>
                    <div className="relative">
                      <div className="flex items-center justify-between relative">
                        {/* Timeline line background */}
                        <div className="absolute top-5 left-5 right-5 h-0.5 bg-muted-foreground/10" />

                        {/* Timeline progress line */}
                        {!isCancelled && currentStepIndex > 0 && (
                          <motion.div
                            initial={{ scaleX: 0 }}
                            animate={{ scaleX: 1 }}
                            transition={{ duration: 0.5, ease: 'easeOut' }}
                            className="absolute top-5 left-5 h-0.5 bg-restaurant-red origin-left"
                            style={{
                              width: `calc(${(currentStepIndex / (timelineSteps.length - 1)) * 100}% - 20px)`,
                            }}
                          />
                        )}

                        {timelineSteps.map((step, index) => {
                          const isCompleted =
                            !isCancelled && index <= currentStepIndex
                          const isCurrent =
                            !isCancelled && index === currentStepIndex
                          const stepConfig = statusConfig[step.key]
                          const StepIcon = stepConfig.icon

                          return (
                            <div
                              key={step.key}
                              className="flex flex-col items-center relative z-10"
                            >
                              <motion.div
                                initial={{ scale: 0.8 }}
                                animate={{
                                  scale: isCurrent ? 1.1 : 1,
                                }}
                                className={`
                                  w-10 h-10 rounded-full flex items-center justify-center border-2 transition-all duration-300
                                  ${
                                    isCompleted
                                      ? `${stepConfig.color} border-transparent text-white shadow-md`
                                      : 'bg-background border-border text-muted-foreground'
                                  }
                                  ${isCurrent ? 'ring-2 ring-offset-2 ring-offset-background ring-restaurant-red/30' : ''}
                                `}
                              >
                                {isCompleted ? (
                                  <StepIcon
                                    className={`h-4 w-4 ${
                                      step.key === 'preparing' &&
                                      isCurrent
                                        ? 'animate-spin'
                                        : ''
                                    }`}
                                  />
                                ) : (
                                  <span className="text-xs font-medium">
                                    {index + 1}
                                  </span>
                                )}
                              </motion.div>
                              <span
                                className={`mt-2 text-[10px] sm:text-xs font-medium text-center leading-tight ${
                                  isCompleted
                                    ? 'text-foreground'
                                    : 'text-muted-foreground'
                                }`}
                              >
                                {step.label}
                              </span>
                              <span className="text-[9px] text-muted-foreground/60">
                                {step.labelZh}
                              </span>
                            </div>
                          )
                        })}
                      </div>

                      {/* Cancelled indicator */}
                      {isCancelled && (
                        <motion.div
                          initial={{ opacity: 0, y: -5 }}
                          animate={{ opacity: 1, y: 0 }}
                          className="mt-3 flex items-center gap-2 text-red-500 bg-red-500/5 rounded-lg px-3 py-2"
                        >
                          <XCircle className="h-4 w-4 shrink-0" />
                          <span className="text-xs font-medium">
                            This order was cancelled 此订单已取消
                          </span>
                        </motion.div>
                      )}
                    </div>
                  </div>

                  {/* Items List */}
                  <div className="p-4 sm:p-6">
                    <h4 className="text-sm font-semibold text-foreground mb-3">
                      Order Items 订单菜品
                    </h4>
                    <div className="space-y-2.5">
                      {order.orderItems.map((item) => (
                        <div
                          key={item.id}
                          className="flex items-center justify-between gap-3"
                        >
                          <div className="flex items-center gap-3 flex-1 min-w-0">
                            <span className="flex items-center justify-center w-7 h-7 rounded-md bg-restaurant-red/10 text-restaurant-red text-xs font-bold shrink-0">
                              {item.quantity}
                            </span>
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium text-foreground truncate">
                                {item.menuItem?.name || 'Menu Item'}
                              </p>
                              {item.menuItem?.nameZh && (
                                <p className="text-xs text-restaurant-gold">
                                  {item.menuItem.nameZh}
                                </p>
                              )}
                              {item.notes && (
                                <p className="text-xs text-muted-foreground italic mt-0.5">
                                  {item.notes}
                                </p>
                              )}
                            </div>
                          </div>
                          <span className="text-sm font-medium text-foreground whitespace-nowrap">
                            ${item.totalPrice.toFixed(2)}
                          </span>
                        </div>
                      ))}
                    </div>

                    <Separator className="my-4" />

                    {/* Price Breakdown */}
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground">Subtotal 小计</span>
                        <span className="text-foreground">
                          ${order.subtotal.toFixed(2)}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground">Tax 税费</span>
                        <span className="text-foreground">
                          ${order.tax.toFixed(2)}
                        </span>
                      </div>
                      {order.discount > 0 && (
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-emerald-600">Discount 折扣</span>
                          <span className="text-emerald-600">
                            -${order.discount.toFixed(2)}
                          </span>
                        </div>
                      )}
                      <Separator className="my-2" />
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-foreground">
                          Total 总计
                        </span>
                        <span className="text-lg font-bold text-restaurant-red">
                          ${order.totalAmount.toFixed(2)}
                        </span>
                      </div>
                    </div>

                    {/* Order Notes */}
                    {order.notes && (
                      <>
                        <Separator className="my-4" />
                        <div>
                          <h4 className="text-sm font-semibold text-foreground mb-1.5">
                            Notes 备注
                          </h4>
                          <p className="text-sm text-muted-foreground bg-muted/30 rounded-lg px-3 py-2">
                            {order.notes}
                          </p>
                        </div>
                      </>
                    )}
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </CardContent>
      </Card>
    </motion.div>
  )
}
