import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'
import { getToken, setTokens, clearTokens } from '../api/client'
import { login as apiLogin, register as apiRegister, googleAuth as apiGoogleAuth, telegramAuth as apiTelegramAuth } from '../api/auth'

interface AuthCtx {
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string) => Promise<void>
  googleLogin: (credential: string) => Promise<void>
  telegramLogin: (data: Record<string, unknown>) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthCtx>(null!)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(() => !!getToken())

  const login = useCallback(async (email: string, password: string) => {
    const tokens = await apiLogin(email, password)
    setTokens(tokens.access_token, tokens.refresh_token)
    setIsAuthenticated(true)
  }, [])

  const register = useCallback(async (email: string, password: string) => {
    const tokens = await apiRegister(email, password)
    setTokens(tokens.access_token, tokens.refresh_token)
    setIsAuthenticated(true)
  }, [])

  const googleLogin = useCallback(async (credential: string) => {
    const tokens = await apiGoogleAuth(credential)
    setTokens(tokens.access_token, tokens.refresh_token)
    setIsAuthenticated(true)
  }, [])

  const telegramLogin = useCallback(async (data: Record<string, unknown>) => {
    const tokens = await apiTelegramAuth(data)
    setTokens(tokens.access_token, tokens.refresh_token)
    setIsAuthenticated(true)
  }, [])

  const logout = useCallback(() => {
    clearTokens()
    setIsAuthenticated(false)
  }, [])

  return (
    <AuthContext.Provider value={{ isAuthenticated, login, register, googleLogin, telegramLogin, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
