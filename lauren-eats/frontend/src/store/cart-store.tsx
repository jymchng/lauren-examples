"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { CartItem, MenuItem } from "@/types";

interface CartState {
  items: CartItem[];

  // Actions
  addItem: (item: MenuItem, quantity?: number, notes?: string) => void;
  removeItem: (menuItemId: string) => void;
  updateQuantity: (menuItemId: string, quantity: number) => void;
  updateNotes: (menuItemId: string, notes: string) => void;
  clearCart: () => void;

  // Computed
  totalAmount: () => number;
  totalItems: () => number;
  getItemById: (menuItemId: string) => CartItem | undefined;
}

export const useCartStore = create<CartState>()(
  persist(
    (set, get) => ({
      items: [],

      addItem: (item: MenuItem, quantity = 1, notes = "") => {
        set((state) => {
          const existingIndex = state.items.findIndex(
            (i) => i.id === item.id && i.notes === notes
          );

          if (existingIndex > -1) {
            // Item with same notes exists — increment quantity
            const updated = [...state.items];
            updated[existingIndex] = {
              ...updated[existingIndex],
              quantity: updated[existingIndex].quantity + quantity,
            };
            return { items: updated };
          }

          // Add new item
          const cartItem: CartItem = {
            id: item.id,
            name: item.name,
            nameZh: item.nameZh,
            description: item.description,
            price: item.price,
            image: item.image,
            categoryId: item.categoryId,
            spicyLevel: item.spicyLevel,
            isVegetarian: item.isVegetarian,
            isVegan: item.isVegan,
            isGlutenFree: item.isGlutenFree,
            isPopular: item.isPopular,
            isAvailable: item.isAvailable,
            calories: item.calories,
            preparationTime: item.preparationTime,
            ingredients: item.ingredients,
            allergens: item.allergens,
            tags: item.tags,
            quantity,
            notes,
          };
          return { items: [...state.items, cartItem] };
        });
      },

      removeItem: (menuItemId: string) => {
        set((state) => ({
          items: state.items.filter((i) => i.id !== menuItemId),
        }));
      },

      updateQuantity: (menuItemId: string, quantity: number) => {
        if (quantity <= 0) {
          get().removeItem(menuItemId);
          return;
        }
        set((state) => ({
          items: state.items.map((i) =>
            i.id === menuItemId ? { ...i, quantity } : i
          ),
        }));
      },

      updateNotes: (menuItemId: string, notes: string) => {
        set((state) => ({
          items: state.items.map((i) =>
            i.id === menuItemId ? { ...i, notes } : i
          ),
        }));
      },

      clearCart: () => {
        set({ items: [] });
      },

      totalAmount: () => {
        return get().items.reduce(
          (sum, item) => sum + item.price * item.quantity,
          0
        );
      },

      totalItems: () => {
        return get().items.reduce((sum, item) => sum + item.quantity, 0);
      },

      getItemById: (menuItemId: string) => {
        return get().items.find((i) => i.id === menuItemId);
      },
    }),
    {
      name: "lauren-eats-cart",
      partialize: (state) => ({ items: state.items }),
    }
  )
);
