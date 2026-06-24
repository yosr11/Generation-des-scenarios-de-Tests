import React from 'react'

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  helpText?: string
  icon?: React.ReactNode
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className = '', label, error, helpText, icon, ...props }, ref) => {
    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label className="text-sm font-medium text-slate-700">
            {label}
            {props.required && <span className="text-red-500">*</span>}
          </label>
        )}
        <div className="relative">
          {icon && <div className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">{icon}</div>}
          <input
            ref={ref}
            className={`
              w-full px-4 py-2.5 rounded-lg border border-slate-300 bg-white
              text-slate-900 placeholder-slate-400 text-base
              transition-all duration-200
              focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
              disabled:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50
              ${icon ? 'pl-10' : ''}
              ${error ? 'border-red-500 focus:ring-red-500' : ''}
              ${className}
            `}
            {...props}
          />
        </div>
        {error && <p className="text-sm text-red-600 font-medium">{error}</p>}
        {helpText && !error && <p className="text-sm text-slate-500">{helpText}</p>}
      </div>
    )
  }
)

Input.displayName = 'Input'

interface TextAreaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string
  error?: string
  helpText?: string
}

export const TextArea = React.forwardRef<HTMLTextAreaElement, TextAreaProps>(
  ({ className = '', label, error, helpText, ...props }, ref) => {
    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label className="text-sm font-medium text-slate-700">
            {label}
            {props.required && <span className="text-red-500">*</span>}
          </label>
        )}
        <textarea
          ref={ref}
          className={`
            w-full px-4 py-2.5 rounded-lg border border-slate-300 bg-white
            text-slate-900 placeholder-slate-400 text-base font-sans
            transition-all duration-200 resize-none
            focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
            disabled:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50
            ${error ? 'border-red-500 focus:ring-red-500' : ''}
            ${className}
          `}
          {...props}
        />
        {error && <p className="text-sm text-red-600 font-medium">{error}</p>}
        {helpText && !error && <p className="text-sm text-slate-500">{helpText}</p>}
      </div>
    )
  }
)

TextArea.displayName = 'TextArea'

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string
  error?: string
  helpText?: string
  options: Array<{ label: string; value: string | number }>
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className = '', label, error, helpText, options, ...props }, ref) => {
    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label className="text-sm font-medium text-slate-700">
            {label}
            {props.required && <span className="text-red-500">*</span>}
          </label>
        )}
        <select
          ref={ref}
          className={`
            w-full px-4 py-2.5 rounded-lg border border-slate-300 bg-white
            text-slate-900 text-base appearance-none cursor-pointer
            transition-all duration-200
            focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
            disabled:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50
            ${error ? 'border-red-500 focus:ring-red-500' : ''}
            ${className}
          `}
          {...props}
        >
          <option value="">Select an option...</option>
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        {error && <p className="text-sm text-red-600 font-medium">{error}</p>}
        {helpText && !error && <p className="text-sm text-slate-500">{helpText}</p>}
      </div>
    )
  }
)

Select.displayName = 'Select'
