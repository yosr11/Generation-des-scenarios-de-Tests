import React, { createContext, useCallback, useContext, useMemo, useState } from 'react'
import { CheckCircle, AlertCircle, Info, X } from 'lucide-react'

type ToastType = 'success' | 'error' | 'info'

interface Toast {
  id: string
  type: ToastType
  message: string
}

interface ToastContextValue {
  toast: (message: string, type?: ToastType) => void
  success: (message: string) => void
  error: (message: string) => void
  info: (message: string) => void
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined)

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<Toast[]>([])

  const remove = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const push = useCallback(
    (message: string, type: ToastType = 'info') => {
      const id = `${Date.now()}-${Math.random()}`
      setToasts((prev) => [...prev, { id, type, message }])
      setTimeout(() => remove(id), 4500)
    },
    [remove]
  )

  const value = useMemo(
    () => ({
      toast: push,
      success: (m: string) => push(m, 'success'),
      error: (m: string) => push(m, 'error'),
      info: (m: string) => push(m, 'info'),
    }),
    [push]
  )

  const icon = (type: ToastType) => {
    if (type === 'success') return <CheckCircle size={18} className="text-green-600" />
    if (type === 'error') return <AlertCircle size={18} className="text-brand-red" />
    return <Info size={18} className="text-brand-navy" />
  }

  const bg = (type: ToastType) => {
    if (type === 'success') return 'border-green-200 bg-green-50'
    if (type === 'error') return 'border-red-200 bg-red-50'
    return 'border-brand-navy/20 bg-white'
  }

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2 max-w-sm w-full pointer-events-none">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`pointer-events-auto flex items-start gap-3 rounded-lg border px-4 py-3 shadow-lg ${bg(t.type)}`}
          >
            {icon(t.type)}
            <p className="flex-1 text-sm text-brand-navy">{t.message}</p>
            <button
              type="button"
              onClick={() => remove(t.id)}
              className="text-gray-400 hover:text-brand-navy"
            >
              <X size={16} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within ToastProvider')
  return ctx
}
