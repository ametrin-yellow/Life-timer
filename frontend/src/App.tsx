import { AuthProvider, useAuth } from './hooks/useAuth'
import LoginPage from './pages/LoginPage'
import TimerPage from './pages/TimerPage'

function Router() {
  const { isAuthenticated } = useAuth()
  return isAuthenticated ? <TimerPage /> : <LoginPage />
}

export default function App() {
  return (
    <AuthProvider>
      <Router />
    </AuthProvider>
  )
}
