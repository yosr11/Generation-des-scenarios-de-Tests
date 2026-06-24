import React from 'react'

interface PageContainerProps {
  children: React.ReactNode
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | '2xl' | 'full'
  className?: string
}

const maxWidthClasses = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-xl',
  '2xl': 'max-w-2xl',
  full: 'max-w-full',
}

export const PageContainer: React.FC<PageContainerProps> = ({
  children,
  maxWidth = '2xl',
  className = '',
}) => {
  return (
    <div className={`${maxWidthClasses[maxWidth]} mx-auto px-4 sm:px-6 lg:px-8 py-8 ${className}`}>
      {children}
    </div>
  )
}

interface PageHeaderProps {
  title: string
  description?: string
  action?: React.ReactNode
}

export const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  description,
  action,
}) => {
  return (
    <div className="flex items-start justify-between gap-4 mb-8">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">{title}</h1>
        {description && <p className="text-slate-600 mt-2">{description}</p>}
      </div>
      {action}
    </div>
  )
}

interface PageSectionProps {
  title?: string
  description?: string
  children: React.ReactNode
  action?: React.ReactNode
}

export const PageSection: React.FC<PageSectionProps> = ({
  title,
  description,
  children,
  action,
}) => {
  return (
    <div className="mb-8">
      {(title || description || action) && (
        <div className="flex items-start justify-between gap-4 mb-4">
          <div>
            {title && <h2 className="text-xl font-semibold text-slate-900">{title}</h2>}
            {description && <p className="text-sm text-slate-600 mt-1">{description}</p>}
          </div>
          {action}
        </div>
      )}
      {children}
    </div>
  )
}
