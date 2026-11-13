// =============================================================================
// PROJECT NEXUS AI - Registration Page
// =============================================================================

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import { useAuth } from '@/context/AuthContext'
import { Mail, UserIcon, AlertCircle, Loader2 } from 'lucide-react'

const registerSchema = z
  .object({
    full_name: z.string().min(2, 'Full name must be at least 2 characters'),
    email: z.string().email('Invalid email address'),
    password: z
      .string()
      .min(12, 'Password must be at least 12 characters')
      .regex(/[A-Z]/, 'Password must contain an uppercase letter')
      .regex(/[a-z]/, 'Password must contain a lowercase letter')
      .regex(/[0-9]/, 'Password must contain a number')
      .regex(/[^A-Za-z0-9]/, 'Password must contain a special character'),
    confirm_password: z.string(),
    accept_terms: z.boolean().refine((val) => val === true, {
      message: 'You must accept the terms of service',
    }),
    accept_privacy: z.boolean().refine((val) => val === true, {
      message: 'You must acknowledge the privacy notice',
    }),
  })
  .refine((data) => data.password === data.confirm_password, {
    message: 'Passwords do not match',
    path: ['confirm_password'],
  })

export function RegisterPage() {
  const navigate = useNavigate()
  const { register } = useAuth()
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const form = useForm<z.infer<typeof registerSchema>>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      full_name: '',
      email: '',
      password: '',
      confirm_password: '',
      accept_terms: false,
      accept_privacy: false,
    },
  })

  const onSubmit = async (data: z.infer<typeof registerSchema>) => {
    setError(null)
    setIsLoading(true)
    try {
      await register(data)
      navigate('/verify-email', { state: { email: data.email } })
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Registration failed. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex h-screen items-center justify-center bg-nexus-deeper p-4">
      <div className="w-full max-w-md p-8 bg-slate-800/50 border border-slate-700 rounded-xl">
        <div className="flex flex-col items-center mb-8">
          <div className="w-12 h-12 bg-nexus-accent rounded-xl flex items-center justify-center text-nexus-dark font-bold text-xl mb-4">
            N
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Create Account</h1>
          <p className="text-slate-400 text-sm mt-1">Join PROJECT NEXUS AI</p>
        </div>

        {error && (
          <div className="mb-6 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center gap-2">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Full Name
            </label>
            <div className="relative">
              <UserIcon size={18} className="absolute left-3 top-3 text-slate-500" />
              <input
                {...form.register('full_name')}
                type="text"
                placeholder="Jane Investigator"
                className="w-full pl-10 pr-4 py-3 bg-slate-900 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:border-nexus-accent focus:ring-1 focus:ring-nexus-accent"
              />
              {form.formState.errors.full_name && (
                <p className="mt-1 text-xs text-red-400">{form.formState.errors.full_name.message}</p>
              )}
            </div>
          </div>

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
                className="w-full pl-10 pr-4 py-3 bg-slate-900 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:border-nexus-accent focus:ring-1 focus:ring-nexus-accent"
              />
              {form.formState.errors.email && (
                <p className="mt-1 text-xs text-red-400">{form.formState.errors.email.message}</p>
              )}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Password
            </label>
            <input
              {...form.register('password')}
              type="password"
              placeholder="••••••••••••"
              className="w-full px-4 py-3 bg-slate-900 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:border-nexus-accent focus:ring-1 focus:ring-nexus-accent"
            />
            <p className="mt-1 text-xs text-slate-500">
              12+ chars, uppercase, lowercase, number, special character
            </p>
            {form.formState.errors.password && (
              <p className="mt-1 text-xs text-red-400">{form.formState.errors.password.message}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Confirm Password
            </label>
            <input
              {...form.register('confirm_password')}
              type="password"
              placeholder="••••••••••••"
              className="w-full px-4 py-3 bg-slate-900 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:border-nexus-accent focus:ring-1 focus:ring-nexus-accent"
            />
            {form.formState.errors.confirm_password && (
              <p className="mt-1 text-xs text-red-400">{form.formState.errors.confirm_password.message}</p>
            )}
          </div>

          <div className="flex items-start gap-3 mb-4">
            <input
              {...form.register('accept_terms')}
              type="checkbox"
              className="checkbox mt-0.5"
            />
            <label className="text-sm text-slate-300 leading-snug">
              I accept the{' '}
              <a href="/terms-of-service" className="text-nexus-accent hover:underline">
                Terms of Service
              </a>
            </label>
          </div>

          <div className="flex items-start gap-3 mb-6">
            <input
              {...form.register('accept_privacy')}
              type="checkbox"
              className="checkbox mt-0.5"
            />
            <label className="text-sm text-slate-300 leading-snug">
              I acknowledge the{' '}
              <a href="/privacy-policy" className="text-nexus-accent hover:underline">
                Privacy Notice
              </a>
            </label>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full btn-primary py-3"
          >
            {isLoading ? (
              <>
                <Loader2 size={18} className="mr-2 animate-spin" />
                Creating account...
              </>
            ) : (
              'Create Account'
            )}
          </button>

          <p className="text-sm text-slate-400 text-center mt-6">
            Already have an account?{' '}
            <a href="/login" className="text-nexus-accent hover:text-nexus-accentHover font-medium">
              Sign in
            </a>
          </p>

          <p className="text-xs text-slate-500 text-center mt-4">
            Email verification is required before you can sign in.
          </p>
        </form>
      </div>
    </div>
  )
}
