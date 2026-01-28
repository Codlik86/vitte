'use client'

import { useEffect, useState, useCallback } from 'react'
import { useParams, useRouter } from 'next/navigation'

const API_BASE = '/admin-panel/api'

interface UserData {
  telegram_id: number
  username: string
  first_name: string
  last_name: string
  language: string
  utm_source: string
  is_active: boolean
  is_blocked: boolean
  is_admin: boolean
  access_status: string
  free_messages_used: number
  free_messages_limit: number
  created_at: string
  last_interaction: string
  has_subscription: string
  subscription_plan: string
  subscription_is_active: boolean
  subscription_started_at: string
  subscription_expires_at: string
  intense_mode: boolean
  fantasy_scenes: boolean
  payments_total_count: number
  payments_total_stars: number
  first_payment: string
  last_payment: string
  messages_count: number
  active_dialogs: number
  features_unlocked: string[]
  images_total_purchased: number
  images_remaining: number
  images_daily_quota: number
  images_daily_used: number
}

interface ActivityItem {
  type: string
  description: string
  details: string
  created_at: string
}

function formatDate(d: string) {
  if (!d) return '—'
  try {
    return new Date(d).toLocaleString('ru-RU', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    })
  } catch { return d }
}

function Card({ title, children, danger }: { title: string; children: React.ReactNode; danger?: boolean }) {
  return (
    <div className={`bg-tg-card border rounded-lg p-5 mb-4 ${danger ? 'border-tg-danger' : 'border-tg-border'}`}>
      <h2 className={`text-lg font-semibold mb-4 ${danger ? 'text-tg-danger' : 'text-tg-accent'}`}>{title}</h2>
      {children}
    </div>
  )
}

function InfoRow({ label, value }: { label: string; value: string | number | boolean | undefined | null }) {
  const display = value === null || value === undefined || value === '' ? '—' : String(value)
  return (
    <div className="flex justify-between py-2 border-b border-tg-border/50 last:border-0">
      <span className="text-tg-muted">{label}</span>
      <span className="font-medium">{display}</span>
    </div>
  )
}

function ActionBtn({ label, onClick, variant = 'default', loading }: {
  label: string; onClick: () => void; variant?: 'default' | 'danger' | 'success' | 'warn'; loading?: boolean
}) {
  const colors = {
    default: 'bg-tg-accent hover:bg-blue-500',
    danger: 'bg-tg-danger hover:bg-red-400',
    success: 'bg-tg-success hover:bg-green-400',
    warn: 'bg-tg-warn hover:bg-orange-400',
  }
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className={`px-3 py-2 text-sm text-white rounded-lg font-medium transition ${colors[variant]} disabled:opacity-50`}
    >
      {loading ? '...' : label}
    </button>
  )
}

