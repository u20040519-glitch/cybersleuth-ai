// =============================================================================
// CYBERSLEUTH AI - Register Page
// =============================================================================

import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { useAuth } from '@/context/AuthContext'
import { Button } from '@/ui/Button'
import { Input } from '@/ui/Input'
import { Card, CardHeader } from '@/ui/Card'
import { User, ArrowRight } from 'lucide-react'
export function RegisterPage() {
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const { register: authRegister } = useAuth()
  const navigate = useNavigate()
  const { register, handleSubmit, formState: { errors } } = useForm<{
    full_name: string
    email: string
    password: string
    confirm_password: string
    role: string
    accept_terms: boolean
  }>()

  const onSubmit = async (data: {
    full_name: string
    email: string
    password: string
    confirm_password: string
    role: string
    accept_terms: boolean
  }) => {
    setIsLoading(true)
    setError(null)
    try {
      await authRegister({
        full_name: data.full_name,
        email: data.email,
        password: data.password,
        confirm_password: data.confirm_password,
        role: data.role as any,
      })
      navigate('/dashboard', { replace: true })
    } catch (err: any) {
      setError(err.message || 'Registration failed. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-blue to-primary-cyan flex items-center justify-center mx-auto mb-4 shadow-glow-blue">
            <User size={24} className="text-[#080D18]" />
          </div>
          <h1 className="text-2xl font-bold text-text-main">Create Account</h1>
          <p className="text-text-secondary text-sm">
            Join the digital forensics platform
          </p>
        </div>

        <Card>
          <CardHeader
            title="Register"
            subtitle="Create your investigator profile"
          />

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {error && (
              <div className="p-3 rounded-lg bg-error/10 border border-error/20 text-sm text-error">
                {error}
              </div>
            )}

            <Input
              label="Full Name"
              placeholder="Jane Investigator"
              {...register('full_name')}
              error={errors.full_name?.message}
            />

            <Input
              label="Email Address"
              type="email"
              placeholder="jane@agency.gov"
              {...register('email')}
              error={errors.email?.message}
            />

            <div className="grid grid-cols-2 gap-4">
              <Input
                label="Password"
                type="password"
                placeholder="••••••••"
                {...register('password')}
                error={errors.password?.message}
              />
              <Input
                label="Confirm Password"
                type="password"
                placeholder="••••••••"
                {...register('confirm_password')}
                error={errors.confirm_password?.message}
              />
            </div>

            <div className="flex items-start gap-2">
              <input
                id="terms"
                type="checkbox"
                className="checkbox"
                {...register('accept_terms')}
              />
              <label htmlFor="terms" className="text-sm text-text-secondary">
                I accept the terms of service and privacy policy
              </label>
              {errors.accept_terms && (
                <p className="ml-6 mt-1 text-xs text-error">Required</p>
              )}
            </div>

            <Button
              type="submit"
              variant="primary"
              className="w-full"
              disabled={isLoading}
            >
              {isLoading ? (
                <span className="flex items-center gap-2">
                  <LoadingSpinnerInline size="sm" /> Creating account...
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <ArrowRight size={16} /> Create Account
                </span>
              )}
            </Button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-text-secondary/60 text-sm">
              Already have an account?{' '}
              <Link to="/login" className="text-primary-blue hover:text-primary-cyan font-medium">
                Sign in
              </Link>
            </p>
          </div>
        </Card>
      </div>
    </div>
  )
}

function LoadingSpinnerInline({ size = 'sm' }: { size?: 'sm' | 'md' | 'lg' }) {
  const sizes = { sm: 'h-4 w-4', md: 'h-6 w-6', lg: 'h-8 w-8' }
  return (
    <div
      className={`animate-spin rounded-full border-2 border-current text-current ${sizes[size]}`}
      role="status"
      aria-label="Loading"
    >
      <span className="sr-only">Loading...</span>
    </div>
  )
}
