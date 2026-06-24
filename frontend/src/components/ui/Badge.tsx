import React from 'react'

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'primary' | 'success' | 'warning' | 'error' | 'info'
  size?: 'sm' | 'md'
}

const variantStyles = {
  default: 'bg-brand-bg text-brand-navy',
  primary: 'bg-brand-navy/10 text-brand-navy',
  success: 'bg-green-100 text-green-700',
  warning: 'bg-brand-orange/15 text-brand-orange',
  error: 'bg-red-100 text-red-700',
  info: 'bg-brand-bg text-brand-navy border border-brand-navy/20',
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
