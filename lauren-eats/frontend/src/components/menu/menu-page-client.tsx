'use client'

import { useState, useMemo, useCallback, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Search,
  ShoppingCart,
  Flame,
  Leaf,
  Wheat,
  X,
  SlidersHorizontal,
  Loader2,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import {
  Sheet,
  SheetContent,
  SheetTitle,
} from '@/components/ui/sheet'
import { MenuCard } from '@/components/menu/menu-card'
import { CartSidebar } from '@/components/menu/cart-sidebar'
import { useCart } from '@/hooks/use-cart'
import type { Category, MenuItem, SpicyLevel, Pagination } from '@/types'

interface MenuPageClientProps {
  categories: Category[]
  initialItems: MenuItem[]
}

type DietaryFilterType = 'vegetarian' | 'vegan' | 'glutenFree'

const ITEMS_PER_PAGE = 12

export function MenuPageClient({ categories, initialItems }: MenuPageClientProps) {
  const { totalItems } = useCart()

  // ─── State ────────────────────────────────────────────────────────
  const [activeCategory, setActiveCategory] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout>>()
  const [dietaryFilters, setDietaryFilters] = useState<Set<DietaryFilterType>>(new Set())
  const [maxSpicyLevel, setMaxSpicyLevel] = useState<SpicyLevel>(5)
  const [cartOpen, setCartOpen] = useState(false)
  const [showFilters, setShowFilters] = useState(false)

  // ─── Pagination State ────────────────────────────────────────────
  const [currentPage, setCurrentPage] = useState(1)
  const [allItems, setAllItems] = useState<MenuItem[]>(initialItems)
  const [pagination, setPagination] = useState<Pagination>({
    page: 1,
    limit: ITEMS_PER_PAGE,
    total: initialItems.length,
    totalPages: Math.ceil(initialItems.length / ITEMS_PER_PAGE),
  })
  const [loadingMore, setLoadingMore] = useState(false)

  // Debounced search
  useEffect(() => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current)
    }
    debounceTimerRef.current = setTimeout(() => {
      setDebouncedSearch(searchQuery)
    }, 300)
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current)
      }
    }
  }, [searchQuery])

  // Reset to page 1 when filters change
  useEffect(() => {
    setCurrentPage(1)
  }, [activeCategory, debouncedSearch, dietaryFilters, maxSpicyLevel])

  // ─── Filter logic (client-side over all loaded items) ────────────
  const filteredItems = useMemo(() => {
    let items = [...allItems]

    // Category filter
    if (activeCategory !== 'all') {
      items = items.filter((item) => {
        const category = categories.find((c) => c.id === item.categoryId)
        return category?.slug === activeCategory
      })
    }

    // Search filter
    if (debouncedSearch.trim()) {
      const query = debouncedSearch.toLowerCase().trim()
      items = items.filter(
        (item) =>
          item.name.toLowerCase().includes(query) ||
          (item.nameZh && item.nameZh.toLowerCase().includes(query)) ||
          item.description.toLowerCase().includes(query)
      )
    }

    // Dietary filters
    dietaryFilters.forEach((filter) => {
      switch (filter) {
        case 'vegetarian':
          items = items.filter((item) => item.isVegetarian)
          break
        case 'vegan':
          items = items.filter((item) => item.isVegan)
          break
        case 'glutenFree':
          items = items.filter((item) => item.isGlutenFree)
          break
      }
    })

    // Spicy level filter
    if (maxSpicyLevel < 5) {
      items = items.filter((item) => item.spicyLevel <= maxSpicyLevel)
    }

    // Sort: popular first, then by name
    items.sort((a, b) => {
      if (a.isPopular !== b.isPopular) return a.isPopular ? -1 : 1
      return a.name.localeCompare(b.name)
    })

    return items
  }, [allItems, activeCategory, debouncedSearch, dietaryFilters, maxSpicyLevel, categories])

  // ─── Paginate the filtered results ───────────────────────────────
  const totalFiltered = filteredItems.length
  const totalPages = Math.max(1, Math.ceil(totalFiltered / ITEMS_PER_PAGE))
  const safeCurrentPage = Math.min(currentPage, totalPages)

  const paginatedItems = useMemo(() => {
    const start = (safeCurrentPage - 1) * ITEMS_PER_PAGE
    const end = start + ITEMS_PER_PAGE
    return filteredItems.slice(start, end)
  }, [filteredItems, safeCurrentPage])

  const hasMore = safeCurrentPage < totalPages

  // ─── Load More handler ───────────────────────────────────────────
  const handleLoadMore = useCallback(async () => {
    if (loadingMore) return
    setLoadingMore(true)

    try {
      const nextPage = Math.ceil(allItems.length / ITEMS_PER_PAGE) + 1
      const params = new URLSearchParams()
      params.set('page', String(nextPage))
      params.set('limit', String(ITEMS_PER_PAGE))

      const res = await fetch(`/api/menu?${params.toString()}`)
      const data = await res.json()

      if (data.success && data.data) {
        setAllItems((prev) => {
          // Avoid duplicates
          const existingIds = new Set(prev.map((item) => item.id))
          const newItems = data.data.filter((item: MenuItem) => !existingIds.has(item.id))
          return [...prev, ...newItems]
        })
        if (data.pagination) {
          setPagination(data.pagination)
        }
      }
    } catch (err) {
      console.error('Error loading more items:', err)
    } finally {
      setLoadingMore(false)
    }
  }, [allItems, loadingMore])

  // ─── Page navigation ─────────────────────────────────────────────
  const goToPage = useCallback(
    (page: number) => {
      setCurrentPage(Math.max(1, Math.min(page, totalPages)))
      // Scroll to top of grid
      window.scrollTo({ top: 300, behavior: 'smooth' })
    },
    [totalPages]
  )

  const toggleDietaryFilter = useCallback((filter: DietaryFilterType) => {
    setDietaryFilters((prev) => {
      const next = new Set(prev)
      if (next.has(filter)) {
        next.delete(filter)
      } else {
        next.add(filter)
      }
      return next
    })
  }, [])

  const clearAllFilters = useCallback(() => {
    setActiveCategory('all')
    setSearchQuery('')
    setDebouncedSearch('')
    setDietaryFilters(new Set())
    setMaxSpicyLevel(5)
  }, [])

  const hasActiveFilters =
    activeCategory !== 'all' ||
    debouncedSearch.trim() !== '' ||
    dietaryFilters.size > 0 ||
    maxSpicyLevel < 5

  // Category data with "All" option
  const allCategories = useMemo(
    () => [
      { id: 'all', name: 'All', nameZh: '全部', slug: 'all', icon: '🍽️' },
      ...categories.map((c) => ({
        id: c.id,
        name: c.name,
        nameZh: c.nameZh,
        slug: c.slug,
        icon: c.icon,
      })),
    ],
    [categories]
  )

  // Generate page numbers for pagination
  const pageNumbers = useMemo(() => {
    const pages: (number | 'ellipsis')[] = []
    if (totalPages <= 7) {
      for (let i = 1; i <= totalPages; i++) pages.push(i)
    } else {
      pages.push(1)
      if (safeCurrentPage > 3) pages.push('ellipsis')
      for (
        let i = Math.max(2, safeCurrentPage - 1);
        i <= Math.min(totalPages - 1, safeCurrentPage + 1);
        i++
      ) {
        pages.push(i)
      }
      if (safeCurrentPage < totalPages - 2) pages.push('ellipsis')
      pages.push(totalPages)
    }
    return pages
  }, [totalPages, safeCurrentPage])

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
              Our <span className="text-restaurant-red">Menu</span>
            </h1>
            <p className="mt-1 text-restaurant-gold font-medium text-lg">我们的菜单</p>
            <p className="mt-2 text-sm text-muted-foreground max-w-md mx-auto">
              Discover authentic Chinese cuisine crafted with tradition and innovation
            </p>
          </motion.div>
        </div>
      </div>

      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 pb-24 lg:pb-8">
        {/* Search & Filter Bar */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.1 }}
          className="sticky top-16 z-30 bg-background/80 backdrop-blur-xl -mx-4 sm:-mx-6 lg:-mx-8 px-4 sm:px-6 lg:px-8 py-3 border-b border-border/50"
        >
          <div className="flex items-center gap-3">
            {/* Search Input */}
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                type="text"
                placeholder="Search dishes... (搜索菜品)"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 pr-9 h-10 bg-muted/50 border-border/50 focus:border-restaurant-red/50 focus:ring-restaurant-red/20"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2"
                >
                  <X className="h-4 w-4 text-muted-foreground hover:text-foreground" />
                </button>
              )}
            </div>

            {/* Filter Toggle */}
            <Button
              variant="outline"
              size="icon"
              onClick={() => setShowFilters(!showFilters)}
              className={showFilters ? 'border-restaurant-red/50 bg-restaurant-red/5' : ''}
            >
              <SlidersHorizontal className="h-4 w-4" />
            </Button>

            {/* Cart Button (Desktop) */}
            <Button
              variant="outline"
              size="default"
              onClick={() => setCartOpen(true)}
              className="hidden lg:flex gap-2 relative"
            >
              <ShoppingCart className="h-4 w-4" />
              Cart
              {totalItems > 0 && (
                <Badge className="bg-restaurant-red text-restaurant-red-foreground border-0 text-[10px] h-5 min-w-[20px] flex items-center justify-center">
                  {totalItems}
                </Badge>
              )}
            </Button>
          </div>

          {/* Dietary & Spicy Filters */}
          <AnimatePresence>
            {showFilters && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="overflow-hidden"
              >
                <div className="pt-3 space-y-3">
                  {/* Dietary Filters */}
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-medium text-muted-foreground mr-1">
                      Dietary:
                    </span>
                    {(
                      [
                        { key: 'vegetarian' as DietaryFilterType, label: 'Vegetarian', icon: Leaf, color: 'emerald' },
                        { key: 'vegan' as DietaryFilterType, label: 'Vegan', icon: Leaf, color: 'green' },
                        { key: 'glutenFree' as DietaryFilterType, label: 'Gluten-Free', icon: Wheat, color: 'amber' },
                      ] as const
                    ).map((filter) => {
                      const Icon = filter.icon
                      const isActive = dietaryFilters.has(filter.key)
                      return (
                        <button
                          key={filter.key}
                          onClick={() => toggleDietaryFilter(filter.key)}
                          className={`
                            inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all
                            ${
                              isActive
                                ? 'bg-restaurant-red text-restaurant-red-foreground shadow-sm'
                                : 'bg-muted/50 text-muted-foreground hover:bg-muted border border-border/50'
                            }
                          `}
                        >
                          <Icon className="h-3 w-3" />
                          {filter.label}
                        </button>
                      )
                    })}
                  </div>

                  {/* Spicy Level Filter */}
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-medium text-muted-foreground mr-1">
                      Max Spice:
                    </span>
                    {([0, 1, 2, 3, 4, 5] as SpicyLevel[]).map((level) => (
                      <button
                        key={level}
                        onClick={() => setMaxSpicyLevel(level)}
                        className={`
                          inline-flex items-center gap-1 px-2.5 py-1.5 rounded-full text-xs font-medium transition-all
                          ${
                            maxSpicyLevel === level
                              ? 'bg-restaurant-red text-restaurant-red-foreground shadow-sm'
                              : 'bg-muted/50 text-muted-foreground hover:bg-muted border border-border/50'
                          }
                        `}
                      >
                        {level === 0 ? (
                          'None'
                        ) : (
                          <>
                            {Array.from({ length: level }).map((_, i) => (
                              <Flame key={i} className="h-2.5 w-2.5 fill-current" />
                            ))}
                          </>
                        )}
                      </button>
                    ))}
                  </div>

                  {/* Clear Filters */}
                  {hasActiveFilters && (
                    <button
                      onClick={clearAllFilters}
                      className="text-xs text-restaurant-red hover:underline"
                    >
                      Clear all filters
                    </button>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* Category Tabs/Pills */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.4, delay: 0.2 }}
          className="mt-4 mb-6"
        >
          <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-none -mx-4 px-4 sm:mx-0 sm:px-0">
            {allCategories.map((cat) => {
              const isActive = activeCategory === cat.slug
              return (
                <motion.button
                  key={cat.id}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => setActiveCategory(cat.slug)}
                  className={`
                    flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-all shrink-0
                    ${
                      isActive
                        ? 'bg-restaurant-red text-restaurant-red-foreground shadow-md shadow-restaurant-red/20'
                        : 'bg-muted/50 text-muted-foreground hover:bg-muted hover:text-foreground border border-border/50'
                    }
                  `}
                >
                  <span className="text-base">{cat.icon}</span>
                  <span>{cat.name}</span>
                  {cat.nameZh && (
                    <span
                      className={`text-[10px] ${
                        isActive ? 'text-restaurant-red-foreground/70' : 'text-restaurant-gold'
                      }`}
                    >
                      {cat.nameZh}
                    </span>
                  )}
                </motion.button>
              )
            })}
          </div>
        </motion.div>

        {/* Results count & pagination info */}
        <div className="flex items-center justify-between mb-4">
          <p className="text-sm text-muted-foreground">
            Showing <span className="font-medium text-foreground">{paginatedItems.length}</span> of{' '}
            <span className="font-medium text-foreground">{totalFiltered}</span>{' '}
            {totalFiltered === 1 ? 'dish' : 'dishes'}
            {totalFiltered !== allItems.length && (
              <span className="text-muted-foreground/60"> (filtered from {allItems.length} total)</span>
            )}
          </p>
          {totalPages > 1 && (
            <p className="text-xs text-muted-foreground hidden sm:block">
              Page {safeCurrentPage} of {totalPages}
            </p>
          )}
        </div>

        {/* Menu Grid */}
        <AnimatePresence mode="wait">
          {paginatedItems.length > 0 ? (
            <motion.div
              key={activeCategory + debouncedSearch + safeCurrentPage}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6"
            >
              {paginatedItems.map((item, index) => (
                <motion.div
                  key={item.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, delay: Math.min(index * 0.05, 0.3) }}
                >
                  <MenuCard item={item} />
                </motion.div>
              ))}
            </motion.div>
          ) : (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex flex-col items-center justify-center py-20 text-center"
            >
              <div className="w-20 h-20 rounded-full bg-muted/50 flex items-center justify-center mb-4">
                <Search className="h-8 w-8 text-muted-foreground/30" />
              </div>
              <p className="text-lg font-medium text-foreground">No dishes found</p>
              <p className="text-sm text-muted-foreground mt-1 max-w-sm">
                Try adjusting your filters or search query to find what you&apos;re looking for
              </p>
              {hasActiveFilters && (
                <Button
                  variant="outline"
                  onClick={clearAllFilters}
                  className="mt-4 gap-2 border-restaurant-red/30 text-restaurant-red hover:bg-restaurant-red/10"
                >
                  Clear Filters
                </Button>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* ─── Pagination Controls ──────────────────────────────────── */}
        {totalFiltered > ITEMS_PER_PAGE && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="mt-8 flex flex-col items-center gap-4"
          >
            {/* Page number buttons */}
            <div className="flex items-center gap-1">
              {/* Previous */}
              <Button
                variant="outline"
                size="icon"
                className="h-9 w-9"
                disabled={safeCurrentPage === 1}
                onClick={() => goToPage(safeCurrentPage - 1)}
              >
                <ChevronLeft className="h-4 w-4" />
                <span className="sr-only">Previous page</span>
              </Button>

              {/* Page numbers */}
              {pageNumbers.map((page, idx) =>
                page === 'ellipsis' ? (
                  <span key={`ellipsis-${idx}`} className="px-2 text-muted-foreground text-sm">
                    ...
                  </span>
                ) : (
                  <Button
                    key={page}
                    variant={page === safeCurrentPage ? 'default' : 'outline'}
                    size="icon"
                    className={cn(
                      'h-9 w-9 text-sm font-medium',
                      page === safeCurrentPage &&
                        'bg-restaurant-red hover:bg-restaurant-red/90 text-restaurant-red-foreground'
                    )}
                    onClick={() => goToPage(page)}
                  >
                    {page}
                  </Button>
                )
              )}

              {/* Next */}
              <Button
                variant="outline"
                size="icon"
                className="h-9 w-9"
                disabled={safeCurrentPage === totalPages}
                onClick={() => goToPage(safeCurrentPage + 1)}
              >
                <ChevronRight className="h-4 w-4" />
                <span className="sr-only">Next page</span>
              </Button>
            </div>

            {/* Load More button */}
            {hasMore && (
              <Button
                variant="outline"
                onClick={handleLoadMore}
                disabled={loadingMore}
                className="gap-2 border-restaurant-red/30 text-restaurant-red hover:bg-restaurant-red/10 min-w-[200px]"
              >
                {loadingMore ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Loading...
                  </>
                ) : (
                  <>
                    Load More Dishes
                    <Badge variant="secondary" className="text-[10px] ml-1">
                      {totalFiltered - safeCurrentPage * ITEMS_PER_PAGE > 0
                        ? `${Math.min(ITEMS_PER_PAGE, totalFiltered - safeCurrentPage * ITEMS_PER_PAGE)} more`
                        : 'more'}
                    </Badge>
                  </>
                )}
              </Button>
            )}
          </motion.div>
        )}
      </div>

      {/* Cart Sidebar (Sheet) */}
      <Sheet open={cartOpen} onOpenChange={setCartOpen}>
        <SheetContent side="right" className="w-full sm:max-w-md p-0">
          <SheetTitle className="sr-only">Shopping Cart</SheetTitle>
          <CartSidebar open={cartOpen} onClose={() => setCartOpen(false)} />
        </SheetContent>
      </Sheet>

      {/* Floating Cart Button (Mobile) */}
      {totalItems > 0 && (
        <motion.div
          initial={{ y: 100, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          className="fixed bottom-6 right-6 z-40 lg:hidden"
        >
          <Button
            onClick={() => setCartOpen(true)}
            className="h-14 w-14 rounded-full bg-restaurant-red hover:bg-restaurant-red/90 text-restaurant-red-foreground shadow-xl shadow-restaurant-red/30 relative"
            size="icon"
          >
            <ShoppingCart className="h-6 w-6" />
            <Badge className="absolute -top-1 -right-1 h-6 min-w-[24px] flex items-center justify-center bg-restaurant-gold text-restaurant-gold-foreground border-0 text-xs font-bold">
              {totalItems}
            </Badge>
          </Button>
        </motion.div>
      )}
    </div>
  )
}

// Helper - cn utility is imported elsewhere but we need it here too
function cn(...inputs: (string | boolean | undefined | null)[]) {
  return inputs.filter(Boolean).join(' ')
}
