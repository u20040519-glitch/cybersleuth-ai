// =============================================================================
// CYBERSLEUTH AI - Empty State Component
// =============================================================================

import * as React from 'react'
import { cn } from '@/utils/cn'

interface EmptyStateProps {
  icon: React.ElementType
  title: string
  description?: string
  action?: React.ReactNode
  className?: string
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div className={cn('empty-state', className)}>
      <div className="w-20 h-20 rounded-full bg-secondary/50 flex items-center justify-center mb-6 text-text-secondary/50">
        <Icon size={28} />
      </div>
      <h3 className="text-lg font-semibold text-text-main mb-2">{title}</h3>
      {description && <p className="text-text-secondary/70 max-w-xs mb-6">{description}</p>}
      {action && action}
    </div>
  )
}
