import React from 'react'
import { AlertCircle, CheckCircle2, AlertTriangle, Info, X } from 'lucide-react'

type AlertType = 'info' | 'success' | 'warning' | 'error'

interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  type?: AlertType
  title?: string
  description?: string
  children?: React.ReactNode
  dismissible?: boolean
  onDismiss?: () => void
}

const alertStyles: Record<AlertType, {
  container: string; title: string; description: string; icon: string; iconBg: string
}> = {
  info: {
    container:   'bg-brand-violet/5 border border-brand-violet/15',
    title:       'text-brand-violet',
    description: 'text-brand-violet/80',
    icon:        'text-brand-violet',
    iconBg:      'bg-brand-violet/10',
  },
  success: {
    container:   'bg-emerald-50 border border-emerald-200',
    title:       'text-emerald-800',
    description: 'text-emerald-700',
    icon:        'text-emerald-600',
    iconBg:      'bg-emerald-100',
  },
  warning: {
    container:   'bg-orange-50 border border-orange-200',
    title:       'text-orange-800',
    description: 'text-orange-700',
    icon:        'text-brand-orange',
    iconBg:      'bg-orange-100',
  },
  error: {
    container:   'bg-brand-rose/5 border border-brand-rose/20',
    title:       'text-brand-rose',
    description: 'text-brand-rose/80',
    icon:        'text-brand-rose',
    iconBg:      'bg-brand-rose/10',
  },
}

const alertIcons: Record<AlertType, React.ElementType> = {
  info:    Info,
  success: CheckCircle2,
  warning: AlertTriangle,
  error:   AlertCircle,
}

export const Alert = React.forwardRef<HTMLDivElement, AlertProps>(
  (
    {
      className = '',
      type = 'info',
      title,
      description,
      children,
      dismissible = false,
      onDismiss,
      ...props
    },
    ref
  ) => {
    const [isVisible, setIsVisible] = React.useState(true)

    if (!isVisible) return null

    const style = alertStyles[type]
    const Icon = alertIcons[type]

    const handleDismiss = () => {
      setIsVisible(false)
      onDismiss?.()
    }

    return (
      <div
        ref={ref}
        className={`
          rounded-2xl p-4 flex gap-3 items-start animate-fade-in
          ${style.container}
          ${className}
        `}
        role="alert"
        {...props}
      >
        <div className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 ${style.iconBg}`}>
          <Icon className={`w-4 h-4 ${style.icon}`} />
        </div>
        <div className="flex-1 min-w-0">
          {title && (
            <h4 className={`font-bold text-sm ${style.title}`}>{title}</h4>
          )}
          {description && (
            <p className={`text-sm ${style.description} ${title ? 'mt-0.5' : ''} leading-relaxed`}>
              {description}
            </p>
          )}
          {children && <div className={`text-sm ${style.description}`}>{children}</div>}
        </div>
        {dismissible && (
          <button
            onClick={handleDismiss}
            className={`flex-shrink-0 p-1 rounded-lg hover:bg-black/5 transition-colors ${style.icon}`}
          >
            <X size={14} />
          </button>
        )}
      </div>
    )
  }
)

Alert.displayName = 'Alert'
