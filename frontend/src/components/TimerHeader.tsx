import { formatTime } from '../utils'
import type { Task } from '../types'

interface Props {
  activeTask: (Task & { live_elapsed: number }) | null
  procrastination: number
  procrastinationRunning: boolean
  nextDayBoundary: string | null
}

export default function TimerHeader({ activeTask, procrastination, procrastinationRunning, nextDayBoundary }: Props) {
  const hasDeadline = activeTask ? activeTask.allocated_seconds > 0 : false
  const remaining = activeTask && hasDeadline
    ? activeTask.allocated_seconds - activeTask.live_elapsed
    : null

  const dayRemaining = nextDayBoundary
    ? Math.max(0, Math.floor((new Date(nextDayBoundary).getTime() - Date.now()) / 1000))
    : null

  return (
    <div className="px-4 py-6 border-b border-zinc-800">
      {activeTask ? (
        <div className="text-center">
          <p className="text-zinc-400 text-sm mb-1">{activeTask.name}</p>
          {hasDeadline ? (
            <p className={`text-5xl font-mono font-bold tabular-nums ${remaining !== null && remaining < 0 ? 'text-red-400' : 'text-white'}`}>
              {formatTime(remaining ?? 0)}
            </p>
          ) : (
            <p className="text-5xl font-mono font-bold tabular-nums text-white">
              {formatTime(activeTask.live_elapsed)}
            </p>
          )}
        </div>
      ) : (
        <div className="text-center">
          <p className="text-zinc-500 text-sm mb-1">Нет активной задачи</p>
          <p className="text-5xl font-mono font-bold tabular-nums text-zinc-600">
            --:--
          </p>
        </div>
      )}
      <div className="mt-4 flex justify-center gap-3 flex-wrap">
        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm ${procrastinationRunning ? 'bg-amber-900/30 text-amber-400' : 'bg-zinc-900 text-zinc-500'}`}>
          <span className={`w-2 h-2 rounded-full ${procrastinationRunning ? 'bg-amber-400 animate-pulse' : 'bg-zinc-700'}`} />
          Прокрастинация: {formatTime(procrastination)}
        </div>
        {dayRemaining !== null && (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full text-sm bg-zinc-900 text-zinc-500">
            До конца дня: {formatTime(dayRemaining)}
          </div>
        )}
      </div>
    </div>
  )
}
