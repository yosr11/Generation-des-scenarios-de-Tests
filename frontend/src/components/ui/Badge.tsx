import React from 'react'

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'primary' | 'success' | 'warning' | 'error' | 'info' | 'violet' | 'rose' | 'orange' | 'navy'
  size?: 'sm' | 'md'
  dot?: boolean
}

const variantStyles: Record<string, string> = {
  default: 'bg-gray-100 text-gray-700',
  primary: 'bg-brand-navy/10 text-brand-navy',
  success: 'bg-emerald-50 text-emerald-700 border border-emerald-200',
  warning: 'bg-orange-50 text-brand-orange border border-orange-200',
  error:   'bg-red-50 text-brand-red border border-red-200',
  info:    'bg-violet-50 text-brand-violet border border-violet-200',
  violet:  'bg-brand-violet/10 text-brand-violet border border-brand-violet/20',
  rose:    'bg-brand-rose/10 text-brand-rose border border-brand-rose/20',
  orange:  'bg-brand-orange/10 text-brand-orange border border-brand-orange/20',
}

const dotColors: Record<string, string> = {
  default: 'bg-gray-500',
  primary: 'bg-brand-navy',
  success: 'bg-emerald-500',
  warning: 'bg-brand-orange',
  error:   'bg-brand-red',
  info:    'bg-brand-violet',
  violet:  'bg-brand-violet',
  rose:    'bg-brand-rose',
  orange:  'bg-brand-orange',
}

const sizeStyles: Record<string, string> = {
  sm: 'px-2 py-0.5 text-[10px] font-bold',
  md: 'px-2.5 py-1 text-xs font-semibold',
}

export const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
  (
    {
      className = '',
      variant = 'default',
      size = 'md',
      dot = false,
      children,
      ...props
    },
    ref
  ) => {
    return (
      <span
        ref={ref}
        className={`
          inline-flex items-center gap-1.5
          rounded-full uppercase tracking-wide
          ${variantStyles[variant]}
          ${sizeStyles[size]}
          ${className}
        `}
        {...props}
      >
        {dot && (
          <span className={`w-1.5 h-1.5 rounded-full ${dotColors[variant]} flex-shrink-0`} />
        )}
        {children}
      </span>
    )
  }
)

Badge.displayName = 'Badge'
