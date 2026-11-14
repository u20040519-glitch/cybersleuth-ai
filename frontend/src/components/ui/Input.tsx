// =============================================================================
// CYBERSLEUTH AI - Input Component
// =============================================================================

import * as React from 'react'
import { cn } from '@/utils/cn'

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  type?: 'text' | 'email' | 'password' | 'number'
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, type = 'text', ...props }, ref) => (
    <div className="mb-4">
      {label && <label className="label">{label}</label>}
      <input
        ref={ref}
        type={type}
        className={cn(
          'input',
          error && 'input-error',
          className,
        )}
        {...props}
      />
      {error && <p className="mt-1 text-xs text-error">{error}</p>}
    </div>
  ),
)

Input.displayName = 'Input'

interface TextAreaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string
  error?: string
  rows?: number
}

export const TextArea = React.forwardRef<HTMLTextAreaElement, TextAreaProps>(
  ({ className, label, error, rows = 4, ...props }, ref) => (
    <div className="mb-4">
      {label && <label className="label">{label}</label>}
      <textarea
        ref={ref}
        className={cn(
          'block w-full px-4 py-3 bg-secondary border border-border rounded-xl text-text-main placeholder-text-secondary/60 focus:border-primary-blue focus:ring-1 focus:ring-primary-blue transition-all',
          error && 'input-error',
          className,
        )}
        rows={rows}
        {...props}
      />
      {error && <p className="mt-1 text-xs text-error">{error}</p>}
    </div>
  ),
)

TextArea.displayName = 'TextArea'
