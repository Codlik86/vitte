import type { Metadata } from 'next'
import './globals.css'
import { Shell } from './Shell'

export const metadata: Metadata = {
  title: 'Vitte Admin Panel',
  description: 'User management panel',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <body className="min-h-screen bg-tg-bg text-tg-text">
        <Shell>{children}</Shell>
      </body>
    </html>
  )
}
