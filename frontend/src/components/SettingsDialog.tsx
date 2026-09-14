import { useState, useEffect, useRef, useCallback } from 'react'
import { changePassword, getMe, linkTelegram, unlinkTelegram } from '../api/auth'

declare global {
  interface Window {
    onTelegramLink?: (user: Record<string, unknown>) => void
  }
}

interface Props {
  open: boolean
  onClose: () => void
}

export default function SettingsDialog({ open, onClose }: Props) {
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [pwError, setPwError] = useState('')
  const [pwDone, setPwDone] = useState(false)
  const [busy, setBusy] = useState(false)

  const [hasPassword, setHasPassword] = useState(false)
  const [hasTelegram, setHasTelegram] = useState(false)
  const [tgError, setTgError] = useState('')
  const [tgBotUsername, setTgBotUsername] = useState<string | null>(null)
  const tgBtnRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    getMe().then((me) => {
      setHasPassword(me.has_password)
      setHasTelegram(me.has_telegram)
    }).catch(() => {})

    fetch('/api/auth/telegram-bot')
      .then((r) => r.json())
      .then((data) => {
        if (data.bot_username) setTgBotUsername(data.bot_username)
      })
      .catch(() => {})
  }, [open])

  const handleTelegramLink = useCallback(async (user: Record<string, unknown>) => {
    setTgError('')
    setBusy(true)
    try {
      await linkTelegram(user)
      setHasTelegram(true)
    } catch (err) {
      setTgError(err instanceof Error ? err.message : 'Ошибка привязки')
    } finally {
      setBusy(false)
    }
  }, [])

  useEffect(() => {
    if (!open || !tgBotUsername || hasTelegram || !tgBtnRef.current) return

    window.onTelegramLink = handleTelegramLink

    const el = tgBtnRef.current
    el.innerHTML = ''
    const script = document.createElement('script')
    script.src = 'https://telegram.org/js/telegram-widget.js?22'
    script.setAttribute('data-telegram-login', tgBotUsername)
    script.setAttribute('data-size', 'medium')
    script.setAttribute('data-radius', '8')
    script.setAttribute('data-onauth', 'onTelegramLink(user)')
    script.setAttribute('data-request-access', 'write')
    script.async = true
    el.appendChild(script)

    return () => {
      delete window.onTelegramLink
    }
  }, [open, tgBotUsername, hasTelegram, handleTelegramLink])

  if (!open) return null

  function reset() {
    setCurrent('')
    setNext('')
    setConfirm('')
    setPwError('')
    setPwDone(false)
    setTgError('')
  }

  function handleClose() {
    reset()
    onClose()
  }

  async function handlePasswordSubmit(e: React.FormEvent) {
    e.preventDefault()
    setPwError('')

    if (next.length < 6) {
      setPwError('Минимум 6 символов')
      return
    }
    if (next !== confirm) {
      setPwError('Пароли не совпадают')
      return
    }

    setBusy(true)
    try {
      await changePassword(current, next)
      setPwDone(true)
      setHasPassword(true)
    } catch {
      setPwError('Неверный текущий пароль')
    } finally {
      setBusy(false)
    }
  }

  async function handleUnlinkTelegram() {
    setTgError('')
    setBusy(true)
    try {
      await unlinkTelegram()
      setHasTelegram(false)
    } catch (err) {
      setTgError(err instanceof Error ? err.message : 'Ошибка отвязки')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={handleClose}>
      <div
        className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 w-full max-w-md max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-semibold text-white mb-5">Настройки</h2>

        {/* Telegram */}
        {tgBotUsername && (
          <div className="mb-6">
            <h3 className="text-sm text-zinc-400 mb-3">Telegram</h3>
            {hasTelegram ? (
              <div className="flex items-center justify-between">
                <span className="text-sm text-green-400">Привязан</span>
                <button
                  onClick={handleUnlinkTelegram}
                  disabled={busy}
                  className="text-sm text-zinc-500 hover:text-red-400 transition-colors disabled:opacity-50"
                >
                  Отвязать
                </button>
              </div>
            ) : (
              <div ref={tgBtnRef} />
            )}
            {tgError && <p className="text-red-400 text-sm mt-2">{tgError}</p>}
          </div>
        )}

        {/* Password */}
        {hasPassword && (
          <div className="mb-4">
            <h3 className="text-sm text-zinc-400 mb-3">Смена пароля</h3>
            {pwDone ? (
              <p className="text-green-400 text-sm">Пароль изменён</p>
            ) : (
              <form onSubmit={handlePasswordSubmit} className="space-y-3">
                <input
                  type="password"
                  placeholder="Текущий пароль"
                  value={current}
                  onChange={(e) => setCurrent(e.target.value)}
                  required
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
                {pwError && <p className="text-red-400 text-sm">{pwError}</p>}
                <button
                  type="submit"
                  disabled={busy}
                  className="w-full py-2.5 bg-violet-600 text-white rounded-lg hover:bg-violet-500 transition-colors disabled:opacity-50"
                >
                  {busy ? '...' : 'Сменить пароль'}
                </button>
              </form>
            )}
          </div>
        )}

        <button
          onClick={handleClose}
          className="w-full py-2.5 mt-2 bg-zinc-800 text-zinc-400 rounded-lg hover:bg-zinc-700 transition-colors"
        >
          Закрыть
        </button>
      </div>
    </div>
  )
}
