'use client'

import { useState, useRef, useEffect } from 'react'
import { useRouter, usePathname } from 'next/navigation'

export function HeaderAuth() {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const router = useRouter()
  const pathname = usePathname()

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  const handleLogout = async () => {
    await fetch('/admin-panel/api/auth/logout', { method: 'POST' })
    router.push('/admin-panel/login')
    router.refresh()
  }

  // Don't show on login page (after all hooks)
  if (pathname === '/admin-panel/login') return null

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="w-9 h-9 rounded-full bg-tg-card border border-tg-border flex items-center justify-center hover:border-tg-accent transition"
        title="Аккаунт"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-tg-muted">
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
          <circle cx="12" cy="7" r="4" />
        </svg>
      </button>

      {open && (
        <div className="absolute right-0 top-12 bg-tg-card border border-tg-border rounded-lg shadow-lg py-1 min-w-[140px] z-50">
          <button
            onClick={handleLogout}
            className="w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-tg-bg transition"
          >
            Выйти
          </button>
        </div>
      )}
    </div>
  )
}
