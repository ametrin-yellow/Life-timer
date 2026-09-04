const TOKEN_KEY = 'lt_access_token'
const REFRESH_KEY = 'lt_refresh_token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY)
}

export function setTokens(access: string, refresh: string) {
  localStorage.setItem(TOKEN_KEY, access)
  localStorage.setItem(REFRESH_KEY, refresh)
}

export function clearTokens() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(REFRESH_KEY)
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options.headers as Record<string, string>) || {}),
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`/api${path}`, { ...options, headers })

  if (res.status === 401) {
    const refreshed = await tryRefresh()
    if (refreshed) {
      headers['Authorization'] = `Bearer ${getToken()}`
      const retry = await fetch(`/api${path}`, { ...options, headers })
      if (!retry.ok) throw new ApiError(retry.status, await retry.text())
      if (retry.status === 204) return undefined as T
      return retry.json()
    }
    clearTokens()
    window.location.reload()
    throw new ApiError(401, 'Unauthorized')
  }

  if (!res.ok) throw new ApiError(res.status, await res.text())
  if (res.status === 204) return undefined as T
  return res.json()
}

async function tryRefresh(): Promise<boolean> {
  const refresh = getRefreshToken()
  if (!refresh) return false
  try {
    const res = await fetch('/api/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refresh }),
    })
    if (!res.ok) return false
    const data = await res.json()
    setTokens(data.access_token, data.refresh_token)
    return true
  } catch {
    return false
  }
}

export class ApiError extends Error {
  constructor(public status: number, public body: string) {
    super(`API error ${status}: ${body}`)
  }
}
