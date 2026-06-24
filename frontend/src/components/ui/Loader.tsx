import React from 'react'

interface LoaderProps {
  size?: 'sm' | 'md' | 'lg'
  text?: string
}

export const Loader: React.FC<LoaderProps> = ({ size = 'md', text }) => {
  const ringSize = { sm: 'w-8 h-8', md: 'w-12 h-12', lg: 'w-16 h-16' }[size]
  const innerSize = { sm: 'w-5 h-5', md: 'w-8 h-8', lg: 'w-10 h-10' }[size]

  return (
    <div className="flex flex-col items-center justify-center gap-3">
      <div className={`relative ${ringSize}`}>
        {/* Outer ring */}
        <div className={`absolute inset-0 rounded-full border-2 border-brand-violet/15`} />
        {/* Spinning gradient ring */}
        <div
          className={`absolute inset-0 rounded-full border-2 border-transparent animate-spin`}
          style={{
            borderTopColor: '#f43f5e',
            borderRightColor: 'transparent',
            borderBottomColor: 'transparent',
            borderLeftColor: 'transparent',
          }}
        />
        {/* Inner ring reverse */}
        <div
          className={`absolute inset-[4px] rounded-full border-2 border-transparent animate-spin`}
          style={{
            borderTopColor: '#f97316',
            animationDirection: 'reverse',
            animationDuration: '0.7s',
          }}
        />
      </div>
      {text && (
        <p className="text-sm font-medium text-brand-muted animate-pulse">{text}</p>
      )}
    </div>
  )
}

export const SkeletonLoader: React.FC<{ lines?: number }> = ({ lines = 3 }) => {
  return (
    <div className="space-y-3 animate-pulse">
      {[...Array(lines)].map((_, i) => (
        <div key={i} className="space-y-2">
          <div
            className="h-3.5 rounded-full"
            style={{
              width: `${75 - i * 12}%`,
              background: 'linear-gradient(90deg, #f1f5f9, #e2e8f0, #f1f5f9)',
              backgroundSize: '200% auto',
              animation: 'shimmer 1.5s linear infinite',
            }}
          />
          <div
            className="h-3 rounded-full"
            style={{
              width: `${55 - i * 8}%`,
              background: 'linear-gradient(90deg, #f1f5f9, #e2e8f0, #f1f5f9)',
              backgroundSize: '200% auto',
              animation: `shimmer 1.5s linear infinite`,
              animationDelay: `${i * 0.15}s`,
            }}
          />
        </div>
      ))}
    </div>
  )
}
