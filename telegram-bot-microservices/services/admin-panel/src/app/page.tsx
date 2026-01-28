'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

export default function SearchPage() {
  const [telegramId, setTelegramId] = useState('')
  const router = useRouter()

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    const id = telegramId.trim()
    if (id) {
      router.push(`/admin-panel/user/${id}`)
    }
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh]">
      <h1 className="text-3xl font-bold mb-2">Карточка пользователя</h1>
      <p className="text-tg-muted mb-8">Введите Telegram ID для поиска</p>

      <form onSubmit={handleSearch} className="w-full max-w-md">
        <div className="flex gap-3">
          <input
            type="text"
            value={telegramId}
            onChange={(e) => setTelegramId(e.target.value)}
            placeholder="Telegram ID"
            className="flex-1 px-4 py-3 bg-tg-card border border-tg-border rounded-lg text-tg-text placeholder-tg-muted focus:outline-none focus:border-tg-accent text-lg"
            autoFocus
          />
          <button
            type="submit"
            className="px-6 py-3 bg-tg-accent text-white rounded-lg font-medium hover:bg-blue-500 transition"
          >
            Найти
          </button>
        </div>
      </form>
    </div>
  )
}
