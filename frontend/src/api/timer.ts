import { apiFetch } from './client'
import type { TimerState, DayPlan } from '../types'

export const timerApi = {
  getState: () => apiFetch<TimerState>('/timer/state'),

  startTask: (taskId: string) =>
    apiFetch<TimerState>(`/timer/tasks/${taskId}/start`, { method: 'POST' }),

  pauseTask: (taskId: string) =>
    apiFetch<TimerState>(`/timer/tasks/${taskId}/pause`, { method: 'POST' }),

  completeTask: (taskId: string) =>
    apiFetch<TimerState>(`/timer/tasks/${taskId}/complete`, { method: 'POST' }),

  skipTask: (taskId: string) =>
    apiFetch<TimerState>(`/timer/tasks/${taskId}/skip`, { method: 'POST' }),
}

export const statsApi = {
  getPlans: (dateFrom?: string, dateTo?: string) => {
    const params = new URLSearchParams()
    if (dateFrom) params.set('date_from', dateFrom)
    if (dateTo) params.set('date_to', dateTo)
    const qs = params.toString()
    return apiFetch<DayPlan[]>(`/plans/${qs ? `?${qs}` : ''}`)
  },

  getPlan: (planId: number) =>
    apiFetch<DayPlan>(`/plans/${planId}`),
}

export const planApi = {
  createTask: (planId: number, data: {
    name: string
    allocated_seconds: number
    priority?: string
    scheduled_time?: string
  }) => apiFetch(`/plans/${planId}/tasks`, {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  deleteTask: (planId: number, taskId: string) =>
    apiFetch(`/plans/${planId}/tasks/${taskId}`, { method: 'DELETE' }),

  updateTask: (planId: number, taskId: string, data: Record<string, unknown>) =>
    apiFetch(`/plans/${planId}/tasks/${taskId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  reorderTasks: (planId: number, taskIds: string[]) =>
    apiFetch(`/plans/${planId}/tasks/reorder`, {
      method: 'POST',
      body: JSON.stringify(taskIds),
    }),
}
