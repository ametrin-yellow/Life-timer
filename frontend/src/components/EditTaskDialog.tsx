import { useState, useEffect } from 'react'
import type { Task } from '../types'

interface Props {
  open: boolean
  task: Task | null
  onClose: () => void
  onSave: (data: { name: string; allocated_seconds: number; priority: string; is_recurring: boolean }) => void
}

export default function EditTaskDialog({ open, task, onClose, onSave }: Props) {
  const [name, setName] = useState('')
  const [hours, setHours] = useState(0)
  const [minutes, setMinutes] = useState(0)
  const [priority, setPriority] = useState('normal')
  const [noDeadline, setNoDeadline] = useState(false)
  const [isRecurring, setIsRecurring] = useState(false)

  useEffect(() => {
    if (task) {
      setName(task.name)
      setNoDeadline(task.allocated_seconds === 0)
      setIsRecurring(task.is_recurring)
      const h = Math.floor(task.allocated_seconds / 3600)
      const m = Math.floor((task.allocated_seconds % 3600) / 60)
      setHours(h)
      setMinutes(m)
      setPriority(task.priority)
    }
  }, [task])

  if (!open || !task) return null

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim()) return
    const allocated_seconds = noDeadline ? 0 : hours * 3600 + minutes * 60
    if (!noDeadline && allocated_seconds <= 0) return
    onSave({ name: name.trim(), allocated_seconds, priority, is_recurring: isRecurring })
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 w-full max-w-md" onClick={(e) => e.stopPropagation()}>
        <h2 className="text-lg font-semibold text-white mb-4">Редактировать задачу</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="text"
            placeholder="Название задачи"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            autoFocus
            className="w-full px-4 py-2.5 bg-zinc-800 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:border-violet-500"
          />
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={noDeadline}
              onChange={(e) => setNoDeadline(e.target.checked)}
              className="w-4 h-4 rounded border-zinc-600 bg-zinc-800 text-violet-500 focus:ring-violet-500 focus:ring-offset-0"
            />
            <span className="text-sm text-zinc-400">Без дедлайна (просто таймер)</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={isRecurring}
              onChange={(e) => setIsRecurring(e.target.checked)}
              className="w-4 h-4 rounded border-zinc-600 bg-zinc-800 text-violet-500 focus:ring-violet-500 focus:ring-offset-0"
            />
            <span className="text-sm text-zinc-400">Регулярная (переносится в новый день)</span>
          </label>
          {!noDeadline && (
            <div className="flex gap-3">
              <div className="flex-1">
                <label className="block text-xs text-zinc-500 mb-1">Часы</label>
                <input
                  type="number"
                  min={0}
                  max={23}
                  value={hours}
                  onChange={(e) => setHours(Number(e.target.value))}
                  className="w-full px-3 py-2.5 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none focus:border-violet-500"
                />
              </div>
              <div className="flex-1">
                <label className="block text-xs text-zinc-500 mb-1">Минуты</label>
                <input
                  type="number"
                  min={0}
                  max={59}
                  value={minutes}
                  onChange={(e) => setMinutes(Number(e.target.value))}
                  className="w-full px-3 py-2.5 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none focus:border-violet-500"
                />
              </div>
            </div>
          )}
          <div>
            <label className="block text-xs text-zinc-500 mb-1">Приоритет</label>
            <div className="flex gap-2">
              {(['low', 'normal', 'high'] as const).map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setPriority(p)}
                  className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
                    priority === p
                      ? p === 'high' ? 'bg-red-900/40 text-red-400 border border-red-800'
                        : p === 'low' ? 'bg-zinc-700 text-zinc-300 border border-zinc-600'
                        : 'bg-violet-900/40 text-violet-400 border border-violet-800'
                      : 'bg-zinc-800 text-zinc-500 border border-zinc-700'
                  }`}
                >
                  {p === 'high' ? 'Высокий' : p === 'low' ? 'Низкий' : 'Обычный'}
                </button>
              ))}
            </div>
          </div>
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2.5 bg-zinc-800 text-zinc-400 rounded-lg hover:bg-zinc-700 transition-colors"
            >
              Отмена
            </button>
            <button
              type="submit"
              className="flex-1 py-2.5 bg-violet-600 text-white rounded-lg hover:bg-violet-500 transition-colors"
            >
              Сохранить
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
