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

/**
 * Turns an API error into a message that tells the truth.
 *
 * A request that never reached the API (the demo backend is behind a tunnel
 * whose address changes, the network is down, the browser blocked the
 * request) used to be reported as "Invalid email or password", which sent
 * everybody looking for a typing error instead of the real problem. The same
 * was true for a response that is not the API's JSON at all - for example
 * the HTML error page of a static host that has no /api route.
 */
export function describeAuthError(err: any, fallback: string): string {
  const response = err?.response

  // No response: the request never made it to the API.
  if (!response) {
    const code = err?.code ? ` (${err.code})` : ''
    return (
      `Cannot reach the API${code}. The demo backend is offline or the address changed - ` +
      'check the "API status" above, then try again.'
    )
  }

  const status = response.status
  const detail = response.data?.detail

  // The API answered with its own error format.
  if (typeof detail === 'string' && detail) {
    if (status === 429) {
      return 'Too many attempts from this address. Please wait a minute and try again.'
    }
    return detail
  }

  if (status === 429) {
    return 'Too many attempts from this address. Please wait a minute and try again.'
  }

  if (status === 401) {
    return fallback
  }

  if (status >= 500) {
    return `The API reported an error (${status}). It may be restarting - please try again in a moment.`
  }

  // Any other status without the API's JSON body: the address does not point
  // at the CyberSleuth API (a static host answers 404 with an HTML page).
  return (
    `The API answered ${status} instead of the expected response. ` +
    'The configured address does not point at the CyberSleuth API - check the "API status" above.'
  )
}

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
      throw new Error(describeAuthError(err, 'Invalid email or password'))
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
        typeof detail === 'string'
          ? detail
          : validation ?? describeAuthError(err, 'Registration failed. Please try again.'),
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
