'use client'

import Link from 'next/link'
import { motion } from 'framer-motion'
import {
  UtensilsCrossed,
  Phone,
  Mail,
  MapPin,
  Instagram,
  Twitter,
  Facebook,
  Sparkles,
  Heart,
} from 'lucide-react'
import { Separator } from '@/components/ui/separator'

const quickLinks = [
  { href: '/', label: 'Home' },
  { href: '/menu', label: 'Menu' },
  { href: '/chat', label: 'AI Chat' },
  { href: '/reservation', label: 'Reservations' },
]

const socialLinks = [
  { href: '#', label: 'Instagram', icon: Instagram },
  { href: '#', label: 'Twitter', icon: Twitter },
  { href: '#', label: 'Facebook', icon: Facebook },
]

export function Footer() {
  return (
    <footer className="bg-restaurant-dark text-white/80 mt-auto">
      {/* Decorative top border */}
      <div className="h-1 w-full bg-gradient-to-r from-restaurant-red via-restaurant-gold to-restaurant-red" />

      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8 lg:gap-12">
          {/* Brand */}
          <div className="sm:col-span-2 lg:col-span-1">
            <Link href="/" className="flex items-center gap-2 group">
              <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-restaurant-red text-white">
                <UtensilsCrossed className="h-5 w-5" />
              </div>
              <div className="flex flex-col">
                <span className="text-lg font-bold text-white group-hover:text-restaurant-gold transition-colors">
                  Lauren Eats
                </span>
                <span className="text-[10px] leading-none text-restaurant-gold font-medium tracking-widest">
                  美食
                </span>
              </div>
            </Link>
            <p className="mt-4 text-sm text-white/60 leading-relaxed max-w-xs">
              Where tradition meets innovation. Experience authentic Chinese cuisine,
              elevated by AI-powered personalization and modern culinary artistry.
            </p>
            <div className="mt-4 flex items-center gap-1.5">
              <Sparkles className="h-3.5 w-3.5 text-restaurant-gold" />
              <span className="text-xs font-medium text-restaurant-gold tracking-wide">
                Powered by Lauren AI
              </span>
            </div>
          </div>

          {/* Quick Links */}
          <div>
            <h3 className="text-sm font-semibold text-white tracking-wide uppercase mb-4">
              Quick Links
            </h3>
            <ul className="space-y-2.5">
              {quickLinks.map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="text-sm text-white/50 hover:text-restaurant-gold transition-colors duration-200"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Contact */}
          <div>
            <h3 className="text-sm font-semibold text-white tracking-wide uppercase mb-4">
              Contact Us
            </h3>
            <ul className="space-y-3">
              <li className="flex items-start gap-2.5">
                <Phone className="h-4 w-4 mt-0.5 text-restaurant-gold shrink-0" />
                <span className="text-sm text-white/50">(555) 888-6688</span>
              </li>
              <li className="flex items-start gap-2.5">
                <Mail className="h-4 w-4 mt-0.5 text-restaurant-gold shrink-0" />
                <span className="text-sm text-white/50">hello@laureneats.com</span>
              </li>
              <li className="flex items-start gap-2.5">
                <MapPin className="h-4 w-4 mt-0.5 text-restaurant-gold shrink-0" />
                <span className="text-sm text-white/50">
                  888 Dragon Gate Lane<br />
                  San Francisco, CA 94102
                </span>
              </li>
            </ul>
          </div>

          {/* Social & Hours */}
          <div>
            <h3 className="text-sm font-semibold text-white tracking-wide uppercase mb-4">
              Follow Us
            </h3>
            <div className="flex items-center gap-2">
              {socialLinks.map((social) => {
                const Icon = social.icon
                return (
                  <motion.a
                    key={social.label}
                    href={social.href}
                    aria-label={social.label}
                    whileHover={{ scale: 1.1, y: -2 }}
                    whileTap={{ scale: 0.95 }}
                    className="flex items-center justify-center w-9 h-9 rounded-full bg-white/10 text-white/60 hover:bg-restaurant-red hover:text-white transition-colors duration-200"
                  >
                    <Icon className="h-4 w-4" />
                  </motion.a>
                )
              })}
            </div>

            <h3 className="text-sm font-semibold text-white tracking-wide uppercase mt-6 mb-3">
              Hours
            </h3>
            <ul className="space-y-1.5 text-sm text-white/50">
              <li className="flex justify-between">
                <span>Mon - Thu</span>
                <span>11am - 10pm</span>
              </li>
              <li className="flex justify-between">
                <span>Fri - Sat</span>
                <span>11am - 11pm</span>
              </li>
              <li className="flex justify-between">
                <span>Sunday</span>
                <span>12pm - 9pm</span>
              </li>
            </ul>
          </div>
        </div>

        <Separator className="my-8 bg-white/10" />

        {/* Bottom bar */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-xs text-white/40">
            &copy; {new Date().getFullYear()} Lauren Eats. All rights reserved.
          </p>
          <div className="flex items-center gap-1 text-xs text-white/40">
            <span>Made with</span>
            <Heart className="h-3 w-3 text-restaurant-red fill-restaurant-red" />
            <span>and</span>
            <Sparkles className="h-3 w-3 text-restaurant-gold" />
            <span>by Lauren AI</span>
          </div>
        </div>
      </div>
    </footer>
  )
}
