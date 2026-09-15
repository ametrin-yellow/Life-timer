import { useState, useEffect, useCallback } from 'react'
import { allTasksApi, planApi, statsApi } from '../api/timer'
import AddTaskDialog from '../components/AddTaskDialog'
import EditTaskDialog from '../components/EditTaskDialog'
import type { Task } from '../types'

const SHORT_DAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']

function formatSchedule(schedule: string): string {
  const days = schedule.split(',').map(Number).sort()
  if (days.length === 5 && days.join(',') === '1,2,3,4,5') return 'Пн–Пт'
  if (days.length === 2 && days.join(',') === '6,7') return 'Сб–Вс'
  return days.map(d => SHORT_DAYS[d - 1]).join(', ')
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00')
  return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })
}

function formatAlloc(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  if (h > 0) return `${h}ч${m > 0 ? ` ${m}м` : ''}`
  return `${m}м`
}

interface Props {
  onBack: () => void
}

export default function AllTasksPage({ onBack }: Props) {
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [planId, setPlanId] = useState<number | null>(null)
  const [showAdd, setShowAdd] = useState(false)
  const [editingTask, setEditingTask] = useState<Task | null>(null)
  const [menuOpen, setMenuOpen] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const refresh = useCallback(async () => {
    const [t, plan] = await Promise.all([
      allTasksApi.getAll(),
      statsApi.getPlans().then(plans => plans[0]),
    ])
    setTasks(t)
    if (plan) setPlanId(plan.id)
  }, [])

  useEffect(() => {
    refresh().finally(() => setLoading(false))
  }, [refresh])

  async function handleDelete(task: Task) {
    setBusy(true)
    try {
      await planApi.deleteTask(task.plan_id, task.id)
      await refresh()
    } finally {
      setBusy(false)
      setMenuOpen(null)
    }
  }

  const recurring = tasks.filter(t => t.is_recurring)
  const scheduled = tasks.filter(t => !t.is_recurring && t.scheduled_date)

  return (
    <div className="min-h-screen bg-zinc-950 text-white">
      <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800">
        <button onClick={onBack} className="text-sm text-zinc-500 hover:text-zinc-300 transition-colors">
          ← Назад
        </button>
        <h1 className="text-lg font-bold">Все задачи</h1>
        <div className="w-16" />
      </div>

      <div className="max-w-2xl mx-auto">
        <div className="px-4 py-3">
          <button
            onClick={() => setShowAdd(true)}
            className="w-full py-2.5 border border-dashed border-zinc-700 text-zinc-500 rounded-lg hover:border-zinc-500 hover:text-zinc-300 transition-colors"
          >
            + Добавить задачу
          </button>
        </div>

        {loading ? (
          <div className="text-center py-12 text-zinc-600">Загрузка...</div>
        ) : (
          <>
            {recurring.length > 0 && (
              <div>
                <div className="px-4 py-2">
                  <span className="text-xs text-zinc-500 uppercase tracking-wider">Регулярные</span>
                </div>
                {recurring.map(task => (
                  <div key={task.id} className="flex items-center gap-3 px-4 py-3 border-b border-zinc-800/50">
                    <div className="flex-1 min-w-0 cursor-pointer" onClick={() => setEditingTask(task)}>
                      <div className="flex items-center gap-2">
                        <span className="flex-1 min-w-0 text-sm text-white truncate">{task.name}</span>
                        <span className="shrink-0 text-xs px-1.5 py-0.5 rounded bg-blue-900/30 text-blue-400">
                          ↻ {task.schedule_days ? formatSchedule(task.schedule_days) : 'Ежедневно'}
                        </span>
                        {task.priority !== 'normal' && (
                          <span className={`shrink-0 text-xs px-1.5 py-0.5 rounded ${task.priority === 'high' ? 'bg-red-900/30 text-red-400' : 'bg-zinc-800 text-zinc-500'}`}>
                            {task.priority === 'high' ? 'Высокий' : 'Низкий'}
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-zinc-600 mt-0.5">
                        {task.allocated_seconds > 0 ? formatAlloc(task.allocated_seconds) : 'Без лимита'}
                      </div>
                    </div>
                    <div className="shrink-0 relative">
                      <button
                        onClick={() => setMenuOpen(menuOpen === task.id ? null : task.id)}
                        className="w-8 h-8 flex items-center justify-center rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition-colors"
                      >
                        ⋮
                      </button>
                      {menuOpen === task.id && (
                        <div className="absolute right-0 top-full mt-1 z-50 bg-zinc-900 border border-zinc-700 rounded-lg shadow-xl py-1 min-w-[140px]">
                          <button
                            onClick={() => { setMenuOpen(null); setEditingTask(task) }}
                            className="w-full text-left px-3 py-2 text-sm text-zinc-300 hover:bg-zinc-800 transition-colors"
                          >
                            Редактировать
                          </button>
                          <button
                            onClick={() => handleDelete(task)}
                            disabled={busy}
                            className="w-full text-left px-3 py-2 text-sm text-red-400 hover:bg-zinc-800 transition-colors disabled:opacity-50"
                          >
                            Удалить
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {scheduled.length > 0 && (
              <div>
                <div className="px-4 py-2 mt-2">
                  <span className="text-xs text-zinc-500 uppercase tracking-wider">Запланированные</span>
                </div>
                {scheduled.map(task => (
                  <div key={task.id} className="flex items-center gap-3 px-4 py-3 border-b border-zinc-800/50">
                    <div className="flex-1 min-w-0 cursor-pointer" onClick={() => setEditingTask(task)}>
                      <div className="flex items-center gap-2">
                        <span className="flex-1 min-w-0 text-sm text-white truncate">{task.name}</span>
                        <span className="shrink-0 text-xs px-1.5 py-0.5 rounded bg-violet-900/30 text-violet-400">
                          {formatDate(task.scheduled_date!)}
                        </span>
                      </div>
                      <div className="text-xs text-zinc-600 mt-0.5">
                        {task.allocated_seconds > 0 ? formatAlloc(task.allocated_seconds) : 'Без лимита'}
                      </div>
                    </div>
                    <div className="shrink-0 relative">
                      <button
                        onClick={() => setMenuOpen(menuOpen === task.id ? null : task.id)}
                        className="w-8 h-8 flex items-center justify-center rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition-colors"
                      >
                        ⋮
                      </button>
                      {menuOpen === task.id && (
                        <div className="absolute right-0 top-full mt-1 z-50 bg-zinc-900 border border-zinc-700 rounded-lg shadow-xl py-1 min-w-[140px]">
                          <button
                            onClick={() => { setMenuOpen(null); setEditingTask(task) }}
                            className="w-full text-left px-3 py-2 text-sm text-zinc-300 hover:bg-zinc-800 transition-colors"
                          >
                            Редактировать
                          </button>
                          <button
                            onClick={() => handleDelete(task)}
                            disabled={busy}
                            className="w-full text-left px-3 py-2 text-sm text-red-400 hover:bg-zinc-800 transition-colors disabled:opacity-50"
                          >
                            Удалить
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {recurring.length === 0 && scheduled.length === 0 && (
              <div className="text-center py-12 text-zinc-600">
                Нет регулярных или запланированных задач
              </div>
            )}
          </>
        )}
      </div>

      <AddTaskDialog
        open={showAdd}
        onClose={() => setShowAdd(false)}
        onAdd={async (data) => {
          if (!planId) return
          setBusy(true)
          try {
            await planApi.createTask(planId, data)
            await refresh()
          } finally {
            setBusy(false)
          }
        }}
      />

      <EditTaskDialog
        open={editingTask !== null}
        task={editingTask}
        onClose={() => setEditingTask(null)}
        onSave={async (data) => {
          if (!editingTask) return
          setBusy(true)
          try {
            await planApi.updateTask(editingTask.plan_id, editingTask.id, data)
            await refresh()
          } finally {
            setBusy(false)
          }
        }}
      />
    </div>
  )
}
