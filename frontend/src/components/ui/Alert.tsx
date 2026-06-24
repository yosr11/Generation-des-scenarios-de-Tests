import React from 'react'
import { AlertCircle, CheckCircle, AlertTriangle, Info } from 'lucide-react'

type AlertType = 'info' | 'success' | 'warning' | 'error'

interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  type?: AlertType
  title?: string
  description?: string
  children?: React.ReactNode
  dismissible?: boolean
  onDismiss?: () => void
}

const alertStyles = {
  info: {
    container: 'bg-blue-50 border border-blue-200',
    title: 'text-blue-900',
    description: 'text-blue-700',
    icon: 'text-blue-600',
  },
  success: {
    container: 'bg-green-50 border border-green-200',
    title: 'text-green-900',
    description: 'text-green-700',
    icon: 'text-green-600',
  },
  warning: {
    container: 'bg-amber-50 border border-amber-200',
    title: 'text-amber-900',
    description: 'text-amber-700',
    icon: 'text-amber-600',
  },
  error: {
    container: 'bg-red-50 border border-red-200',
    title: 'text-red-900',
    description: 'text-red-700',
    icon: 'text-red-600',
  },
}

const alertIcons = {
  info: Info,
  success: CheckCircle,
  warning: AlertTriangle,
  error: AlertCircle,
}

export const Alert = React.forwardRef<
  HTMLDivElement,
  AlertProps
>(
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
          rounded-lg p-4 flex gap-4 items-start
          ${style.container}
          ${className}
        `}
        role="alert"
        {...props}
      >
        <Icon className={`w-5 h-5 mt-0.5 flex-shrink-0 ${style.icon}`} />
        <div className="flex-1">
          {title && <h4 className={`font-semibold ${style.title}`}>{title}</h4>}
          {description && <p className={`text-sm ${style.description} ${title ? 'mt-1' : ''}`}>{description}</p>}
          {children && <div className={style.description}>{children}</div>}
        </div>
        {dismissible && (
          <button
            onClick={handleDismiss}
            className={`flex-shrink-0 font-medium text-sm hover:opacity-70 transition ${style.description}`}
          >
            ✕
          </button>
        )}
      </div>
    )
  }
)

Alert.displayName = 'Alert'
