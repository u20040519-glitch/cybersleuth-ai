// =============================================================================
// CYBERSLEUTH AI - Button Component
// =============================================================================

import * as React from 'react'
import { Slot } from '@radix-ui/react-slot'
import { cn } from '@/utils/cn'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'cyan' | 'secondary' | 'ghost' | 'danger' | 'success'
  size?: 'sm' | 'md' | 'lg'
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button'

    const variants = {
      primary: 'bg-primary-blue text-white hover:bg-blue-600 shadow-[0_0_15px_rgba(59,130,246,0.3)]',
      cyan: 'bg-primary-cyan text-[#080D18] hover:bg-cyan-400 shadow-[0_0_15px_rgba(34,211,238,0.3)]',
      secondary:
        'bg-secondary text-text-main border border-border hover:bg-[#1f2d44] hover:border-primary-blue/50',
      ghost:
        'bg-transparent text-text-secondary hover:bg-secondary hover:text-text-main',
      danger: 'bg-error/90 text-white hover:bg-error',
      success: 'bg-success/90 text-[#080D18] hover:bg-success',
    }

    const sizes = {
      sm: 'px-3 py-2 text-xs',
      md: 'px-4 py-2.5 text-sm',
      lg: 'px-6 py-3 text-base',
    }

    return (
      <Comp
        ref={ref}
        className={cn(
          'inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-all duration-200 disabled:opacity-50 disabled:pointer-events-none focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-blue focus-visible:ring-offset-1 focus-visible:ring-offset-background',
          variants[variant],
          sizes[size],
          className,
        )}
        {...props}
      />
    )
  },
)

Button.displayName = 'Button'

export { Button }
