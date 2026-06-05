'use client'

import { useCartStore } from '@/store/cart-store'
import type { MenuItem } from '@/types'

export function useCart() {
  const items = useCartStore((state) => state.items)
  const addItem = useCartStore((state) => state.addItem)
  const removeItem = useCartStore((state) => state.removeItem)
  const updateQuantity = useCartStore((state) => state.updateQuantity)
  const clearCart = useCartStore((state) => state.clearCart)
  const totalAmount = useCartStore((state) => state.totalAmount)
  const totalItems = useCartStore((state) => state.totalItems)

  return {
    items,
    addItem: (item: MenuItem, quantity?: number, notes?: string) =>
      addItem(item, quantity, notes),
    removeItem,
    updateQuantity,
    clearCart,
    totalAmount: totalAmount(),
    totalItems: totalItems(),
  }
}
