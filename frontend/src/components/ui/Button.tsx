import React from 'react'
import { Loader2 } from 'lucide-react'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'success' | 'outline' | 'violet' | 'ghost'
  size?: 'sm' | 'md' | 'lg'
  isLoading?: boolean
  fullWidth?: boolean
}

const variantStyles: Record<string, string> = {
  primary:   'bg-grad-cta text-white hover:shadow-glow-rose hover:-translate-y-0.5 border border-transparent',
  secondary: 'bg-brand-navy text-white hover:bg-brand-navymid hover:-translate-y-0.5 border border-transparent',
  danger:    'bg-brand-red text-white hover:bg-red-600 hover:-translate-y-0.5 border border-transparent',
  success:   'bg-emerald-500 text-white hover:bg-emerald-600 hover:-translate-y-0.5 border border-transparent',
  violet:    'bg-grad-violet text-white hover:shadow-glow-violet hover:-translate-y-0.5 border border-transparent',
  outline:   'bg-white text-brand-navy border-2 border-gray-200 hover:border-brand-violet hover:text-brand-violet hover:bg-brand-violet/5',
  ghost:     'bg-brand-bg text-brand-navy border border-gray-100 hover:border-brand-violet/30 hover:bg-brand-violet/5',
}

const sizeStyles: Record<string, string> = {
  sm: 'px-3.5 py-2 text-xs font-semibold rounded-xl',
  md: 'px-5 py-2.5 text-sm font-semibold rounded-xl',
  lg: 'px-7 py-3.5 text-base font-bold rounded-xl',
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className = '',
      variant = 'primary',
      size = 'md',
      isLoading = false,
      fullWidth = false,
      disabled = false,
      children,
      ...props
    },
    ref
  ) => {
    return (
      <button
        ref={ref}
        className={`
          inline-flex items-center justify-center gap-2
          transition-all duration-200
          disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none
          ${variantStyles[variant]}
          ${sizeStyles[size]}
          ${fullWidth ? 'w-full' : ''}
          ${className}
        `}
        disabled={disabled || isLoading}
        {...props}
      >
        {isLoading && <Loader2 className="w-4 h-4 animate-spin" />}
        {children}
      </button>
    )
  }
)

Button.displayName = 'Button'
