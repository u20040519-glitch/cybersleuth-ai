// =============================================================================
// CYBERSLEUTH AI - Loading Spinner Component
// =============================================================================

import { cn } from '@/utils/cn'

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

export function LoadingSpinner({ size = 'md', className }: LoadingSpinnerProps) {
  const sizes = {
    sm: 'h-8 w-8',
    md: 'h-12 w-12',
    lg: 'h-20 w-20',
  }

  return (
    <div
      className={cn(
        'animate-spin rounded-full border-2 border-border/50 border-t-primary-blue text-primary-blue',
        sizes[size],
        className,
      )}
      role="status"
      aria-label="Loading"
    >
      <span className="sr-only">Loading...</span>
    </div>
  )
}
