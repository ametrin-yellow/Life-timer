export interface Task {
  id: string
  plan_id: number
  name: string
  allocated_seconds: number
  elapsed_seconds: number
  overrun_seconds: number
  status: 'pending' | 'active' | 'completed' | 'skipped'
  scheduled_time: string | null
  position: number
  priority: 'high' | 'normal' | 'low'
  is_recurring: boolean
  schedule_days: string | null
  scheduled_date: string | null
  coins_earned: number
  coins_penalty: number
  started_at: string | null
  created_at: string
  completed_at: string | null
}

export interface TimerState {
  plan_id: number
  date: string
  server_time: string
  active_task_id: string | null
  procrastination_seconds: number
  procrastination_running: boolean
  tasks: Task[]
  day_finalized: boolean
  next_day_boundary: string | null
}

export interface DayPlan {
  id: number
  date: string
  procrastination_used: number
  day_bonus: number
  day_penalty: number
  day_total: number
  day_finalized: boolean
  tasks: Task[]
}

export interface AuthTokens {
  access_token: string
  refresh_token: string
  token_type: string
}
