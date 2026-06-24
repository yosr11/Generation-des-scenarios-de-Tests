import React from 'react'
import { AlertCircle, CheckCircle, Clock } from 'lucide-react'

interface KPICardProps {
  title: string
  value: string | number
  subtitle?: string
  variant?: 'default' | 'success' | 'warning' | 'error'
  icon?: React.ReactNode
  trend?: { value: number; direction: 'up' | 'down' }
}

const variantStyles = {
  default: 'bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200',
  success: 'bg-gradient-to-br from-green-50 to-green-100 border-green-200',
  warning: 'bg-gradient-to-br from-amber-50 to-amber-100 border-amber-200',
  error: 'bg-gradient-to-br from-red-50 to-red-100 border-red-200',
}

const iconColorStyles = {
  default: 'text-blue-600',
  success: 'text-green-600',
  warning: 'text-amber-600',
  error: 'text-red-600',
}

export const KPICard: React.FC<KPICardProps> = ({
  title,
  value,
  subtitle,
  variant = 'default',
  icon,
  trend,
}) => {
  return (
    <div
      className={`
        rounded-xl border-2 p-6 transition-all duration-200 hover:shadow-md
        ${variantStyles[variant]}
      `}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <p className="text-sm font-medium text-slate-600 mb-2">{title}</p>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold text-slate-900">{value}</span>
            {trend && (
              <span
                className={`
                  text-sm font-semibold
                  ${trend.direction === 'up' ? 'text-green-600' : 'text-red-600'}
                `}
              >
                {trend.direction === 'up' ? '↑' : '↓'} {Math.abs(trend.value)}%
              </span>
            )}
          </div>
          {subtitle && <p className="text-xs text-slate-500 mt-1">{subtitle}</p>}
        </div>
        {icon && <div className={`text-4xl ${iconColorStyles[variant]}`}>{icon}</div>}
      </div>
    </div>
  )
}

interface StatsGridProps {
  stats: KPICardProps[]
}

export const StatsGrid: React.FC<StatsGridProps> = ({ stats }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {stats.map((stat, idx) => (
        <KPICard key={idx} {...stat} />
      ))}
    </div>
  )
}