export default function UserCardPage() {
  const params = useParams()
  const router = useRouter()
  const telegramId = params.id as string

  const [user, setUser] = useState<UserData | null>(null)
  const [activity, setActivity] = useState<ActivityItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [actionLoading, setActionLoading] = useState('')
  const [toast, setToast] = useState('')

  const showToast = (msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(''), 3000)
  }

  const loadUser = useCallback(async () => {
    try {
      setLoading(true)
      setError('')
      const res = await fetch(`${API_BASE}/user/${telegramId}/card`)
      if (!res.ok) throw new Error(`${res.status}`)
      setUser(await res.json())
    } catch (e: any) {
      setError(`Пользователь не найден: ${e.message}`)
    } finally {
      setLoading(false)
    }
  }, [telegramId])

  const loadActivity = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/user/${telegramId}/activity`)
      if (res.ok) setActivity(await res.json())
    } catch {}
  }, [telegramId])

  useEffect(() => {
    loadUser()
    loadActivity()
  }, [loadUser, loadActivity])

  const doAction = async (path: string, body: object, label: string) => {
    try {
      setActionLoading(label)
      const res = await fetch(`${API_BASE}/user/${telegramId}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) throw new Error(await res.text())
      showToast(`${label} — OK`)
      await loadUser()
      await loadActivity()
    } catch (e: any) {
      showToast(`Ошибка: ${e.message}`)
    } finally {
      setActionLoading('')
    }
  }

  const handleDelete = async () => {
    if (!confirm(`Удалить аккаунт ${telegramId}? Это действие необратимо!`)) return
    if (!confirm('Точно удалить? Все данные будут потеряны!')) return
    try {
      setActionLoading('delete')
      const res = await fetch(`${API_BASE}/user/${telegramId}`, { method: 'DELETE' })
      if (!res.ok) throw new Error(await res.text())
      showToast('Аккаунт удалён')
      setTimeout(() => router.push('/admin-panel'), 1500)
    } catch (e: any) {
      showToast(`Ошибка: ${e.message}`)
    } finally {
      setActionLoading('')
    }
  }

  if (loading) return <div className="text-center py-20 text-tg-muted text-lg">Загрузка...</div>
  if (error) return (
    <div className="text-center py-20">
      <p className="text-tg-danger text-lg mb-4">{error}</p>
      <button onClick={() => router.push('/admin-panel')} className="text-tg-accent hover:underline">
        Назад к поиску
      </button>
    </div>
  )
  if (!user) return null

  const subActive = user.has_subscription === 'true'

  return (
    <div className="relative">
      {toast && (
        <div className="fixed top-4 right-4 bg-tg-card border border-tg-accent text-tg-text px-4 py-3 rounded-lg shadow-lg z-50">
          {toast}
        </div>
      )}

      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => router.push('/admin-panel')} className="text-tg-muted hover:text-tg-text transition">
          &larr; Назад
        </button>
        <h1 className="text-2xl font-bold">Пользователь {telegramId}</h1>
      </div>

      {/* Основная информация */}
      <Card title="Основная информация">
        <InfoRow label="Telegram ID" value={user.telegram_id} />
        <InfoRow label="Username" value={user.username ? `@${user.username}` : '—'} />
        <InfoRow label="Имя" value={user.first_name} />
        <InfoRow label="Фамилия" value={user.last_name} />
        <InfoRow label="Язык" value={user.language} />
        <InfoRow label="UTM метка" value={user.utm_source} />
        <InfoRow label="Статус доступа" value={user.access_status} />
        <InfoRow label="Бесплатные сообщения" value={`${user.free_messages_used} / ${user.free_messages_limit}`} />
        <InfoRow label="Дата регистрации" value={formatDate(user.created_at)} />
        <InfoRow label="Последняя активность" value={formatDate(user.last_interaction)} />
      </Card>

      {/* Подписка */}
      <Card title="Подписка">
        <InfoRow label="Статус" value={subActive ? 'Активна' : 'Нет'} />
        <InfoRow label="План" value={user.subscription_plan} />
        <InfoRow label="Действует с" value={formatDate(user.subscription_started_at)} />
        <InfoRow label="Действует до" value={formatDate(user.subscription_expires_at)} />
        <InfoRow label="Intense Mode" value={user.intense_mode ? 'Да' : 'Нет'} />
        <InfoRow label="Fantasy Scenes" value={user.fantasy_scenes ? 'Да' : 'Нет'} />
        <div className="flex flex-wrap gap-2 mt-4">
          <ActionBtn label="Premium 30д" variant="success"
            loading={actionLoading === 'sub30'}
            onClick={() => doAction('/subscription', { action: 'grant_premium', days: 30 }, 'sub30')} />
          <ActionBtn label="Premium 90д" variant="success"
            loading={actionLoading === 'sub90'}
            onClick={() => doAction('/subscription', { action: 'grant_premium', days: 90 }, 'sub90')} />
          <ActionBtn label="Premium 365д" variant="success"
            loading={actionLoading === 'sub365'}
            onClick={() => doAction('/subscription', { action: 'grant_premium', days: 365 }, 'sub365')} />
          <ActionBtn label="Убрать подписку" variant="danger"
            loading={actionLoading === 'subrevoke'}
            onClick={() => doAction('/subscription', { action: 'revoke' }, 'subrevoke')} />
        </div>
      </Card>

      {/* Изображения */}
      <Card title="Изображения">
        <InfoRow label="Куплено всего" value={user.images_total_purchased} />
        <InfoRow label="Осталось" value={user.images_remaining} />
        <InfoRow label="Дневная квота" value={`${user.images_daily_used} / ${user.images_daily_quota}`} />
        <div className="flex flex-wrap gap-2 mt-4">
          <ActionBtn label="+10" variant="success"
            loading={actionLoading === 'img10'}
            onClick={() => doAction('/images', { action: 'add', amount: 10 }, 'img10')} />
          <ActionBtn label="+50" variant="success"
            loading={actionLoading === 'img50'}
            onClick={() => doAction('/images', { action: 'add', amount: 50 }, 'img50')} />
          <ActionBtn label="+100" variant="success"
            loading={actionLoading === 'img100'}
            onClick={() => doAction('/images', { action: 'add', amount: 100 }, 'img100')} />
          <ActionBtn label="Обнулить" variant="danger"
            loading={actionLoading === 'imgreset'}
            onClick={() => doAction('/images', { action: 'reset' }, 'imgreset')} />
        </div>
      </Card>

      {/* Улучшения */}
      <Card title="Улучшения">
        <div className="mb-3">
          {user.features_unlocked.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {user.features_unlocked.map((f) => (
                <span key={f} className="px-3 py-1 bg-tg-success/20 text-tg-success rounded-full text-sm">{f}</span>
              ))}
            </div>
          ) : (
            <p className="text-tg-muted">Нет разблокированных улучшений</p>
          )}
        </div>
        <div className="flex flex-wrap gap-2 mt-4">
          <ActionBtn label="Дать intense_mode" variant="success"
            loading={actionLoading === 'feat_intense_grant'}
            onClick={() => doAction('/features', { action: 'grant', feature_code: 'intense_mode' }, 'feat_intense_grant')} />
          <ActionBtn label="Убрать intense_mode" variant="danger"
            loading={actionLoading === 'feat_intense_revoke'}
            onClick={() => doAction('/features', { action: 'revoke', feature_code: 'intense_mode' }, 'feat_intense_revoke')} />
          <ActionBtn label="Дать fantasy_scenes" variant="success"
            loading={actionLoading === 'feat_fantasy_grant'}
            onClick={() => doAction('/features', { action: 'grant', feature_code: 'fantasy_scenes' }, 'feat_fantasy_grant')} />
          <ActionBtn label="Убрать fantasy_scenes" variant="danger"
            loading={actionLoading === 'feat_fantasy_revoke'}
            onClick={() => doAction('/features', { action: 'revoke', feature_code: 'fantasy_scenes' }, 'feat_fantasy_revoke')} />
        </div>
      </Card>

      {/* Платежи */}
      <Card title="Платежи">
        <InfoRow label="Всего платежей" value={user.payments_total_count} />
        <InfoRow label="Потрачено звёзд" value={user.payments_total_stars} />
        <InfoRow label="Первый платёж" value={formatDate(user.first_payment)} />
        <InfoRow label="Последний платёж" value={formatDate(user.last_payment)} />
      </Card>

      {/* История активности */}
      <Card title="История активности">
        {activity.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-tg-muted border-b border-tg-border">
                  <th className="text-left py-2 pr-4">Время</th>
                  <th className="text-left py-2 pr-4">Тип</th>
                  <th className="text-left py-2 pr-4">Описание</th>
                  <th className="text-left py-2">Детали</th>
                </tr>
              </thead>
              <tbody>
                {activity.map((item, i) => (
                  <tr key={i} className="border-b border-tg-border/30">
                    <td className="py-2 pr-4 text-tg-muted whitespace-nowrap">{formatDate(item.created_at)}</td>
                    <td className="py-2 pr-4">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                        item.type === 'purchase' ? 'bg-tg-warn/20 text-tg-warn' :
                        item.type === 'dialog' ? 'bg-tg-accent/20 text-tg-accent' :
                        item.type === 'subscription' ? 'bg-tg-success/20 text-tg-success' :
                        'bg-tg-muted/20 text-tg-muted'
                      }`}>
                        {item.type === 'purchase' ? 'Покупка' :
                         item.type === 'dialog' ? 'Диалог' :
                         item.type === 'subscription' ? 'Подписка' :
                         item.type === 'feature' ? 'Улучшение' : item.type}
                      </span>
                    </td>
                    <td className="py-2 pr-4">{item.description}</td>
                    <td className="py-2 text-tg-muted">{item.details}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-tg-muted">Нет записей активности</p>
        )}
      </Card>

      {/* Опасная зона */}
      <Card title="Опасная зона" danger>
        <p className="text-tg-muted mb-4">Полное удаление аккаунта из базы данных и кеша. Это действие необратимо.</p>
        <ActionBtn label="Удалить аккаунт" variant="danger"
          loading={actionLoading === 'delete'}
          onClick={handleDelete} />
      </Card>
    </div>
  )
}
