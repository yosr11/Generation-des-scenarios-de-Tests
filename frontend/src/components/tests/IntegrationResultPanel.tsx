import React from 'react'
import { X, CheckCircle, AlertCircle, ExternalLink } from 'lucide-react'
import { Button } from '../ui/Button'
import { Badge } from '../ui/Badge'

export interface IntegrationResult {
  status: string
  created_count: number
  created_keys: string[]
  errors: string[]
  test_name?: string
}

interface IntegrationResultPanelProps {
  result: IntegrationResult
  onClose: () => void
}

export const IntegrationResultPanel: React.FC<IntegrationResultPanelProps> = ({
  result,
  onClose,
}) => {
  const isSuccess = result.status === 'success' && result.errors.length === 0
  const isPartial = result.status === 'partial' || (result.created_keys.length > 0 && result.errors.length > 0)

  return (
    <>
      <div className="fixed inset-0 bg-black/30 z-40" onClick={onClose} aria-hidden />
      <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-md bg-white rounded-xl shadow-2xl z-50 overflow-hidden">
        <div
          className={`px-5 py-4 flex items-center justify-between ${
            isSuccess ? 'bg-green-600' : isPartial ? 'bg-brand-orange' : 'bg-brand-red'
          } text-white`}
        >
          <div className="flex items-center gap-2">
            {isSuccess ? <CheckCircle size={20} /> : <AlertCircle size={20} />}
            <h3 className="font-semibold">Xray Integration Result</h3>
          </div>
          <button type="button" onClick={onClose} className="p-1 hover:bg-white/10 rounded">
            <X size={18} />
          </button>
        </div>

        <div className="p-5 space-y-4">
          {result.test_name && (
            <p className="text-sm text-gray-600">
              Test: <span className="font-medium text-brand-navy">{result.test_name}</span>
            </p>
          )}

          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-600">Status:</span>
            <Badge variant={isSuccess ? 'success' : isPartial ? 'warning' : 'error'}>
              {result.status}
            </Badge>
          </div>

          {result.created_keys.length > 0 && (
            <div>
              <p className="text-sm font-medium text-brand-navy mb-2">
                Created / linked keys ({result.created_count})
              </p>
              <ul className="space-y-1">
                {result.created_keys.map((key) => (
                  <li
                    key={key}
                    className="flex items-center gap-2 text-sm font-mono bg-brand-bg px-3 py-2 rounded-lg"
                  >
                    <ExternalLink size={14} className="text-brand-orange" />
                    {key}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {result.errors.length > 0 && (
            <div>
              <p className="text-sm font-medium text-brand-red mb-2">Errors</p>
              <ul className="space-y-1">
                {result.errors.map((err, idx) => (
                  <li key={idx} className="text-sm text-red-700 bg-red-50 px-3 py-2 rounded-lg">
                    {err}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <div className="px-5 py-4 border-t border-gray-200">
          <Button type="button" variant="primary" fullWidth onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </>
  )
}
