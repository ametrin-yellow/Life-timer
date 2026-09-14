import { useState, useEffect, useRef, useCallback } from 'react'
import { useAuth } from '../hooks/useAuth'

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: { client_id: string; callback: (response: { credential: string }) => void }) => void
          renderButton: (el: HTMLElement, config: { theme: string; size: string; width: number; text: string; locale: string }) => void
        }
      }
    }
    onTelegramAuth?: (user: Record<string, unknown>) => void
  }
}

export default function LoginPage() {
  const { login, register, googleLogin, telegramLogin } = useAuth()
  const [isRegister, setIsRegister] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [googleClientId, setGoogleClientId] = useState<string | null>(null)
  const [telegramBot, setTelegramBot] = useState<string | null>(null)
  const googleBtnRef = useRef<HTMLDivElement>(null)
  const telegramBtnRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetch('/api/auth/google-client-id')
      .then((r) => r.json())
      .then((data) => {
        if (data.client_id) setGoogleClientId(data.client_id)
      })
      .catch(() => {})

    fetch('/api/auth/telegram-bot')
      .then((r) => r.json())
      .then((data) => {
        if (data.bot_username) setTelegramBot(data.bot_username)
      })
      .catch(() => {})
  }, [])

  const handleTelegramAuth = useCallback(async (user: Record<string, unknown>) => {
    setError('')
    setLoading(true)
    try {
      await telegramLogin(user)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка входа через Telegram')
    } finally {
      setLoading(false)
    }
  }, [telegramLogin])

  useEffect(() => {
    if (!googleClientId || !googleBtnRef.current || !window.google) return

    window.google.accounts.id.initialize({
      client_id: googleClientId,
      callback: async (response) => {
        setError('')
        setLoading(true)
        try {
          await googleLogin(response.credential)
        } catch (err) {
          setError(err instanceof Error ? err.message : 'Ошибка входа через Google')
        } finally {
          setLoading(false)
        }
      },
    })

    window.google.accounts.id.renderButton(googleBtnRef.current, {
      theme: 'filled_black',
      size: 'large',
      width: 352,
      text: 'signin_with',
      locale: 'ru',
    })
  }, [googleClientId, googleLogin])

  useEffect(() => {
    if (!telegramBot || !telegramBtnRef.current) return

    window.onTelegramAuth = handleTelegramAuth

    const el = telegramBtnRef.current
    el.innerHTML = ''
    const script = document.createElement('script')
    script.src = 'https://telegram.org/js/telegram-widget.js?22'
    script.setAttribute('data-telegram-login', telegramBot)
    script.setAttribute('data-size', 'large')
    script.setAttribute('data-radius', '8')
    script.setAttribute('data-onauth', 'onTelegramAuth(user)')
    script.setAttribute('data-request-access', 'write')
    script.async = true
    el.appendChild(script)

    return () => {
      delete window.onTelegramAuth
    }
  }, [telegramBot, handleTelegramAuth])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      if (isRegister) {
        await register(email, password)
      } else {
        await login(email, password)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Что-то пошло не так')
    } finally {
      setLoading(false)
    }
  }

  const hasOAuth = googleClientId || telegramBot

  return (
    <div className="min-h-screen flex items-center justify-center bg-zinc-950 px-4">
      <div className="w-full max-w-sm">
        <h1 className="text-3xl font-bold text-center text-white mb-8">
          Life Timer
        </h1>
        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="email"
            placeholder="Электронная почта"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="w-full px-4 py-3 bg-zinc-900 border border-zinc-800 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:border-violet-500"
          />
          <input
            type="password"
            placeholder="Пароль"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={6}
            className="w-full px-4 py-3 bg-zinc-900 border border-zinc-800 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:border-violet-500"
          />
          {error && (
            <p className="text-red-400 text-sm">{error}</p>
          )}
          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white font-medium rounded-lg transition-colors"
          >
            {loading ? '...' : isRegister ? 'Зарегистрироваться' : 'Войти'}
          </button>
        </form>
        <button
          onClick={() => { setIsRegister(!isRegister); setError('') }}
          className="mt-4 w-full text-center text-sm text-zinc-500 hover:text-zinc-300 transition-colors"
        >
          {isRegister ? 'Уже есть аккаунт? Войти' : 'Нет аккаунта? Зарегистрироваться'}
        </button>

        {hasOAuth && (
          <>
            <div className="flex items-center gap-3 my-6">
              <div className="flex-1 h-px bg-zinc-800" />
              <span className="text-xs text-zinc-600">или</span>
              <div className="flex-1 h-px bg-zinc-800" />
            </div>
            <div className="space-y-3">
              {telegramBot && (
                <div ref={telegramBtnRef} className="flex justify-center" />
              )}
              {googleClientId && (
                <div ref={googleBtnRef} className="flex justify-center" />
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
