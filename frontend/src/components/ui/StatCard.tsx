// =============================================================================
// CYBERSLEUTH AI - StatCard Component
// =============================================================================

interface StatCardProps {
  title: string
  value: string | number
  subtitle?: string
  icon: React.ElementType
  color: string
  trend?: { value: number; label: string; positive: boolean }
}

export function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  color,
  trend,
}: StatCardProps) {
  return (
    <div className="bg-card border border-border rounded-xl p-5 shadow-cyber">
      <div className="flex items-center justify-between mb-3">
        <div>
          <p className="text-sm text-text-secondary font-medium">{title}</p>
          <p className="text-2xl font-bold text-text-main">{value}</p>
          {subtitle && <p className="text-xs text-text-secondary/70">{subtitle}</p>}
        </div>
        <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-secondary border border-border">
          <Icon size={18} className={color} />
        </div>
      </div>
      {trend && (
        <div className="flex items-center gap-1 mt-2">
          <span
            className={`text-xs font-medium ${
              trend.positive ? 'text-success' : 'text-error'
            }`}
          >
            {trend.positive ? '▲' : '▼'} {trend.value}%
          </span>
          <span className="text-xs text-text-secondary">{trend.label}</span>
        </div>
      )}
    </div>
  )
}
