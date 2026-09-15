import { apiFetch } from './client'

export interface UserSettingsData {
  day_start_hour: number
  timezone: string
}

export function getSettings() {
  return apiFetch<UserSettingsData>('/settings/')
}

export function updateSettings(data: Partial<UserSettingsData>) {
  return apiFetch<UserSettingsData>('/settings/', {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}
