import { useState, useCallback, useRef } from 'react'
import { useTimer } from '../hooks/useTimer'
import { useAuth } from '../hooks/useAuth'
import { timerApi, planApi } from '../api/timer'
import TimerHeader from '../components/TimerHeader'
import TaskRow from '../components/TaskRow'
import AddTaskDialog from '../components/AddTaskDialog'
import EditTaskDialog from '../components/EditTaskDialog'
import SettingsDialog from '../components/SettingsDialog'
import type { Task } from '../types'

interface Props {
  onStats: () => void
}

export default function TimerPage({ onStats }: Props) {
  const { logout } = useAuth()
  const { state, loading, tasks, liveProcrastination, activeTask, refresh } = useTimer()
  const [busy, setBusy] = useState(false)
  const [showAdd, setShowAdd] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [editingTask, setEditingTask] = useState<Task | null>(null)
  const [dragOverId, setDragOverId] = useState<string | null>(null)
  const dragIdRef = useRef<string | null>(null)

  const wrap = useCallback(async (fn: () => Promise<unknown>) => {
    setBusy(true)
    try {
      await fn()
      await refresh()
    } finally {
      setBusy(false)
    }
  }, [refresh])

  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
        <div className="text-zinc-500">Загрузка...</div>
      </div>
    )
  }

  const planDate = state?.date ? new Date(state.date + 'T00:00:00') : new Date()
  const planIsoDay = planDate.getDay() === 0 ? 7 : planDate.getDay()

  function matchesSchedule(t: { schedule_days: string | null }) {
    if (!t.schedule_days) return true
    return t.schedule_days.split(',').map(Number).includes(planIsoDay)
  }

  const sorted = [...tasks]
    .filter(matchesSchedule)
    .sort((a, b) => a.position - b.position || a.created_at.localeCompare(b.created_at))
  const pending = sorted.filter((t) => t.status === 'pending' || t.status === 'active')
  const done = sorted.filter((t) => t.status === 'completed' || t.status === 'skipped')

  function handleDragStart(taskId: string) {
    dragIdRef.current = taskId
  }

  function handleDragOver(e: React.DragEvent, taskId: string) {
    e.preventDefault()
    if (dragIdRef.current && dragIdRef.current !== taskId) {
      setDragOverId(taskId)
    }
  }

  function handleDragEnd() {
    if (!state || !dragIdRef.current || !dragOverId) {
      dragIdRef.current = null
      setDragOverId(null)
      return
    }

    const fromId = dragIdRef.current
    const toId = dragOverId
    dragIdRef.current = null
    setDragOverId(null)

    const ids = pending.map((t) => t.id)
    const fromIdx = ids.indexOf(fromId)
    const toIdx = ids.indexOf(toId)
    if (fromIdx === -1 || toIdx === -1 || fromIdx === toIdx) return

    ids.splice(fromIdx, 1)
    ids.splice(toIdx, 0, fromId)

    const allIds = [...ids, ...done.map((t) => t.id)]
    wrap(() => planApi.reorderTasks(state.plan_id, allIds))
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-white">
      <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800">
        <h1 className="text-lg font-bold">Life Timer</h1>
        <div className="flex items-center gap-4">
          <button
            onClick={onStats}
            className="text-sm text-zinc-500 hover:text-zinc-300 transition-colors"
          >
            Статистика
          </button>
          <button
            onClick={() => setShowPassword(true)}
            className="text-sm text-zinc-500 hover:text-zinc-300 transition-colors"
          >
            Настройки
          </button>
          <button
            onClick={logout}
            className="text-sm text-zinc-500 hover:text-zinc-300 transition-colors"
          >
            Выйти
          </button>
        </div>
      </div>

      <TimerHeader
        activeTask={activeTask}
        procrastination={liveProcrastination}
        procrastinationRunning={state?.procrastination_running ?? false}
      />

      <div className="max-w-2xl mx-auto">
        <div className="px-4 py-3">
          <button
            onClick={() => setShowAdd(true)}
            className="w-full py-2.5 border border-dashed border-zinc-700 text-zinc-500 rounded-lg hover:border-zinc-500 hover:text-zinc-300 transition-colors"
          >
            + Добавить задачу
          </button>
        </div>

        {pending.map((task) => (
          <TaskRow
            key={task.id}
            task={task}
            isActive={task.id === state?.active_task_id}
            onStart={() => wrap(() => timerApi.startTask(task.id))}
            onPause={() => wrap(() => timerApi.pauseTask(task.id))}
            onComplete={() => wrap(() => timerApi.completeTask(task.id))}
            onSkip={() => wrap(() => timerApi.skipTask(task.id))}
            onReopen={() => wrap(() => timerApi.reopenTask(task.id))}
            onDelete={() => state && wrap(() => planApi.deleteTask(state.plan_id, task.id))}
            onEdit={() => setEditingTask(task)}
            disabled={busy}
            draggable
            onDragStart={(e) => {
              e.dataTransfer.effectAllowed = 'move'
              handleDragStart(task.id)
            }}
            onDragOver={(e) => handleDragOver(e, task.id)}
            onDragEnd={handleDragEnd}
            dragOver={dragOverId === task.id}
          />
        ))}

        {done.length > 0 && (
          <>
            <div className="px-4 py-2 mt-2">
              <span className="text-xs text-zinc-600 uppercase tracking-wider">Завершённые</span>
            </div>
            {done.map((task) => (
              <TaskRow
                key={task.id}
                task={task}
                isActive={false}
                onStart={() => {}}
                onPause={() => {}}
                onComplete={() => {}}
                onSkip={() => {}}
                onReopen={() => wrap(() => timerApi.reopenTask(task.id))}
                onDelete={() => state && wrap(() => planApi.deleteTask(state.plan_id, task.id))}
                onEdit={() => {}}
                disabled={busy}
              />
            ))}
          </>
        )}

        {tasks.length === 0 && (
          <div className="text-center py-12 text-zinc-600">
            Задач пока нет. Добавьте первую, чтобы начать день.
          </div>
        )}
      </div>

      <SettingsDialog
        open={showPassword}
        onClose={() => setShowPassword(false)}
      />

      <AddTaskDialog
        open={showAdd}
        onClose={() => setShowAdd(false)}
        onAdd={(data) => {
          if (!state) return
          wrap(() => planApi.createTask(state.plan_id, data))
        }}
      />

      <EditTaskDialog
        open={editingTask !== null}
        task={editingTask}
        onClose={() => setEditingTask(null)}
        onSave={(data) => {
          if (!state || !editingTask) return
          wrap(() => planApi.updateTask(state.plan_id, editingTask.id, data))
        }}
      />
    </div>
  )
}
