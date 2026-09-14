import { useState } from 'react'
import { changePassword } from '../api/auth'

interface Props {
  open: boolean
  onClose: () => void
}

export default function ChangePasswordDialog({ open, onClose }: Props) {
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(false)

  if (!open) return null

  function reset() {
    setCurrent('')
    setNext('')
    setConfirm('')
    setError('')
    setDone(false)
  }

  function handleClose() {
    reset()
    onClose()
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')

    if (next.length < 6) {
      setError('Минимум 6 символов')
      return
    }
    if (next !== confirm) {
      setError('Пароли не совпадают')
      return
    }

    setBusy(true)
    try {
      await changePassword(current, next)
      setDone(true)
    } catch {
      setError('Неверный текущий пароль')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={handleClose}>
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 w-full max-w-md" onClick={(e) => e.stopPropagation()}>
        <h2 className="text-lg font-semibold text-white mb-4">Смена пароля</h2>

        {done ? (
          <div>
            <p className="text-green-400 mb-4">Пароль изменён</p>
            <button
              onClick={handleClose}
              className="w-full py-2.5 bg-zinc-800 text-zinc-400 rounded-lg hover:bg-zinc-700 transition-colors"
            >
              Закрыть
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <input
              type="password"
              placeholder="Текущий пароль"
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
              required
              autoFocus
              className="w-full px-4 py-2.5 bg-zinc-800 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:border-violet-500"
            />
            <input
              type="password"
              placeholder="Новый пароль"
              value={next}
              onChange={(e) => setNext(e.target.value)}
              required
              className="w-full px-4 py-2.5 bg-zinc-800 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:border-violet-500"
            />
            <input
              type="password"
              placeholder="Повторите новый пароль"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              required
              className="w-full px-4 py-2.5 bg-zinc-800 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:border-violet-500"
            />
            {error && <p className="text-red-400 text-sm">{error}</p>}
            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={handleClose}
                className="flex-1 py-2.5 bg-zinc-800 text-zinc-400 rounded-lg hover:bg-zinc-700 transition-colors"
              >
                Отмена
              </button>
              <button
                type="submit"
                disabled={busy}
                className="flex-1 py-2.5 bg-violet-600 text-white rounded-lg hover:bg-violet-500 transition-colors disabled:opacity-50"
              >
                {busy ? '...' : 'Сменить'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
