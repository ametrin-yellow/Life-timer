import { useState, useEffect, useCallback, useRef } from 'react'
import { getToken } from '../api/client'
import { timerApi } from '../api/timer'
import type { TimerState, Task } from '../types'

function computeElapsed(task: Task, now: number, serverOffset: number): number {
  if (!task.started_at) return task.elapsed_seconds
  const startedAt = new Date(task.started_at).getTime()
  const delta = Math.max(0, Math.floor((now - startedAt - serverOffset) / 1000))
  return task.elapsed_seconds + delta
}

function computeProcrastination(state: TimerState, now: number, serverOffset: number): number {
  if (!state.procrastination_running) return state.procrastination_seconds
  const serverTime = new Date(state.server_time).getTime()
  const delta = Math.max(0, Math.floor((now - serverTime - serverOffset) / 1000))
  return state.procrastination_seconds + delta
}

export interface LiveTimerState {
  state: TimerState | null
  loading: boolean
  tasks: (Task & { live_elapsed: number })[]
  liveProcrastination: number
  activeTask: (Task & { live_elapsed: number }) | null
  refresh: () => Promise<void>
}

export function useTimer(): LiveTimerState {
  const [state, setState] = useState<TimerState | null>(null)
  const [loading, setLoading] = useState(true)
  const serverOffsetRef = useRef(0)
  const [tick, setTick] = useState(0)

  const refresh = useCallback(async () => {
    try {
      const before = Date.now()
      const s = await timerApi.getState()
      const rtt = Date.now() - before
      serverOffsetRef.current = Date.now() - new Date(s.server_time).getTime() - rtt / 2
      setState(s)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  useEffect(() => {
    const token = getToken()
    if (!token) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws/timer/ws?token=${token}`
    let ws: WebSocket | null = null
    let reconnectTimer: ReturnType<typeof setTimeout>

    function connect() {
      ws = new WebSocket(wsUrl)
      ws.onmessage = (e) => {
        const data: TimerState = JSON.parse(e.data)
        serverOffsetRef.current = Date.now() - new Date(data.server_time).getTime()
        setState(data)
      }
      ws.onclose = () => {
        reconnectTimer = setTimeout(connect, 3000)
      }
    }

    connect()
    return () => {
      clearTimeout(reconnectTimer)
      ws?.close()
    }
  }, [])

  useEffect(() => {
    const interval = setInterval(() => setTick((t) => t + 1), 1000)
    return () => clearInterval(interval)
  }, [])

  const now = Date.now()
  const offset = serverOffsetRef.current
  void tick

  const tasks = (state?.tasks ?? []).map((t) => ({
    ...t,
    live_elapsed: computeElapsed(t, now, offset),
  }))

  const activeTask = tasks.find((t) => t.id === state?.active_task_id) ?? null

  const liveProcrastination = state
    ? computeProcrastination(state, now, offset)
    : 0

  return { state, loading, tasks, liveProcrastination, activeTask, refresh }
}
