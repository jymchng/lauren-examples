'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Plus, Minus, Trash2, ShoppingCart, UtensilsCrossed } from 'lucide-react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useCart } from '@/hooks/use-cart'

const TAX_RATE = 0.08

interface CartSidebarProps {
  open: boolean
  onClose: () => void
}

export function CartSidebar({ open, onClose }: CartSidebarProps) {
  const { items, removeItem, updateQuantity, clearCart, totalAmount, totalItems } = useCart()
  const [isPlacing, setIsPlacing] = useState(false)
  const [orderSuccess, setOrderSuccess] = useState(false)

  const subtotal = totalAmount
  const tax = Math.round(subtotal * TAX_RATE * 100) / 100
  const total = Math.round((subtotal + tax) * 100) / 100

  const handlePlaceOrder = async () => {
    if (items.length === 0) return

    setIsPlacing(true)
    try {
      const orderItems = items.map((item) => ({
        menuItemId: item.id,
        quantity: item.quantity,
        notes: item.notes || undefined,
      }))

      const res = await fetch('/api/orders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          items: orderItems,
          type: 'dine_in',
        }),
      })

      const data = await res.json()

      if (data.success) {
        setOrderSuccess(true)
        clearCart()
        setTimeout(() => {
          setOrderSuccess(false)
          onClose()
        }, 2000)
      }
    } catch (error) {
      console.error('Failed to place order:', error)
    } finally {
      setIsPlacing(false)
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 pt-4 pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShoppingCart className="h-5 w-5 text-restaurant-red" />
            <h2 className="text-lg font-bold text-foreground">Your Order</h2>
            {totalItems > 0 && (
              <Badge className="bg-restaurant-red text-restaurant-red-foreground border-0 text-xs">
                {totalItems} {totalItems === 1 ? 'item' : 'items'}
              </Badge>
            )}
          </div>
          {items.length > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={clearCart}
              className="text-xs text-muted-foreground hover:text-destructive"
            >
              Clear All
            </Button>
          )}
        </div>
      </div>

      <Separator />

      {/* Cart Items or Empty State */}
      {items.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center px-6 text-center">
          <AnimatePresence mode="wait">
            {orderSuccess ? (
              <motion.div
                key="success"
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.8, opacity: 0 }}
                className="flex flex-col items-center gap-3"
              >
                <div className="w-16 h-16 rounded-full bg-emerald-500/10 flex items-center justify-center">
                  <span className="text-3xl">✅</span>
                </div>
                <p className="text-lg font-semibold text-foreground">Order Placed!</p>
                <p className="text-sm text-muted-foreground">
                  Your order is being prepared
                </p>
              </motion.div>
            ) : (
              <motion.div
                key="empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex flex-col items-center gap-3"
              >
                <div className="w-20 h-20 rounded-full bg-muted/50 flex items-center justify-center">
                  <UtensilsCrossed className="h-8 w-8 text-muted-foreground/30" />
                </div>
                <p className="text-sm font-medium text-muted-foreground">
                  Your cart is empty
                </p>
                <p className="text-xs text-muted-foreground/60 max-w-[200px]">
                  Browse our menu and add some delicious dishes to get started
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      ) : (
        <>
          <ScrollArea className="flex-1 px-4">
            <div className="py-3 space-y-3">
              <AnimatePresence>
                {items.map((item) => (
                  <motion.div
                    key={item.id}
                    layout
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -20, height: 0 }}
                    transition={{ duration: 0.2 }}
                    className="flex gap-3 p-3 rounded-lg bg-muted/30 border border-border/30"
                  >
                    {/* Item image/emoji */}
                    <div className="w-12 h-12 rounded-lg bg-restaurant-red/10 flex items-center justify-center shrink-0 text-xl">
                      {item.image || '🍽️'}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <h4 className="text-sm font-medium text-foreground truncate">
                            {item.name}
                          </h4>
                          {item.nameZh && (
                            <p className="text-[10px] text-restaurant-gold">{item.nameZh}</p>
                          )}
                        </div>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => removeItem(item.id)}
                          className="h-6 w-6 shrink-0 hover:bg-destructive/10 hover:text-destructive"
                        >
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      </div>

                      <div className="flex items-center justify-between mt-2">
                        {/* Quantity controls */}
                        <div className="flex items-center gap-1.5 bg-background rounded-md border border-border/50">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => updateQuantity(item.id, item.quantity - 1)}
                            className="h-7 w-7 rounded-none rounded-l-md"
                          >
                            <Minus className="h-3 w-3" />
                          </Button>
                          <span className="text-xs font-semibold w-6 text-center">
                            {item.quantity}
                          </span>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => updateQuantity(item.id, item.quantity + 1)}
                            className="h-7 w-7 rounded-none rounded-r-md"
                          >
                            <Plus className="h-3 w-3" />
                          </Button>
                        </div>

                        <span className="text-sm font-bold text-restaurant-red">
                          ${(item.price * item.quantity).toFixed(2)}
                        </span>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          </ScrollArea>

          <Separator />

          {/* Price Breakdown */}
          <div className="px-4 py-3 space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Subtotal</span>
              <span className="font-medium">${subtotal.toFixed(2)}</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Tax (8%)</span>
              <span className="font-medium">${tax.toFixed(2)}</span>
            </div>
            <Separator />
            <div className="flex items-center justify-between">
              <span className="font-bold text-foreground">Total</span>
              <span className="text-lg font-bold text-restaurant-red">
                ${total.toFixed(2)}
              </span>
            </div>
          </div>

          {/* Place Order Button */}
          <div className="px-4 pb-4 pt-1">
            <Button
              onClick={handlePlaceOrder}
              disabled={isPlacing}
              className="w-full bg-restaurant-red hover:bg-restaurant-red/90 text-restaurant-red-foreground shadow-lg shadow-restaurant-red/20 h-12 text-base font-semibold gap-2"
            >
              {isPlacing ? (
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}
                >
                  <UtensilsCrossed className="h-4 w-4" />
                </motion.div>
              ) : (
                <>
                  <ShoppingCart className="h-4 w-4" />
                  Place Order — ${total.toFixed(2)}
                </>
              )}
            </Button>
          </div>
        </>
      )}
    </div>
  )
}
