// =============================================================================
// CYBERSLEUTH AI - Auth Context
// =============================================================================
// Authenticates against the live backend. Access/refresh tokens are kept in
// localStorage (see services/api.ts); `auth/me` rehydrates the profile on
// reload; 401s trigger a single refresh and then an `auth:unauthorized`
// event that this provider listens for.
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
import { authAPI, tokenStore } from '@/services/api'

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
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

function toUser(payload: any): User {
  return {
    id: String(payload.id),
    email: payload.email,
    full_name: payload.full_name,
    role: payload.role,
    created_at: payload.created_at,
    updated_at: payload.updated_at,
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    async function restore() {
      if (!tokenStore.access) {
        setIsLoading(false)
        return
      }
      try {
        const res = await authAPI.me()
        if (!cancelled) setUser(toUser(res.data))
      } catch {
        if (!cancelled) {
          tokenStore.clear()
          setUser(null)
        }
      } finally {
        if (!cancelled) setIsLoading(false)
      }
    }
    restore()

    const onUnauthorized = () => {
      tokenStore.clear()
      setUser(null)
    }
    window.addEventListener('auth:unauthorized', onUnauthorized)
    return () => {
      cancelled = true
      window.removeEventListener('auth:unauthorized', onUnauthorized)
    }
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    try {
      const res = await authAPI.login(email, password)
      tokenStore.save(res.data.access_token, res.data.refresh_token)
      setUser(toUser(res.data.user))
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      throw new Error(typeof detail === 'string' ? detail : 'Invalid email or password')
    }
  }, [])

  const register = useCallback(async (data: {
    full_name: string
    email: string
    password: string
    confirm_password: string
    role?: UserRole
  }) => {
    try {
      const res = await authAPI.register(data)
      tokenStore.save(res.data.access_token, res.data.refresh_token)
      setUser(toUser(res.data.user))
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      const validation = err?.response?.data?.errors?.[0]?.msg
      throw new Error(
        typeof detail === 'string' ? detail : validation ?? 'Registration failed. Please try again.',
      )
    }
  }, [])

  const logout = useCallback(async () => {
    try {
      await authAPI.logout()
    } catch {
      // Best effort: the token is discarded locally either way.
    }
    tokenStore.clear()
    setUser(null)
  }, [])

  const value = {
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    register,
    logout,
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
