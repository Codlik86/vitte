'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const router = useRouter()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const res = await fetch('/admin-panel/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      })

      if (!res.ok) {
        setError('Неверный логин или пароль')
        return
      }

      router.push('/admin-panel')
      router.refresh()
    } catch {
      setError('Ошибка подключения')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-tg-bg flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="bg-tg-card border border-tg-border rounded-lg p-8">
          <h1 className="text-2xl font-bold text-tg-accent text-center mb-2">Vitte Admin</h1>
          <p className="text-tg-muted text-center mb-6">Вход в панель управления</p>

          <form onSubmit={handleSubmit}>
            <div className="mb-4">
              <label className="block text-tg-muted text-sm mb-1">Логин</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full px-4 py-3 bg-tg-bg border border-tg-border rounded-lg text-tg-text placeholder-tg-muted focus:outline-none focus:border-tg-accent"
                placeholder="admin"
                autoFocus
                required
              />
            </div>

            <div className="mb-6">
              <label className="block text-tg-muted text-sm mb-1">Пароль</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-3 bg-tg-bg border border-tg-border rounded-lg text-tg-text placeholder-tg-muted focus:outline-none focus:border-tg-accent"
                placeholder="Пароль"
                required
              />
            </div>

            {error && (
              <div className="mb-4 text-center text-red-400 text-sm">{error}</div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-tg-accent text-white rounded-lg font-medium hover:bg-blue-500 transition disabled:opacity-50"
            >
              {loading ? 'Вход...' : 'Войти'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
