// =============================================================================
// CYBERSLEUTH AI - Auth Context
// =============================================================================
// Phase 1: Supabase-ready auth context. In demo mode (no Supabase credentials),
// it uses localStorage persistence so navigation and protected routes work.
// Phase 2: Connect real Supabase client here.
// =============================================================================

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  ReactNode,
} from 'react'
import type { User, UserRole } from '@/types/index'

interface AuthContextType {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (data: {
    full_name: string
    email: string
    password: string
    confirm_password: string
    role?: UserRole
  }) => Promise<void>
  logout: () => Promise<void>
  resetPassword: (email: string) => Promise<void>
}

const DEMO_USER: User = {
  id: 'demo-user-001',
  email: 'investigator@cybersleuth.ai',
  full_name: 'Lead Investigator',
  role: 'investigator',
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
}

const DEMO_SUPERVISOR: User = {
  id: 'demo-user-002',
  email: 'supervisor@cybersleuth.ai',
  full_name: 'Case Supervisor',
  role: 'supervisor',
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
}

const STORAGE_KEY = 'cybersleuth_auth_user'

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const getDemoUser = useCallback((email: string): User | null => {
    const lower = email.toLowerCase()
    if (lower === DEMO_USER.email) return DEMO_USER
    if (lower === DEMO_SUPERVISOR.email) return DEMO_SUPERVISOR
    return null
  }, [])

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      try {
        setUser(JSON.parse(stored))
      } catch {
        setUser(null)
      }
    }
    setIsLoading(false)
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    // Phase 2: replace with supabase.auth.signInWithPassword({ email, password })
    const demoUser = getDemoUser(email)
    if (!demoUser || password.length < 6) {
      throw new Error('Invalid credentials. Try investigator@cybersleuth.ai / password123')
    }
    setUser(demoUser)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(demoUser))
  }, [getDemoUser])

  const register = useCallback(async (data: {
    full_name: string
    email: string
    password: string
    confirm_password: string
    role?: UserRole
  }) => {
    if (data.password !== data.confirm_password) {
      throw new Error('Passwords do not match')
    }
    if (data.password.length < 8) {
      throw new Error('Password must be at least 8 characters')
    }
    const newUser: User = {
      id: `user-${Math.random().toString(36).slice(2)}`,
      email: data.email,
      full_name: data.full_name,
      role: data.role || 'investigator',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
    setUser(newUser)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(newUser))
    // Phase 2: replace with supabase.auth.signUp({ email, password, ... })
  }, [])

  const logout = useCallback(async () => {
    // Phase 2: replace with supabase.auth.signOut()
    setUser(null)
    localStorage.removeItem(STORAGE_KEY)
  }, [])

  const resetPassword = useCallback(async (_email: string) => {
    // Phase 2: replace with supabase.auth.resetPasswordForEmail(email)
    return
  }, [])

  const value = {
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    register,
    logout,
    resetPassword,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
