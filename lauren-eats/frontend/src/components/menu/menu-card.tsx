'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Plus, Minus, Flame, Leaf, Wheat, Star } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useCart } from '@/hooks/use-cart'
import type { MenuItem } from '@/types'

// Category gradient map for visual variety
const categoryGradients: Record<string, { from: string; to: string; emoji: string }> = {
  appetizers: { from: 'from-amber-500/20', to: 'to-orange-500/10', emoji: '🥟' },
  soups: { from: 'from-red-500/20', to: 'to-orange-500/10', emoji: '🍲' },
  'dim-sum': { from: 'from-yellow-500/20', to: 'to-amber-500/10', emoji: '🫔' },
  'main-meat': { from: 'from-rose-500/20', to: 'to-red-500/10', emoji: '🥩' },
  'main-seafood': { from: 'from-cyan-500/20', to: 'to-blue-500/10', emoji: '🦐' },
  'main-vegetable': { from: 'from-emerald-500/20', to: 'to-green-500/10', emoji: '🥬' },
  'rice-noodles': { from: 'from-yellow-600/20', to: 'to-amber-400/10', emoji: '🍜' },
  desserts: { from: 'from-pink-500/20', to: 'to-rose-400/10', emoji: '🍮' },
}

interface MenuCardProps {
  item: MenuItem
}

export function MenuCard({ item }: MenuCardProps) {
  const { addItem, items, updateQuantity, removeItem } = useCart()
  const [isAdding, setIsAdding] = useState(false)

  const cartItem = items.find((i) => i.id === item.id)
  const quantity = cartItem?.quantity ?? 0

  const gradient = categoryGradients[item.categoryId] || {
    from: 'from-restaurant-red/20',
    to: 'to-restaurant-gold/10',
    emoji: '🍽️',
  }

  const handleAdd = () => {
    setIsAdding(true)
    addItem(item, 1)
    setTimeout(() => setIsAdding(false), 300)
  }

  const handleIncrement = () => {
    updateQuantity(item.id, quantity + 1)
  }

  const handleDecrement = () => {
    if (quantity <= 1) {
      removeItem(item.id)
    } else {
      updateQuantity(item.id, quantity - 1)
    }
  }

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95 }}
      whileHover={{ y: -4, transition: { duration: 0.2 } }}
    >
      <Card className="h-full overflow-hidden border-border/50 hover:border-restaurant-red/20 hover:shadow-lg hover:shadow-restaurant-red/5 transition-all duration-300 group">
        {/* Image / Gradient Placeholder */}
        <div
          className={`relative h-40 bg-gradient-to-br ${gradient.from} ${gradient.to} flex items-center justify-center overflow-hidden`}
        >
          {/* Decorative pattern */}
          <div className="absolute inset-0 chinese-pattern" />

          {/* Emoji Icon */}
          <motion.span
            className="text-5xl relative z-10"
            animate={isAdding ? { scale: [1, 1.3, 1], rotate: [0, 10, -10, 0] } : {}}
            transition={{ duration: 0.3 }}
          >
            {item.image || gradient.emoji}
          </motion.span>

          {/* Popular Badge */}
          {item.isPopular && (
            <Badge className="absolute top-3 right-3 bg-restaurant-gold text-restaurant-gold-foreground border-0 text-[10px] gap-1 shadow-sm">
              <Star className="h-3 w-3 fill-current" />
              Popular
            </Badge>
          )}

          {/* Spicy Level Indicator */}
          {item.spicyLevel > 0 && (
            <div className="absolute top-3 left-3 flex items-center gap-0.5 bg-black/30 backdrop-blur-sm rounded-full px-2 py-1">
              {Array.from({ length: Math.min(item.spicyLevel, 5) }).map((_, i) => (
                <Flame
                  key={i}
                  className="h-3 w-3 text-restaurant-red fill-restaurant-red"
                />
              ))}
            </div>
          )}

          {/* Quantity badge on image */}
          <AnimatePresence>
            {quantity > 0 && (
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0 }}
                className="absolute bottom-3 right-3 bg-restaurant-red text-restaurant-red-foreground rounded-full w-8 h-8 flex items-center justify-center text-sm font-bold shadow-lg"
              >
                {quantity}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <CardContent className="p-4 flex flex-col gap-3">
          {/* Name & Price Row */}
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              <h3 className="font-semibold text-foreground text-sm leading-tight truncate">
                {item.name}
              </h3>
              {item.nameZh && (
                <p className="text-xs text-restaurant-gold font-medium mt-0.5">
                  {item.nameZh}
                </p>
              )}
            </div>
            <span className="text-lg font-bold text-restaurant-red whitespace-nowrap">
              ${item.price.toFixed(2)}
            </span>
          </div>

          {/* Description */}
          <p className="text-xs text-muted-foreground leading-relaxed line-clamp-2">
            {item.description}
          </p>

          {/* Dietary Badges */}
          <div className="flex flex-wrap gap-1.5">
            {item.isVegetarian && (
              <Badge
                variant="outline"
                className="text-[10px] gap-1 border-emerald-500/30 text-emerald-600 dark:text-emerald-400 bg-emerald-500/5"
              >
                <Leaf className="h-2.5 w-2.5" />
                Vegetarian
              </Badge>
            )}
            {item.isVegan && (
              <Badge
                variant="outline"
                className="text-[10px] gap-1 border-green-500/30 text-green-600 dark:text-green-400 bg-green-500/5"
              >
                <Leaf className="h-2.5 w-2.5" />
                Vegan
              </Badge>
            )}
            {item.isGlutenFree && (
              <Badge
                variant="outline"
                className="text-[10px] gap-1 border-amber-500/30 text-amber-600 dark:text-amber-400 bg-amber-500/5"
              >
                <Wheat className="h-2.5 w-2.5" />
                Gluten-Free
              </Badge>
            )}
          </div>

          {/* Add to Cart / Quantity Selector */}
          <div className="mt-auto pt-1">
            {quantity === 0 ? (
              <motion.div whileTap={{ scale: 0.95 }}>
                <Button
                  onClick={handleAdd}
                  size="sm"
                  className="w-full bg-restaurant-red hover:bg-restaurant-red/90 text-restaurant-red-foreground gap-1.5 shadow-sm"
                >
                  <Plus className="h-3.5 w-3.5" />
                  Add to Cart
                </Button>
              </motion.div>
            ) : (
              <div className="flex items-center justify-between bg-restaurant-red/5 rounded-lg p-1">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={handleDecrement}
                  className="h-8 w-8 hover:bg-restaurant-red/10 rounded-md"
                >
                  <Minus className="h-3.5 w-3.5 text-restaurant-red" />
                </Button>
                <span className="text-sm font-bold text-restaurant-red min-w-[2rem] text-center">
                  {quantity}
                </span>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={handleIncrement}
                  className="h-8 w-8 hover:bg-restaurant-red/10 rounded-md"
                >
                  <Plus className="h-3.5 w-3.5 text-restaurant-red" />
                </Button>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </motion.div>
  )
}
