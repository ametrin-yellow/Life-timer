import { useState } from 'react'
import { AuthProvider, useAuth } from './hooks/useAuth'
import LoginPage from './pages/LoginPage'
import TimerPage from './pages/TimerPage'
import StatsPage from './pages/StatsPage'
import AllTasksPage from './pages/AllTasksPage'

type View = 'timer' | 'stats' | 'all-tasks'

function Router() {
  const { isAuthenticated } = useAuth()
  const [view, setView] = useState<View>('timer')

  if (!isAuthenticated) return <LoginPage />

  switch (view) {
    case 'stats':
      return <StatsPage onBack={() => setView('timer')} />
    case 'all-tasks':
      return <AllTasksPage onBack={() => setView('timer')} />
    default:
      return (
        <TimerPage
          onStats={() => setView('stats')}
          onAllTasks={() => setView('all-tasks')}
        />
      )
  }
}

export default function App() {
  return (
    <AuthProvider>
      <Router />
    </AuthProvider>
  )
}
