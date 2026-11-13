// =============================================================================
// PROJECT NEXUS AI - Login Page
// =============================================================================

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import { useAuth } from '@/context/AuthContext'
import { Mail, Lock, Eye, EyeOff, AlertCircle, Loader2 } from 'lucide-react'

const loginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(1, 'Password is required'),
})

export function LoginPage() {
  const navigate = useNavigate()
  const { login, isLoading } = useAuth()
  const [error, setError] = useState<string | null>(null)
  const [showPassword, setShowPassword] = useState(false)

  const form = useForm<z.infer<typeof loginSchema>>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', password: '' },
  })

  const onSubmit = async (data: z.infer<typeof loginSchema>) => {
    setError(null)
    try {
      await login(data.email, data.password)
      navigate('/dashboard', { replace: true })
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid email or password')
    }
  }

  return (
    <div className="flex h-screen items-center justify-center bg-nexus-deeper">
      <div className="w-full max-w-md p-8">
        {/* Brand */}
        <div className="flex flex-col items-center mb-8">
          <div className="w-12 h-12 bg-nexus-accent rounded-xl flex items-center justify-center text-nexus-dark font-bold text-xl mb-4">
            N
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">PROJECT NEXUS AI</h1>
          <p className="text-slate-400 text-sm mt-1">Secure Forensic Investigation Platform</p>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center gap-2">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        {/* Login Form */}
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Email Address
            </label>
            <div className="relative">
              <Mail size={18} className="absolute left-3 top-3 text-slate-500" />
              <input
                {...form.register('email')}
                type="email"
                placeholder="name@organization.com"
                className="w-full pl-10 pr-4 py-3 bg-slate-800 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:border-nexus-accent focus:ring-1 focus:ring-nexus-accent transition-all"
                disabled={isLoading}
              />
              {form.formState.errors.email && (
                <p className="mt-1 text-xs text-red-400">{form.formState.errors.email.message}</p>
              )}
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-slate-300">
                Password
              </label>
            </div>
            <div className="relative">
              <Lock size={18} className="absolute left-3 top-3 text-slate-500" />
              <input
                {...form.register('password')}
                type={showPassword ? 'text' : 'password'}
                placeholder="••••••••"
                className="w-full pl-10 pr-10 py-3 bg-slate-800 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:border-nexus-accent focus:ring-1 focus:ring-nexus-accent transition-all"
                disabled={isLoading}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-3 text-slate-500 hover:text-white"
                aria-label="Toggle password visibility"
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
              {form.formState.errors.password && (
                <p className="mt-1 text-xs text-red-400">{form.formState.errors.password.message}</p>
              )}
            </div>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full btn-primary py-3"
          >
            {isLoading ? (
              <>
                <Loader2 size={18} className="mr-2 animate-spin" />
                Signing in...
              </>
            ) : (
              'Sign In'
            )}
          </button>

          <p className="text-sm text-slate-400 text-center mt-6">
            Don't have an account?{' '}
            <a href="/register" className="text-nexus-accent hover:text-nexus-accentHover font-medium">
              Create account
            </a>
          </p>
        </form>

        <p className="text-xs text-slate-500 text-center mt-8">
          PROJECT NEXUS AI - Academic Project • Secure by Design
        </p>
      </div>
    </div>
  )
}
