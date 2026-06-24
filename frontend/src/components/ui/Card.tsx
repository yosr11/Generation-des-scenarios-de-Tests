import React from 'react'

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode
  hover?: boolean
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className = '', hover = false, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={`
          rounded-xl bg-white border border-slate-200 shadow-sm
          ${hover ? 'hover:shadow-md hover:border-slate-300 transition-all duration-200' : ''}
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
}

export const CardHeader = React.forwardRef<HTMLDivElement, CardHeaderProps>(
  ({ className = '', title, description, action, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={`
          px-6 py-4 border-b border-slate-100 flex items-start justify-between gap-4
          ${className}
        `}
        {...props}
      >
        <div className="flex-1">
          {title && <h3 className="text-lg font-semibold text-slate-900">{title}</h3>}
          {description && <p className="text-sm text-slate-500 mt-1">{description}</p>}
          {children && !title && children}
        </div>
        {action}
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
          px-6 py-4 border-t border-slate-100 flex gap-3 justify-end
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
