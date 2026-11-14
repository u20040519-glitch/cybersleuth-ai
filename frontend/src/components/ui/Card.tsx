// =============================================================================
// CYBERSLEUTH AI - Card Component
// =============================================================================

import * as React from 'react'
import { cn } from '@/utils/cn'

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  hover?: boolean
}

export function Card({ className, hover = false, children, ...props }: CardProps) {
  return (
    <div
      {...props}
      className={cn(
        'bg-card border border-border rounded-xl p-6 shadow-cyber transition-all duration-300',
        hover && 'card-hover',
        className,
      )}
    >
      {children}
    </div>
  )
}

interface CardHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string
  subtitle?: string
}

export function CardHeader({ className, title, subtitle, ...props }: CardHeaderProps) {
  return (
    <div
      {...props}
      className={cn('mb-4', className)}
    >
      {title && <h3 className="text-lg font-semibold text-text-main mb-1">{title}</h3>}
      {subtitle && <p className="text-sm text-text-secondary">{subtitle}</p>}
    </div>
  )
}
