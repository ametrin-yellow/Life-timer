import { useState, useRef, useEffect } from 'react'
import { formatTime, priorityLabel } from '../utils'
import type { Task } from '../types'

const SHORT_DAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']

function formatScheduleShort(schedule: string): string {
  const days = schedule.split(',').map(Number).sort()
  if (days.length === 5 && days.join(',') === '1,2,3,4,5') return 'Пн-Пт'
  if (days.length === 2 && days.join(',') === '6,7') return 'Сб-Вс'
  return days.map(d => SHORT_DAYS[d - 1]).join(',')
}

function formatSchedule(schedule: string): string {
  const days = schedule.split(',').map(Number).sort()
  return days.map(d => SHORT_DAYS[d - 1]).join(', ')
}

interface Props {
  task: Task & { live_elapsed: number }
  isActive: boolean
  onStart: () => void
  onPause: () => void
  onComplete: () => void
  onSkip: () => void
  onReopen: () => void
  onDelete: () => void
  onEdit: () => void
  disabled: boolean
  draggable?: boolean
  onDragStart?: (e: React.DragEvent) => void
  onDragOver?: (e: React.DragEvent) => void
  onDragEnd?: () => void
  dragOver?: boolean
}

export default function TaskRow({ task, isActive, onStart, onPause, onComplete, onSkip, onReopen, onDelete, onEdit, disabled, draggable, onDragStart, onDragOver, onDragEnd, dragOver }: Props) {
  const isDone = task.status === 'completed' || task.status === 'skipped'
  const hasDeadline = task.allocated_seconds > 0
  const remaining = hasDeadline ? task.allocated_seconds - task.live_elapsed : 0
  const progress = hasDeadline ? Math.min(100, (task.live_elapsed / task.allocated_seconds) * 100) : 0
  const overrun = hasDeadline && remaining < 0

  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!menuOpen) return
    function handleClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [menuOpen])

  function menuAction(fn: () => void) {
    setMenuOpen(false)
    fn()
  }

  return (
    <div
      className={`flex items-center gap-3 px-4 py-3 border-b border-zinc-800/50 transition-colors ${isDone ? 'opacity-50' : 'hover:bg-zinc-900/50'} ${dragOver ? 'border-t-2 border-t-violet-500' : ''}`}
      draggable={draggable}
      onDragStart={onDragStart}
      onDragOver={onDragOver}
      onDragEnd={onDragEnd}
    >
      {draggable && (
        <div className="shrink-0 cursor-grab active:cursor-grabbing text-zinc-600 hover:text-zinc-400 select-none" title="Перетащить">
          ⠿
        </div>
      )}

      <div className="shrink-0">
        {isDone ? (
          <span className="w-9 h-9 flex items-center justify-center text-zinc-600">
            {task.status === 'completed' ? '✓' : '—'}
          </span>
        ) : isActive ? (
          <button
            onClick={onPause}
            disabled={disabled}
            className="w-9 h-9 flex items-center justify-center rounded-full bg-violet-600 hover:bg-violet-500 text-white transition-colors disabled:opacity-50"
            title="Пауза"
          >
            ❚❚
          </button>
        ) : (
          <button
            onClick={onStart}
            disabled={disabled}
            className="w-9 h-9 flex items-center justify-center rounded-full bg-zinc-800 hover:bg-zinc-700 text-white transition-colors disabled:opacity-50"
            title="Старт"
          >
            ▶
          </button>
        )}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className={`flex-1 min-w-0 text-sm truncate ${isDone ? 'line-through text-zinc-500' : 'text-white'}`}>
            {task.name}
          </span>
          {task.is_recurring && (
            <span className="shrink-0 text-xs px-1.5 py-0.5 rounded bg-blue-900/30 text-blue-400" title={task.schedule_days ? formatSchedule(task.schedule_days) : 'Каждый день'}>
              ↻{task.schedule_days ? ` ${formatScheduleShort(task.schedule_days)}` : ''}
            </span>
          )}
          {task.priority !== 'normal' && (
            <span className={`shrink-0 text-xs px-1.5 py-0.5 rounded ${task.priority === 'high' ? 'bg-red-900/30 text-red-400' : 'bg-zinc-800 text-zinc-500'}`}>
              {priorityLabel(task.priority)}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1 mt-0.5">
          <span className={`font-mono text-xs tabular-nums ${overrun ? 'text-red-400' : 'text-zinc-500'}`}>
            {formatTime(task.live_elapsed)}
            {hasDeadline && (
              <span className="text-zinc-600"> / {formatTime(task.allocated_seconds)}</span>
            )}
          </span>
        </div>
        {!isDone && hasDeadline && (
          <div className="mt-1 h-1 bg-zinc-800 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${overrun ? 'bg-red-500' : isActive ? 'bg-violet-500' : 'bg-zinc-600'}`}
              style={{ width: `${Math.min(progress, 100)}%` }}
            />
          </div>
        )}
      </div>

      <div className="shrink-0 relative" ref={menuRef}>
        <button
          onClick={() => setMenuOpen(!menuOpen)}
          className="w-8 h-8 flex items-center justify-center rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition-colors"
        >
          ⋮
        </button>
        {menuOpen && (
          <div className="absolute right-0 top-full mt-1 z-50 bg-zinc-900 border border-zinc-700 rounded-lg shadow-xl py-1 min-w-[140px]">
            {isDone ? (
              <>
                <button
                  onClick={() => menuAction(onReopen)}
                  disabled={disabled}
                  className="w-full text-left px-3 py-2 text-sm text-violet-400 hover:bg-zinc-800 transition-colors disabled:opacity-50"
                >
                  Вернуть
                </button>
                <button
                  onClick={() => menuAction(onDelete)}
                  disabled={disabled}
                  className="w-full text-left px-3 py-2 text-sm text-red-400 hover:bg-zinc-800 transition-colors disabled:opacity-50"
                >
                  Удалить
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={() => menuAction(onEdit)}
                  disabled={disabled}
                  className="w-full text-left px-3 py-2 text-sm text-zinc-300 hover:bg-zinc-800 transition-colors disabled:opacity-50"
                >
                  Редактировать
                </button>
                <button
                  onClick={() => menuAction(onComplete)}
                  disabled={disabled}
                  className="w-full text-left px-3 py-2 text-sm text-emerald-400 hover:bg-zinc-800 transition-colors disabled:opacity-50"
                >
                  Готово
                </button>
                <button
                  onClick={() => menuAction(onSkip)}
                  disabled={disabled}
                  className="w-full text-left px-3 py-2 text-sm text-zinc-400 hover:bg-zinc-800 transition-colors disabled:opacity-50"
                >
                  Пропустить
                </button>
                <button
                  onClick={() => menuAction(onDelete)}
                  disabled={disabled}
                  className="w-full text-left px-3 py-2 text-sm text-red-400 hover:bg-zinc-800 transition-colors disabled:opacity-50"
                >
                  Удалить
                </button>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
