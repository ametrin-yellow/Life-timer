import { formatTime, priorityLabel } from '../utils'
import type { Task } from '../types'

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
            <span className="shrink-0 text-xs px-1.5 py-0.5 rounded bg-blue-900/30 text-blue-400">
              ↻
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

      <div className="shrink-0 flex gap-1">
        {isDone ? (
          <>
            <button
              onClick={onReopen}
              disabled={disabled}
              className="px-2 py-1 text-xs bg-violet-900/30 text-violet-400 rounded hover:bg-violet-900/50 transition-colors disabled:opacity-50"
              title="Вернуть в список"
            >
              Вернуть
            </button>
            <button
              onClick={onDelete}
              disabled={disabled}
              className="px-2 py-1 text-xs bg-zinc-800 text-zinc-400 rounded hover:bg-zinc-700 transition-colors disabled:opacity-50"
              title="Удалить"
            >
              ×
            </button>
          </>
        ) : (
          <>
            <button
              onClick={onEdit}
              disabled={disabled}
              className="px-2 py-1 text-xs bg-zinc-800 text-zinc-400 rounded hover:bg-zinc-700 transition-colors disabled:opacity-50"
              title="Редактировать"
            >
              ✎
            </button>
            <button
              onClick={onComplete}
              disabled={disabled}
              className="px-2 py-1 text-xs bg-emerald-900/30 text-emerald-400 rounded hover:bg-emerald-900/50 transition-colors disabled:opacity-50"
              title="Завершить"
            >
              Готово
            </button>
            <button
              onClick={onSkip}
              disabled={disabled}
              className="px-2 py-1 text-xs bg-zinc-800 text-zinc-400 rounded hover:bg-zinc-700 transition-colors disabled:opacity-50"
              title="Пропустить"
            >
              Проп.
            </button>
            <button
              onClick={onDelete}
              disabled={disabled}
              className="px-2 py-1 text-xs bg-zinc-800 text-zinc-400 rounded hover:bg-zinc-700 transition-colors disabled:opacity-50"
              title="Удалить"
            >
              ×
            </button>
          </>
        )}
      </div>
    </div>
  )
}
