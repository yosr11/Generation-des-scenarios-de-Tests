import React from 'react'

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode
  hover?: boolean
  variant?: 'default' | 'gradient' | 'dark'
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className = '', hover = false, variant = 'default', children, ...props }, ref) => {
    const variantClass = {
      default:  'bg-white border border-gray-100 shadow-card',
      gradient: 'bg-white border border-gray-100 shadow-card',
      dark:     'bg-brand-navy text-white border border-white/10',
    }[variant]

    return (
      <div
        ref={ref}
        className={`
          rounded-2xl
          ${variantClass}
          ${hover ? 'hover:shadow-elevated hover:-translate-y-1 transition-all duration-250 cursor-pointer' : ''}
          ${className}
        `}
        {...props}
      >
        {children}
      </div>
    )
  }
)

Card.displayName = 'Card'

interface CardHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string
  description?: string
  action?: React.ReactNode
  accent?: boolean
}

export const CardHeader = React.forwardRef<HTMLDivElement, CardHeaderProps>(
  ({ className = '', title, description, action, accent = false, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={`
          px-6 py-4 flex items-start justify-between gap-4
          ${accent
            ? 'border-b-2 border-transparent bg-gradient-to-r from-brand-violet/5 to-brand-rose/5 rounded-t-2xl'
            : 'border-b border-gray-100'
          }
          ${className}
        `}
        {...props}
      >
        <div className="flex-1 min-w-0">
          {title && (
            <h3 className="text-base font-bold text-brand-navy flex items-center gap-2">
              {accent && (
                <span className="w-2 h-2 rounded-full inline-block" style={{ background: 'var(--grad-cta)' }} />
              )}
              {title}
            </h3>
          )}
          {description && <p className="text-sm text-brand-muted mt-0.5">{description}</p>}
          {children && !title && children}
        </div>
        {action && <div className="flex-shrink-0">{action}</div>}
      </div>
    )
  }
)

CardHeader.displayName = 'CardHeader'

interface CardBodyProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode
}

export const CardBody = React.forwardRef<HTMLDivElement, CardBodyProps>(
  ({ className = '', children, ...props }, ref) => {
    return (
      <div ref={ref} className={`px-6 py-4 ${className}`} {...props}>
        {children}
      </div>
    )
  }
)

CardBody.displayName = 'CardBody'

interface CardFooterProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode
}

export const CardFooter = React.forwardRef<HTMLDivElement, CardFooterProps>(
  ({ className = '', children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={`
          px-6 py-4 border-t border-gray-100 flex gap-3 justify-end rounded-b-2xl
          bg-gray-50/50
          ${className}
        `}
        {...props}
      >
        {children}
      </div>
    )
  }
)

CardFooter.displayName = 'CardFooter'
