import React from 'react'

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'primary' | 'success' | 'warning' | 'error' | 'info'
  size?: 'sm' | 'md'
}

const variantStyles = {
  default: 'bg-slate-100 text-slate-700',
  primary: 'bg-blue-100 text-blue-700',
  success: 'bg-green-100 text-green-700',
  warning: 'bg-amber-100 text-amber-700',
  error: 'bg-red-100 text-red-700',
  info: 'bg-cyan-100 text-cyan-700',
}

const sizeStyles = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-2.5 py-1 text-sm',
}

export const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
  (
    {
      className = '',
      variant = 'default',
      size = 'md',
      children,
      ...props
    },
    ref
  ) => {
    return (
      <span
        ref={ref}
        className={`
          inline-flex items-center justify-center font-medium rounded-full
          ${variantStyles[variant]}
          ${sizeStyles[size]}
          ${className}
        `}
        {...props}
      >
        {children}
      </span>
    )
  }
)

Badge.displayName = 'Badge'
