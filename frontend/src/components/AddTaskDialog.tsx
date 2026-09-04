import { useState } from 'react'

interface Props {
  open: boolean
  onClose: () => void
  onAdd: (data: { name: string; allocated_seconds: number; priority: string }) => void
}

export default function AddTaskDialog({ open, onClose, onAdd }: Props) {
  const [name, setName] = useState('')
  const [hours, setHours] = useState(0)
  const [minutes, setMinutes] = useState(30)
  const [priority, setPriority] = useState('normal')

  if (!open) return null

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const allocated_seconds = hours * 3600 + minutes * 60
    if (allocated_seconds <= 0 || !name.trim()) return
    onAdd({ name: name.trim(), allocated_seconds, priority })
    setName('')
    setHours(0)
    setMinutes(30)
    setPriority('normal')
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 w-full max-w-md" onClick={(e) => e.stopPropagation()}>
        <h2 className="text-lg font-semibold text-white mb-4">Add Task</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="text"
            placeholder="Task name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            autoFocus
            className="w-full px-4 py-2.5 bg-zinc-800 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:border-violet-500"
          />
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="block text-xs text-zinc-500 mb-1">Hours</label>
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
              <label className="block text-xs text-zinc-500 mb-1">Minutes</label>
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
          <div>
            <label className="block text-xs text-zinc-500 mb-1">Priority</label>
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
                  {p === 'high' ? 'High' : p === 'low' ? 'Low' : 'Normal'}
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
              Cancel
            </button>
            <button
              type="submit"
              className="flex-1 py-2.5 bg-violet-600 text-white rounded-lg hover:bg-violet-500 transition-colors"
            >
              Add
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
