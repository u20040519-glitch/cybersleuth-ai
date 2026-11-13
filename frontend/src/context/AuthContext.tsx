// =============================================================================
// PROJECT NEXUS AI - Auth Context
// =============================================================================
// Authentication state management with secure httpOnly cookie handling.
// Tokens are never accessible to JavaScript (stored in httpOnly cookies).
// =============================================================================

import { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react'
import { authAPI, User } from '@/services/api'

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
    accept_terms: boolean
    accept_privacy: boolean
  }) => Promise<void>
  logout: () => Promise<void>
  verifyEmail: (token: string) => Promise<void>
  forgotPassword: (email: string) => Promise<void>
  resetPassword: (token: string, new_password: string) => Promise<void>
  changePassword: (current_password: string, new_password: string) => Promise<void>
  resendVerification: (email: string) => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // Check authentication on mount
  useEffect(() => {
    checkAuth()
  }, [])

  const checkAuth = useCallback(async () => {
    try {
      const response = await authAPI.getProfile()
      setUser(response.data)
    } catch {
      setUser(null)
    } finally {
      setIsLoading(false)
    }
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    await authAPI.login({ email, password })
    // Tokens are set in httpOnly cookies by the backend
    await checkAuth()
  }, [checkAuth])

  const register = useCallback(async (data: {
    full_name: string
    email: string
    password: string
    confirm_password: string
    accept_terms: boolean
    accept_privacy: boolean
  }) => {
    await authAPI.register(data)
    // After registration, user needs to verify email before login
  }, [])

  const logout = useCallback(async () => {
    await authAPI.logout()
    setUser(null)
  }, [])

  const verifyEmail = useCallback(async (token: string) => {
    await authAPI.verifyEmail(token)
    await checkAuth()
  }, [checkAuth])

  const forgotPassword = useCallback(async (email: string) => {
    await authAPI.forgotPassword(email)
  }, [])

  const resetPassword = useCallback(async (token: string, new_password: string) => {
    await authAPI.resetPassword({ token, new_password })
  }, [])

  const changePassword = useCallback(
    async (current_password: string, new_password: string) => {
      await authAPI.changePassword({ current_password, new_password })
    },
    []
  )

  const resendVerification = useCallback(async (email: string) => {
    await authAPI.resendVerification(email)
  }, [])

  const value = {
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    register,
    logout,
    verifyEmail,
    forgotPassword,
    resetPassword,
    changePassword,
    resendVerification,
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
