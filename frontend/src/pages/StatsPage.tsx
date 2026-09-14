import { useState, useEffect, useMemo } from 'react'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'
import { statsApi } from '../api/timer'
import { formatTime } from '../utils'
import type { DayPlan } from '../types'

interface Props {
  onBack: () => void
}

const COLORS = [
  '#8b5cf6', '#6366f1', '#3b82f6', '#06b6d4', '#14b8a6',
  '#22c55e', '#eab308', '#f97316', '#ef4444', '#ec4899',
]
const PROCRASTINATION_COLOR = '#f59e0b'

function formatDateShort(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00')
  return d.toLocaleDateString('ru-RU', { weekday: 'short', day: 'numeric', month: 'short' })
}

function formatDateFull(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00')
  return d.toLocaleDateString('ru-RU', { weekday: 'long', day: 'numeric', month: 'long' })
}

function todayStr(): string {
  return new Date().toISOString().slice(0, 10)
}

function planProductiveTime(plan: DayPlan): number {
  return plan.tasks.reduce((s, t) => s + t.elapsed_seconds, 0)
}

export default function StatsPage({ onBack }: Props) {
  const [plans, setPlans] = useState<DayPlan[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedDate, setSelectedDate] = useState(todayStr())

  useEffect(() => {
    statsApi.getPlans()
      .then(setPlans)
      .finally(() => setLoading(false))
  }, [])

  const plan = useMemo(
    () => plans.find((p) => p.date === selectedDate) ?? null,
    [plans, selectedDate],
  )

  const chartData = useMemo(() => {
    if (!plan) return []
    const taskItems = plan.tasks
      .filter((t) => t.elapsed_seconds > 0)
      .map((t) => ({ name: t.name, value: t.elapsed_seconds, color: '' }))
    taskItems.forEach((item, i) => {
      item.color = COLORS[i % COLORS.length]
    })
    if (plan.procrastination_used > 0) {
      taskItems.push({ name: 'Прокрастинация', value: plan.procrastination_used, color: PROCRASTINATION_COLOR })
    }
    return taskItems
  }, [plan])

  const totalProductive = useMemo(
    () => plan?.tasks.reduce((s, t) => s + t.elapsed_seconds, 0) ?? 0,
    [plan],
  )

  const totalTime = totalProductive + (plan?.procrastination_used ?? 0)

  const sortedPlans = useMemo(
    () => [...plans].sort((a, b) => b.date.localeCompare(a.date)),
    [plans],
  )

  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
        <div className="text-zinc-500">Загрузка...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-white">
      <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800">
        <button onClick={onBack} className="text-sm text-zinc-500 hover:text-zinc-300 transition-colors">
          ← Таймер
        </button>
        <h1 className="text-lg font-bold">Статистика</h1>
        <div className="w-16" />
      </div>

      <div className="max-w-2xl mx-auto">
        {/* Selected day header */}
        <div className="px-4 pt-4 pb-2">
          <h2 className="text-sm text-zinc-400">
            {selectedDate === todayStr() ? 'Сегодня' : formatDateFull(selectedDate)}
          </h2>
        </div>

        {!plan ? (
          <div className="text-center py-12 text-zinc-600">
            Нет данных за этот день
          </div>
        ) : (
          <>
            {chartData.length > 0 ? (
              <div className="px-4 py-4">
                <div className="h-56">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={chartData}
                        cx="50%"
                        cy="50%"
                        innerRadius={55}
                        outerRadius={90}
                        paddingAngle={2}
                        dataKey="value"
                      >
                        {chartData.map((entry, i) => (
                          <Cell key={i} fill={entry.color} stroke="transparent" />
                        ))}
                      </Pie>
                      <Tooltip
                        formatter={(value: number) => formatTime(value)}
                        contentStyle={{ background: '#18181b', border: '1px solid #27272a', borderRadius: '8px', color: '#fff' }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>

                <div className="flex justify-center gap-8 mt-2">
                  <div className="text-center">
                    <p className="text-xs text-zinc-500">Продуктивно</p>
                    <p className="text-lg font-mono font-bold text-violet-400">{formatTime(totalProductive)}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-zinc-500">Прокрастинация</p>
                    <p className="text-lg font-mono font-bold text-amber-400">{formatTime(plan.procrastination_used)}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-zinc-500">Всего</p>
                    <p className="text-lg font-mono font-bold text-zinc-300">{formatTime(totalTime)}</p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-zinc-600">
                Нет записей о времени
              </div>
            )}

            {/* Task breakdown */}
            <div className="px-4 py-4">
              <h2 className="text-sm text-zinc-500 mb-3">Задачи</h2>
              <div className="space-y-2">
                {plan.tasks
                  .filter((t) => t.elapsed_seconds > 0 || t.status === 'active')
                  .sort((a, b) => b.elapsed_seconds - a.elapsed_seconds)
                  .map((task, i) => {
                    const pct = totalTime > 0 ? (task.elapsed_seconds / totalTime) * 100 : 0
                    return (
                      <div key={task.id} className="flex items-center gap-3">
                        <div
                          className="w-3 h-3 rounded-sm shrink-0"
                          style={{ background: COLORS[i % COLORS.length] }}
                        />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-sm truncate">{task.name}</span>
                            <span className="text-xs text-zinc-500 shrink-0 ml-2">
                              {formatTime(task.elapsed_seconds)}
                              {task.allocated_seconds > 0 && (
                                <span className="text-zinc-600"> / {formatTime(task.allocated_seconds)}</span>
                              )}
                            </span>
                          </div>
                          <div className="h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                            <div
                              className="h-full rounded-full transition-all"
                              style={{ width: `${Math.min(pct, 100)}%`, background: COLORS[i % COLORS.length] }}
                            />
                          </div>
                        </div>
                        <span className="text-xs text-zinc-600 w-10 text-right shrink-0">{Math.round(pct)}%</span>
                      </div>
                    )
                  })}

                {plan.procrastination_used > 0 && (
                  <div className="flex items-center gap-3">
                    <div className="w-3 h-3 rounded-sm shrink-0" style={{ background: PROCRASTINATION_COLOR }} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm text-amber-400">Прокрастинация</span>
                        <span className="text-xs text-zinc-500 shrink-0 ml-2">
                          {formatTime(plan.procrastination_used)}
                        </span>
                      </div>
                      <div className="h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${totalTime > 0 ? (plan.procrastination_used / totalTime) * 100 : 0}%`,
                            background: PROCRASTINATION_COLOR,
                          }}
                        />
                      </div>
                    </div>
                    <span className="text-xs text-zinc-600 w-10 text-right shrink-0">
                      {totalTime > 0 ? Math.round((plan.procrastination_used / totalTime) * 100) : 0}%
                    </span>
                  </div>
                )}
              </div>
            </div>
          </>
        )}

        {/* History list */}
        <div className="px-4 py-4 border-t border-zinc-800">
          <h2 className="text-sm text-zinc-500 mb-3">История</h2>
          {sortedPlans.length === 0 ? (
            <p className="text-zinc-600 text-sm">Пока нет записей</p>
          ) : (
            <div className="space-y-1">
              {sortedPlans.map((p) => {
                const productive = planProductiveTime(p)
                const total = productive + p.procrastination_used
                const completedCount = p.tasks.filter((t) => t.status === 'completed').length
                const totalTasks = p.tasks.length
                const isSelected = p.date === selectedDate
                const productivePct = total > 0 ? Math.round((productive / total) * 100) : 0

                return (
                  <button
                    key={p.id}
                    onClick={() => setSelectedDate(p.date)}
                    className={`w-full text-left px-3 py-2.5 rounded-lg transition-colors ${
                      isSelected
                        ? 'bg-violet-600/20 border border-violet-500/30'
                        : 'hover:bg-zinc-900 border border-transparent'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-sm font-medium">
                        {p.date === todayStr() ? 'Сегодня' : formatDateShort(p.date)}
                      </span>
                      <span className="text-xs text-zinc-500">
                        {completedCount}/{totalTasks} задач
                      </span>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="flex-1 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                        <div className="h-full flex">
                          {productive > 0 && (
                            <div
                              className="h-full bg-violet-500"
                              style={{ width: `${productivePct}%` }}
                            />
                          )}
                          {p.procrastination_used > 0 && (
                            <div
                              className="h-full bg-amber-500"
                              style={{ width: `${100 - productivePct}%` }}
                            />
                          )}
                        </div>
                      </div>
                      <span className="text-xs font-mono text-zinc-500 shrink-0 w-12 text-right">
                        {formatTime(total)}
                      </span>
                    </div>
                  </button>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
