'use client'

import { useState, useEffect, useSyncExternalStore } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useTheme } from 'next-themes'
import { motion, AnimatePresence } from 'framer-motion'
import {
  UtensilsCrossed,
  ShoppingCart,
  Sun,
  Moon,
  Menu,
  Sparkles,
  Home,
  BookOpen,
  MessageCircle,
  CalendarDays,
  Package,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
  SheetClose,
} from '@/components/ui/sheet'
import { Separator } from '@/components/ui/separator'
import { useCartStore } from '@/store/cart-store'

const navLinks = [
  { href: '/', label: 'Home', icon: Home },
  { href: '/menu', label: 'Menu', icon: BookOpen },
  { href: '/orders', label: 'Orders', icon: Package },
  { href: '/chat', label: 'Chat', icon: MessageCircle },
  { href: '/reservation', label: 'Reservations', icon: CalendarDays },
]

export function Navigation() {
  const pathname = usePathname()
  const { theme, setTheme } = useTheme()
  const [scrolled, setScrolled] = useState(false)
  const cartItems = useCartStore((state) => state.items)
  const cartCount = cartItems.reduce((sum, item) => sum + item.quantity, 0)

  const mounted = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false
  )

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 10)
    }
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  const toggleTheme = () => {
    setTheme(theme === 'dark' ? 'light' : 'dark')
  }

  return (
    <motion.header
      initial={{ y: -100 }}
      animate={{ y: 0 }}
      transition={{ duration: 0.5, ease: 'easeOut' }}
      className={cn(
        'fixed top-0 left-0 right-0 z-50 transition-all duration-300',
        scrolled
          ? 'bg-background/80 backdrop-blur-xl border-b shadow-sm'
          : 'bg-background/50 backdrop-blur-sm'
      )}
    >
      <nav className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2 group">
            <motion.div
              whileHover={{ rotate: 10, scale: 1.05 }}
              transition={{ type: 'spring', stiffness: 300 }}
              className="flex items-center justify-center w-9 h-9 rounded-lg bg-restaurant-red text-restaurant-red-foreground"
            >
              <UtensilsCrossed className="h-5 w-5" />
            </motion.div>
            <div className="flex flex-col">
              <span className="text-lg font-bold leading-tight tracking-tight text-foreground group-hover:text-restaurant-red transition-colors">
                Lauren Eats
              </span>
              <span className="text-[10px] leading-none text-restaurant-gold font-medium tracking-widest">
                美食
              </span>
            </div>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-1">
            {navLinks.map((link) => {
              const isActive = pathname === link.href
              return (
                <Link key={link.href} href={link.href}>
                  <motion.div
                    whileHover={{ y: -1 }}
                    whileTap={{ scale: 0.97 }}
                    className={cn(
                      'relative px-3 py-2 rounded-md text-sm font-medium transition-colors',
                      isActive
                        ? 'text-restaurant-red'
                        : 'text-muted-foreground hover:text-foreground'
                    )}
                  >
                    {link.label}
                    {isActive && (
                      <motion.div
                        layoutId="activeNav"
                        className="absolute bottom-0 left-1/2 -translate-x-1/2 w-6 h-0.5 rounded-full bg-restaurant-red"
                        transition={{ type: 'spring', stiffness: 380, damping: 30 }}
                      />
                    )}
                  </motion.div>
                </Link>
              )
            })}
          </div>

          {/* Right side actions */}
          <div className="flex items-center gap-2">
            {/* AI Assistant Button */}
            <Link href="/chat" className="hidden sm:block">
              <motion.div
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
              >
                <Button
                  size="sm"
                  className="bg-restaurant-red hover:bg-restaurant-red/90 text-restaurant-red-foreground gap-1.5 shadow-md"
                >
                  <Sparkles className="h-3.5 w-3.5" />
                  AI Assistant
                </Button>
              </motion.div>
            </Link>

            {/* Cart */}
            <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
              <Button variant="ghost" size="icon" className="relative" asChild>
                <Link href="/menu">
                  <ShoppingCart className="h-5 w-5" />
                  {cartCount > 0 && (
                    <Badge
                      className="absolute -top-1 -right-1 h-5 w-5 rounded-full p-0 flex items-center justify-center text-[10px] bg-restaurant-red text-restaurant-red-foreground border-0"
                    >
                      {cartCount}
                    </Badge>
                  )}
                  <span className="sr-only">Shopping cart</span>
                </Link>
              </Button>
            </motion.div>

            {/* Theme Toggle */}
            {mounted && (
              <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={toggleTheme}
                  aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
                >
                  <AnimatePresence mode="wait" initial={false}>
                    {theme === 'dark' ? (
                      <motion.div
                        key="sun"
                        initial={{ y: -10, opacity: 0, rotate: -90 }}
                        animate={{ y: 0, opacity: 1, rotate: 0 }}
                        exit={{ y: 10, opacity: 0, rotate: 90 }}
                        transition={{ duration: 0.2 }}
                      >
                        <Sun className="h-5 w-5" />
                      </motion.div>
                    ) : (
                      <motion.div
                        key="moon"
                        initial={{ y: -10, opacity: 0, rotate: -90 }}
                        animate={{ y: 0, opacity: 1, rotate: 0 }}
                        exit={{ y: 10, opacity: 0, rotate: 90 }}
                        transition={{ duration: 0.2 }}
                      >
                        <Moon className="h-5 w-5" />
                      </motion.div>
                    )}
                  </AnimatePresence>
                </Button>
              </motion.div>
            )}

            {/* Mobile Menu */}
            <div className="md:hidden">
              <Sheet>
                <SheetTrigger asChild>
                  <Button variant="ghost" size="icon" aria-label="Open menu">
                    <Menu className="h-5 w-5" />
                  </Button>
                </SheetTrigger>
                <SheetContent side="right" className="w-72">
                  <SheetHeader className="space-y-3">
                    <SheetTitle className="flex items-center gap-2">
                      <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-restaurant-red text-restaurant-red-foreground">
                        <UtensilsCrossed className="h-4 w-4" />
                      </div>
                      <div className="flex flex-col items-start">
                        <span className="text-base font-bold">Lauren Eats</span>
                        <span className="text-[9px] text-restaurant-gold font-medium tracking-widest">美食</span>
                      </div>
                    </SheetTitle>
                  </SheetHeader>

                  <div className="mt-4 flex flex-col gap-1">
                    {navLinks.map((link) => {
                      const isActive = pathname === link.href
                      const Icon = link.icon
                      return (
                        <SheetClose asChild key={link.href}>
                          <Link href={link.href}>
                            <motion.div
                              whileTap={{ scale: 0.98 }}
                              className={cn(
                                'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                                isActive
                                  ? 'bg-restaurant-red/10 text-restaurant-red'
                                  : 'text-muted-foreground hover:bg-accent hover:text-foreground'
                              )}
                            >
                              <Icon className="h-4 w-4" />
                              {link.label}
                              {isActive && (
                                <div className="ml-auto w-1.5 h-1.5 rounded-full bg-restaurant-red" />
                              )}
                            </motion.div>
                          </Link>
                        </SheetClose>
                      )
                    })}
                  </div>

                  <Separator className="my-4" />

                  <div className="flex flex-col gap-2">
                    <SheetClose asChild>
                      <Link href="/chat">
                        <Button className="w-full bg-restaurant-red hover:bg-restaurant-red/90 text-restaurant-red-foreground gap-2">
                          <Sparkles className="h-4 w-4" />
                          AI Assistant
                        </Button>
                      </Link>
                    </SheetClose>
                    <SheetClose asChild>
                      <Link href="/menu">
                        <Button variant="outline" className="w-full gap-2">
                          <ShoppingCart className="h-4 w-4" />
                          Cart
                          {cartCount > 0 && (
                            <Badge className="ml-auto bg-restaurant-red text-restaurant-red-foreground border-0">
                              {cartCount}
                            </Badge>
                          )}
                        </Button>
                      </Link>
                    </SheetClose>
                  </div>

                  <div className="mt-6">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={toggleTheme}
                      className="w-full justify-start gap-2"
                    >
                      {mounted && theme === 'dark' ? (
                        <>
                          <Sun className="h-4 w-4" />
                          Light Mode
                        </>
                      ) : (
                        <>
                          <Moon className="h-4 w-4" />
                          Dark Mode
                        </>
                      )}
                    </Button>
                  </div>
                </SheetContent>
              </Sheet>
            </div>
          </div>
        </div>
      </nav>
    </motion.header>
  )
}
