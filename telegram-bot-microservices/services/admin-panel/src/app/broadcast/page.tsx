'use client'

import { useEffect, useState, useCallback } from 'react'

const API_BASE = '/admin-panel/api'

// ==================== TYPES ====================

interface ButtonData {
  text: string
  callback_data: string
}

interface BroadcastData {
  id: number
  name: string
  broadcast_type: string
  status: string
  text: string
  media_url: string | null
  media_type: string | null
  buttons: ButtonData[] | null
  gift_images: number
  delay_minutes: number | null
  scheduled_at: string | null
  total_recipients: number
  sent_count: number
  failed_count: number
  created_at: string
  started_at: string | null
  completed_at: string | null
  progress_percent: number
}

// ==================== HELPERS ====================

function formatDate(d: string | null) {
  if (!d) return '—'
  try {
    return new Date(d).toLocaleString('ru-RU', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    })
  } catch { return d }
}

function getStatusBadge(status: string) {
  const styles: Record<string, string> = {
    draft: 'bg-tg-muted/20 text-tg-muted',
    scheduled: 'bg-tg-accent/20 text-tg-accent',
    running: 'bg-tg-warn/20 text-tg-warn',
    completed: 'bg-tg-success/20 text-tg-success',
    cancelled: 'bg-tg-danger/20 text-tg-danger',
    failed: 'bg-tg-danger/20 text-tg-danger',
  }
  const labels: Record<string, string> = {
    draft: 'Черновик',
    scheduled: 'Запланирована',
    running: 'Выполняется',
    completed: 'Завершена',
    cancelled: 'Отменена',
    failed: 'Ошибка',
  }
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${styles[status] || styles.draft}`}>
      {labels[status] || status}
    </span>
  )
}

function getTypeBadge(type: string) {
  if (type === 'new_user') {
    return <span className="px-2 py-0.5 rounded text-xs font-medium bg-purple-500/20 text-purple-400">Новые юзеры</span>
  }
  return <span className="px-2 py-0.5 rounded text-xs font-medium bg-blue-500/20 text-blue-400">По расписанию</span>
}

// ==================== COMPONENTS ====================

function Card({ title, children, className = '' }: { title: string; children: React.ReactNode; className?: string }) {
  return (
    <div className={`bg-tg-card border border-tg-border rounded-lg p-5 mb-4 ${className}`}>
      <h2 className="text-lg font-semibold mb-4 text-tg-accent">{title}</h2>
      {children}
    </div>
  )
}

function InfoRow({ label, value }: { label: string; value: string | number | null | undefined }) {
  const display = value === null || value === undefined || value === '' ? '—' : String(value)
  return (
    <div className="flex justify-between py-2 border-b border-tg-border/50 last:border-0">
      <span className="text-tg-muted">{label}</span>
      <span className="font-medium">{display}</span>
    </div>
  )
}

function ActionBtn({ label, onClick, variant = 'default', loading, disabled }: {
  label: string; onClick: () => void; variant?: 'default' | 'danger' | 'success' | 'warn'; loading?: boolean; disabled?: boolean
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
      disabled={loading || disabled}
      className={`px-3 py-2 text-sm text-white rounded-lg font-medium transition ${colors[variant]} disabled:opacity-50 disabled:cursor-not-allowed`}
    >
      {loading ? '...' : label}
    </button>
  )
}

// Компонент прогресс-бара
function ProgressBar({ percent, sent, total, failed }: { percent: number; sent: number; total: number; failed: number }) {
  return (
    <div className="w-full">
      <div className="flex justify-between text-sm mb-1">
        <span className="text-tg-muted">Прогресс</span>
        <span className="text-tg-text">{percent}%</span>
      </div>
      <div className="w-full bg-tg-border rounded-full h-2.5">
        <div
          className="bg-tg-accent h-2.5 rounded-full transition-all duration-300"
          style={{ width: `${percent}%` }}
        />
      </div>
      <div className="flex justify-between text-xs mt-1 text-tg-muted">
        <span>Отправлено: {sent}</span>
        <span>Всего: {total}</span>
        {failed > 0 && <span className="text-tg-danger">Ошибок: {failed}</span>}
      </div>
    </div>
  )
}

// ==================== AVAILABLE BUTTONS ====================

const AVAILABLE_BUTTONS = [
  { text: '💬 Начать', callback_data: 'menu:start_chat' },
  { text: '💎 Подписка', callback_data: 'menu:subscription' },
  { text: '🛍 Магазин', callback_data: 'menu:shop' },
  { text: '🏠 Главное меню', callback_data: 'menu:back_to_menu' },
]

const DELAY_OPTIONS = [
  { value: 30, label: 'Через 30 минут' },
  { value: 60, label: 'Через 1 час' },
  { value: 120, label: 'Через 2 часа' },
  { value: 180, label: 'Через 3 часа' },
]

// ==================== MAIN COMPONENT ====================

export default function BroadcastPage() {
  const [broadcasts, setBroadcasts] = useState<BroadcastData[]>([])
  const [activeBroadcasts, setActiveBroadcasts] = useState<BroadcastData[]>([])
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState('')
  const [toast, setToast] = useState('')
  const [showCreateForm, setShowCreateForm] = useState(false)

  // Form state
  const [formType, setFormType] = useState<'new_user' | 'scheduled'>('scheduled')
  const [formName, setFormName] = useState('')
  const [formText, setFormText] = useState('')
  const [formMediaUrl, setFormMediaUrl] = useState('')
  const [formMediaType, setFormMediaType] = useState<'photo' | 'video' | ''>('')
  const [formButtons, setFormButtons] = useState<ButtonData[]>([])
  const [formGiftImages, setFormGiftImages] = useState(0)
  const [formDelayMinutes, setFormDelayMinutes] = useState(30)
  const [formScheduledAt, setFormScheduledAt] = useState('')
  const [uploading, setUploading] = useState(false)

  const showToast = (msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(''), 3000)
  }

  const loadBroadcasts = useCallback(async () => {
    try {
      setLoading(true)
      const res = await fetch(`${API_BASE}/broadcast?limit=50`)
      if (res.ok) {
        setBroadcasts(await res.json())
      }
    } catch (e) {
      console.error('Failed to load broadcasts:', e)
    } finally {
      setLoading(false)
    }
  }, [])

  const loadActiveBroadcasts = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/broadcast/active`)
      if (res.ok) {
        setActiveBroadcasts(await res.json())
      }
    } catch (e) {
      console.error('Failed to load active broadcasts:', e)
    }
  }, [])

  useEffect(() => {
    loadBroadcasts()
    loadActiveBroadcasts()

    // Обновление активных рассылок каждые 5 секунд
    const interval = setInterval(loadActiveBroadcasts, 5000)
    return () => clearInterval(interval)
  }, [loadBroadcasts, loadActiveBroadcasts])

  const resetForm = () => {
    setFormName('')
    setFormText('')
    setFormMediaUrl('')
    setFormMediaType('')
    setFormButtons([])
    setFormGiftImages(0)
    setFormDelayMinutes(30)
    setFormScheduledAt('')
  }

  const handleCreate = async () => {
    if (!formName.trim() || !formText.trim()) {
      showToast('Заполните название и текст')
      return
    }

    if (formType === 'scheduled' && !formScheduledAt) {
      showToast('Укажите дату и время')
      return
    }

    try {
      setActionLoading('create')

      const body: any = {
        name: formName,
        broadcast_type: formType,
        text: formText,
        gift_images: formGiftImages,
      }

      if (formMediaUrl && formMediaType) {
        body.media_url = formMediaUrl
        body.media_type = formMediaType
      }

      if (formButtons.length > 0) {
        body.buttons = formButtons
      }

      if (formType === 'new_user') {
        body.delay_minutes = formDelayMinutes
      } else {
        body.scheduled_at = formScheduledAt
      }

      const res = await fetch(`${API_BASE}/broadcast`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Failed to create')
      }

      showToast('Рассылка создана')
      setShowCreateForm(false)
      resetForm()
      await loadBroadcasts()

    } catch (e: any) {
      showToast(`Ошибка: ${e.message}`)
    } finally {
      setActionLoading('')
    }
  }

  const handleSchedule = async (id: number) => {
    try {
      setActionLoading(`schedule_${id}`)
      const res = await fetch(`${API_BASE}/broadcast/${id}/schedule`, { method: 'POST' })
      if (!res.ok) throw new Error('Failed to schedule')
      showToast('Рассылка запланирована')
      await loadBroadcasts()
      await loadActiveBroadcasts()
    } catch (e: any) {
      showToast(`Ошибка: ${e.message}`)
    } finally {
      setActionLoading('')
    }
  }

  const handleCancel = async (id: number) => {
    if (!confirm('Отменить эту рассылку?')) return
    try {
      setActionLoading(`cancel_${id}`)
      const res = await fetch(`${API_BASE}/broadcast/${id}/cancel`, { method: 'POST' })
      if (!res.ok) throw new Error('Failed to cancel')
      showToast('Рассылка отменена')
      await loadBroadcasts()
      await loadActiveBroadcasts()
    } catch (e: any) {
      showToast(`Ошибка: ${e.message}`)
    } finally {
      setActionLoading('')
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Удалить эту рассылку?')) return
    try {
      setActionLoading(`delete_${id}`)
      const res = await fetch(`${API_BASE}/broadcast/${id}`, { method: 'DELETE' })
      if (!res.ok) throw new Error('Failed to delete')
      showToast('Рассылка удалена')
      await loadBroadcasts()
    } catch (e: any) {
      showToast(`Ошибка: ${e.message}`)
    } finally {
      setActionLoading('')
    }
  }

  const toggleButton = (btn: ButtonData) => {
    const exists = formButtons.find(b => b.callback_data === btn.callback_data)
    if (exists) {
      setFormButtons(formButtons.filter(b => b.callback_data !== btn.callback_data))
    } else {
      setFormButtons([...formButtons, btn])
    }
  }

  return (
    <div className="relative">
      {toast && (
        <div className="fixed top-4 right-4 bg-tg-card border border-tg-accent text-tg-text px-4 py-3 rounded-lg shadow-lg z-50">
          {toast}
        </div>
      )}

      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Сервис рассылки</h1>
        <ActionBtn
          label={showCreateForm ? 'Отмена' : '+ Создать рассылку'}
          onClick={() => {
            setShowCreateForm(!showCreateForm)
            if (!showCreateForm) resetForm()
          }}
          variant={showCreateForm ? 'danger' : 'success'}
        />
      </div>

      {/* Форма создания */}
      {showCreateForm && (
        <Card title="Новая рассылка">
          {/* Тип рассылки */}
          <div className="mb-4">
            <label className="block text-tg-muted mb-2">Тип рассылки</label>
            <div className="flex gap-2">
              <button
                onClick={() => setFormType('scheduled')}
                className={`px-4 py-2 rounded-lg transition ${
                  formType === 'scheduled'
                    ? 'bg-tg-accent text-white'
                    : 'bg-tg-secondary text-tg-muted hover:text-tg-text'
                }`}
              >
                По расписанию
              </button>
              <button
                onClick={() => setFormType('new_user')}
                className={`px-4 py-2 rounded-lg transition ${
                  formType === 'new_user'
                    ? 'bg-purple-500 text-white'
                    : 'bg-tg-secondary text-tg-muted hover:text-tg-text'
                }`}
              >
                Новым пользователям
              </button>
            </div>
          </div>

          {/* Название */}
          <div className="mb-4">
            <label className="block text-tg-muted mb-2">Название (для админки)</label>
            <input
              type="text"
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              placeholder="Например: Новогодняя акция"
              className="w-full px-4 py-2 bg-tg-secondary border border-tg-border rounded-lg text-tg-text focus:outline-none focus:border-tg-accent"
            />
          </div>

          {/* Текст */}
          <div className="mb-4">
            <label className="block text-tg-muted mb-2">Текст рассылки (поддерживает HTML)</label>
            <textarea
              value={formText}
              onChange={(e) => setFormText(e.target.value)}
              placeholder="Привет! У нас для тебя подарок..."
              rows={4}
              className="w-full px-4 py-2 bg-tg-secondary border border-tg-border rounded-lg text-tg-text focus:outline-none focus:border-tg-accent resize-none"
            />
          </div>

          {/* Медиа */}
          <div className="mb-4">
            <label className="block text-tg-muted mb-2">Фото / Видео (опционально)</label>
            <div className="flex items-center gap-4">
              <label className={`flex items-center justify-center px-4 py-3 bg-tg-secondary border border-tg-border border-dashed rounded-lg cursor-pointer hover:border-tg-accent transition ${uploading ? 'opacity-50 cursor-wait' : ''}`}>
                <input
                  type="file"
                  accept="image/*,video/*"
                  className="hidden"
                  disabled={uploading}
                  onChange={async (e) => {
                    const file = e.target.files?.[0]
                    if (!file) return

                    // Определяем тип медиа
                    const isVideo = file.type.startsWith('video/')
                    const mediaType = isVideo ? 'video' : 'photo'

                    try {
                      setUploading(true)
                      const formData = new FormData()
                      formData.append('file', file)

                      const res = await fetch(`${API_BASE}/broadcast/upload`, {
                        method: 'POST',
                        body: formData,
                      })

                      if (!res.ok) {
                        const err = await res.json()
                        throw new Error(err.error || 'Upload failed')
                      }

                      const data = await res.json()
                      setFormMediaUrl(data.url)
                      setFormMediaType(mediaType)
                      showToast('Файл загружен')
                    } catch (err: any) {
                      showToast(`Ошибка загрузки: ${err.message}`)
                    } finally {
                      setUploading(false)
                      e.target.value = ''
                    }
                  }}
                />
                <span className="text-tg-muted">
                  {uploading ? '⏳ Загрузка...' : '📎 Выбрать файл'}
                </span>
              </label>

              {formMediaUrl && (
                <div className="flex items-center gap-2 bg-tg-secondary px-3 py-2 rounded-lg">
                  <span className="text-sm">
                    {formMediaType === 'video' ? '🎬' : '🖼️'} {formMediaType === 'video' ? 'Видео' : 'Фото'}
                  </span>
                  <button
                    type="button"
                    onClick={() => {
                      setFormMediaUrl('')
                      setFormMediaType('')
                    }}
                    className="text-tg-danger hover:text-red-400 transition"
                  >
                    ✕
                  </button>
                </div>
              )}
            </div>

            {formMediaUrl && (
              <div className="mt-2 text-xs text-tg-muted truncate">
                {formMediaUrl}
              </div>
            )}
          </div>

          {/* Кнопки */}
          <div className="mb-4">
            <label className="block text-tg-muted mb-2">Кнопки</label>
            <div className="flex flex-wrap gap-2">
              {AVAILABLE_BUTTONS.map((btn) => {
                const isSelected = formButtons.find(b => b.callback_data === btn.callback_data)
                return (
                  <button
                    key={btn.callback_data}
                    onClick={() => toggleButton(btn)}
                    className={`px-3 py-1.5 rounded-lg text-sm transition ${
                      isSelected
                        ? 'bg-tg-accent text-white'
                        : 'bg-tg-secondary text-tg-muted hover:text-tg-text'
                    }`}
                  >
                    {btn.text}
                  </button>
                )
              })}
            </div>
          </div>

          {/* Начисление изображений */}
          <div className="mb-4">
            <label className="block text-tg-muted mb-2">Начислить изображений (бонус)</label>
            <input
              type="number"
              value={formGiftImages}
              onChange={(e) => setFormGiftImages(Math.max(0, parseInt(e.target.value) || 0))}
              min={0}
              className="w-32 px-4 py-2 bg-tg-secondary border border-tg-border rounded-lg text-tg-text focus:outline-none focus:border-tg-accent"
            />
          </div>

          {/* Для new_user - выбор задержки */}
          {formType === 'new_user' && (
            <div className="mb-4">
              <label className="block text-tg-muted mb-2">Отправить после регистрации</label>
              <select
                value={formDelayMinutes}
                onChange={(e) => setFormDelayMinutes(parseInt(e.target.value))}
                className="w-full px-4 py-2 bg-tg-secondary border border-tg-border rounded-lg text-tg-text focus:outline-none focus:border-tg-accent"
              >
                {DELAY_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
          )}

          {/* Для scheduled - выбор даты */}
          {formType === 'scheduled' && (
            <div className="mb-4">
              <label className="block text-tg-muted mb-2">Дата и время отправки</label>
              <input
                type="datetime-local"
                value={formScheduledAt}
                onChange={(e) => setFormScheduledAt(e.target.value)}
                className="w-full px-4 py-2 bg-tg-secondary border border-tg-border rounded-lg text-tg-text focus:outline-none focus:border-tg-accent"
              />
            </div>
          )}

          {/* Кнопка создания */}
          <div className="flex justify-end gap-2 mt-6">
            <ActionBtn
              label="Создать черновик"
              onClick={handleCreate}
              variant="success"
              loading={actionLoading === 'create'}
            />
          </div>
        </Card>
      )}

      {/* Список рассылок */}
      <Card title="Все рассылки">
        {loading ? (
          <div className="text-center py-8 text-tg-muted">Загрузка...</div>
        ) : broadcasts.length === 0 ? (
          <div className="text-center py-8 text-tg-muted">Рассылок пока нет</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-tg-muted border-b border-tg-border">
                  <th className="text-left py-2 pr-4">Название</th>
                  <th className="text-left py-2 pr-4">Тип</th>
                  <th className="text-left py-2 pr-4">Статус</th>
                  <th className="text-left py-2 pr-4">Получателей</th>
                  <th className="text-left py-2 pr-4">Создана</th>
                  <th className="text-left py-2">Действия</th>
                </tr>
              </thead>
              <tbody>
                {broadcasts.map((b) => (
                  <tr key={b.id} className="border-b border-tg-border/30">
                    <td className="py-3 pr-4">
                      <div className="font-medium">{b.name}</div>
                      <div className="text-tg-muted text-xs mt-1 truncate max-w-xs">{b.text}</div>
                    </td>
                    <td className="py-3 pr-4">{getTypeBadge(b.broadcast_type)}</td>
                    <td className="py-3 pr-4">{getStatusBadge(b.status)}</td>
                    <td className="py-3 pr-4">
                      {b.total_recipients > 0 ? (
                        <span>{b.sent_count}/{b.total_recipients}</span>
                      ) : (
                        <span className="text-tg-muted">—</span>
                      )}
                    </td>
                    <td className="py-3 pr-4 text-tg-muted whitespace-nowrap">
                      {formatDate(b.created_at)}
                    </td>
                    <td className="py-3">
                      <div className="flex gap-2">
                        {b.status === 'draft' && (
                          <>
                            <ActionBtn
                              label="Запустить"
                              onClick={() => handleSchedule(b.id)}
                              variant="success"
                              loading={actionLoading === `schedule_${b.id}`}
                            />
                            <ActionBtn
                              label="Удалить"
                              onClick={() => handleDelete(b.id)}
                              variant="danger"
                              loading={actionLoading === `delete_${b.id}`}
                            />
                          </>
                        )}
                        {(b.status === 'scheduled' || b.status === 'running') && (
                          <ActionBtn
                            label="Отменить"
                            onClick={() => handleCancel(b.id)}
                            variant="danger"
                            loading={actionLoading === `cancel_${b.id}`}
                          />
                        )}
                        {b.status === 'cancelled' && (
                          <ActionBtn
                            label="Удалить"
                            onClick={() => handleDelete(b.id)}
                            variant="danger"
                            loading={actionLoading === `delete_${b.id}`}
                          />
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Мониторинг активных рассылок */}
      <Card title="Мониторинг активных рассылок" className="border-tg-accent">
        {activeBroadcasts.length === 0 ? (
          <div className="text-center py-8 text-tg-muted">
            Нет активных рассылок
          </div>
        ) : (
          <div className="space-y-4">
            {activeBroadcasts.map((b) => (
              <div key={b.id} className="bg-tg-secondary rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <span className="font-medium">{b.name}</span>
                    <span className="ml-2">{getStatusBadge(b.status)}</span>
                    <span className="ml-2">{getTypeBadge(b.broadcast_type)}</span>
                  </div>
                  {b.status === 'running' && (
                    <ActionBtn
                      label="Остановить"
                      onClick={() => handleCancel(b.id)}
                      variant="danger"
                      loading={actionLoading === `cancel_${b.id}`}
                    />
                  )}
                </div>

                {b.status === 'running' && (
                  <ProgressBar
                    percent={b.progress_percent}
                    sent={b.sent_count}
                    total={b.total_recipients}
                    failed={b.failed_count}
                  />
                )}

                {b.status === 'scheduled' && (
                  <div className="text-sm text-tg-muted">
                    {b.broadcast_type === 'new_user' ? (
                      <span>Отправка новым пользователям через {b.delay_minutes} мин после регистрации</span>
                    ) : (
                      <span>Запланирована на {formatDate(b.scheduled_at)}</span>
                    )}
                  </div>
                )}

                {b.gift_images > 0 && (
                  <div className="text-sm text-tg-success mt-2">
                    🎁 Начисление {b.gift_images} изображений
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  )
}
