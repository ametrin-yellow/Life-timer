import type { AuthTokens } from '../types'

export async function login(email: string, password: string): Promise<AuthTokens> {
  const body = new URLSearchParams({ username: email, password })
  const res = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text)
  }
  return res.json()
}

export async function register(email: string, password: string): Promise<AuthTokens> {
  const res = await fetch('/api/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text)
  }
  return res.json()
}
