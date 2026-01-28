'use client'

import { usePathname } from 'next/navigation'
import { HeaderAuth } from './HeaderAuth'

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const isLogin = pathname === '/admin-panel/login'

  if (isLogin) {
    return <>{children}</>
  }

  return (
    <>
      <header className="bg-tg-secondary border-b border-tg-border px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <a href="/admin-panel" className="text-xl font-bold text-tg-accent">
            Vitte Admin
          </a>
          <div className="flex items-center gap-4">
            <a
              href="/grafana/"
              className="text-sm text-tg-muted hover:text-tg-text transition"
            >
              Grafana
            </a>
            <HeaderAuth />
          </div>
        </div>
      </header>
      <main className="max-w-5xl mx-auto px-6 py-8">{children}</main>
    </>
  )
}
