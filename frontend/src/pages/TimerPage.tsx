import { useState, useCallback } from 'react'
import { useTimer } from '../hooks/useTimer'
import { useAuth } from '../hooks/useAuth'
import { timerApi, planApi } from '../api/timer'
import TimerHeader from '../components/TimerHeader'
import TaskRow from '../components/TaskRow'
import AddTaskDialog from '../components/AddTaskDialog'

export default function TimerPage() {
  const { logout } = useAuth()
  const { state, loading, tasks, liveProcrastination, activeTask, refresh } = useTimer()
  const [busy, setBusy] = useState(false)
  const [showAdd, setShowAdd] = useState(false)

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
        <div className="text-zinc-500">Loading...</div>
      </div>
    )
  }

  const sorted = [...tasks].sort((a, b) =>
    a.position - b.position || a.created_at.localeCompare(b.created_at)
  )
  const pending = sorted.filter((t) => t.status === 'pending' || t.status === 'active')
  const done = sorted.filter((t) => t.status === 'completed' || t.status === 'skipped')

  return (
    <div className="min-h-screen bg-zinc-950 text-white">
      {/* Top bar */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800">
        <h1 className="text-lg font-bold">Life Timer</h1>
        <button
          onClick={logout}
          className="text-sm text-zinc-500 hover:text-zinc-300 transition-colors"
        >
          Log out
        </button>
      </div>

      <TimerHeader
        activeTask={activeTask}
        procrastination={liveProcrastination}
        procrastinationRunning={state?.procrastination_running ?? false}
      />

      {/* Task list */}
      <div className="max-w-2xl mx-auto">
        {/* Add task button */}
        <div className="px-4 py-3">
          <button
            onClick={() => setShowAdd(true)}
            className="w-full py-2.5 border border-dashed border-zinc-700 text-zinc-500 rounded-lg hover:border-zinc-500 hover:text-zinc-300 transition-colors"
          >
            + Add task
          </button>
        </div>

        {/* Active / pending tasks */}
        {pending.map((task) => (
          <TaskRow
            key={task.id}
            task={task}
            isActive={task.id === state?.active_task_id}
            onStart={() => wrap(() => timerApi.startTask(task.id))}
            onPause={() => wrap(() => timerApi.pauseTask(task.id))}
            onComplete={() => wrap(() => timerApi.completeTask(task.id))}
            onSkip={() => wrap(() => timerApi.skipTask(task.id))}
            onDelete={() => state && wrap(() => planApi.deleteTask(state.plan_id, task.id))}
            disabled={busy}
          />
        ))}

        {/* Completed / skipped tasks */}
        {done.length > 0 && (
          <>
            <div className="px-4 py-2 mt-2">
              <span className="text-xs text-zinc-600 uppercase tracking-wider">Completed</span>
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
                onDelete={() => state && wrap(() => planApi.deleteTask(state.plan_id, task.id))}
                disabled={busy}
              />
            ))}
          </>
        )}

        {tasks.length === 0 && (
          <div className="text-center py-12 text-zinc-600">
            No tasks yet. Add one to start tracking your day.
          </div>
        )}
      </div>

      <AddTaskDialog
        open={showAdd}
        onClose={() => setShowAdd(false)}
        onAdd={(data) => {
          if (!state) return
          wrap(() => planApi.createTask(state.plan_id, data))
        }}
      />
    </div>
  )
}
