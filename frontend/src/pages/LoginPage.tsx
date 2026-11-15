// =============================================================================
// CYBERSLEUTH AI - Login Page
// =============================================================================

import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { useAuth } from '@/context/AuthContext'
import { Button } from '@/ui/Button'
import { Input } from '@/ui/Input'
import { Card, CardHeader } from '@/ui/Card'
import { ShieldCheck, ArrowRight } from 'lucide-react'
export function LoginPage() {
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()
  const { register, handleSubmit, formState: { errors } } = useForm<{
    email: string
    password: string
  }>()

  const onSubmit = async (data: { email: string; password: string }) => {
    setIsLoading(true)
    setError(null)
    try {
      await login(data.email, data.password)
      navigate('/dashboard', { replace: true })
    } catch (err: any) {
      setError(err.message || 'Login failed. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }



  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-blue to-primary-cyan flex items-center justify-center mx-auto mb-4 shadow-glow-blue">
            <ShieldCheck size={24} className="text-[#080D18]" />
          </div>
          <h1 className="text-2xl font-bold text-text-main">CyberSleuth AI</h1>
          <p className="text-text-secondary text-sm">
            Multimodal Digital Forensics Platform
          </p>
        </div>

        <Card>
          <CardHeader
            title="Sign In"
            subtitle="Access your forensic investigation workspace"
          />

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {error && (
              <div className="p-3 rounded-lg bg-error/10 border border-error/20 text-sm text-error">
                {error}
              </div>
            )}

            <Input
              label="Email Address"
              type="email"
              placeholder="you@agency.gov"
              {...register('email')}
              error={errors.email?.message}
            />

            <Input
              label="Password"
              type="password"
              placeholder="••••••••"
              {...register('password')}
              error={errors.password?.message}
            />

            <Button
              type="submit"
              variant="primary"
              className="w-full"
              disabled={isLoading}
            >
              {isLoading ? (
                <span className="flex items-center gap-2">
                  <LoadingSpinnerInline size="sm" /> Signing in...
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <ArrowRight size={16} /> Sign In
                </span>
              )}
            </Button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-text-secondary/60 text-sm">
              Don&apos;t have an account?{' '}
              <Link to="/register" className="text-primary-blue hover:text-primary-cyan font-medium">
                Create account
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
