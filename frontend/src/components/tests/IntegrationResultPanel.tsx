import React from 'react'
import { X, CheckCircle2, AlertCircle, ExternalLink, Upload } from 'lucide-react'
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

  const headerGrad = isSuccess
    ? 'linear-gradient(135deg, #10b981, #14b8a6)'
    : isPartial
    ? 'linear-gradient(135deg, #f97316, #fbbf24)'
    : 'linear-gradient(135deg, #f43f5e, #ef4444)'

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-brand-navy/40 z-40 backdrop-blur-sm animate-fade-in"
        onClick={onClose}
        aria-hidden
      />

      {/* Modal */}
      <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-md z-50 animate-scale-in">
        <div className="bg-white rounded-3xl shadow-float overflow-hidden">

          {/* Header */}
          <div
            className="px-6 py-5 flex items-center gap-3"
            style={{ background: headerGrad }}
          >
            <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 bg-white/20">
              {isSuccess
                ? <CheckCircle2 size={20} className="text-white" />
                : <AlertCircle size={20} className="text-white" />
              }
            </div>
            <div className="flex-1">
              <h3 className="font-bold text-white">Résultat Xray</h3>
              {result.test_name && (
                <p className="text-xs text-white/70 mt-0.5 truncate">{result.test_name}</p>
              )}
            </div>
            <button
              type="button"
              onClick={onClose}
              className="p-2 rounded-xl text-white/60 hover:text-white hover:bg-white/10 transition-all"
            >
              <X size={16} />
            </button>
          </div>

          {/* Body */}
          <div className="p-5 space-y-4">

            {/* Status */}
            <div className="flex items-center gap-3 p-3 rounded-xl bg-gray-50">
              <span className="text-sm text-brand-muted">Statut :</span>
              <Badge
                variant={isSuccess ? 'success' : isPartial ? 'warning' : 'error'}
                dot
              >
                {result.status}
              </Badge>
              {result.created_count > 0 && (
                <span className="ml-auto text-sm font-bold text-brand-navy">
                  {result.created_count} créé(s)
                </span>
              )}
            </div>

            {/* Created Keys */}
            {result.created_keys.length > 0 && (
              <div>
                <p className="text-xs font-bold text-brand-navy uppercase tracking-widest mb-2">
                  Clés créées / liées
                </p>
                <ul className="space-y-2">
                  {result.created_keys.map((key) => (
                    <li
                      key={key}
                      className="flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-mono font-semibold"
                      style={{
                        background: 'rgba(16,185,129,0.06)',
                        border: '1px solid rgba(16,185,129,0.2)',
                        color: '#065f46',
                      }}
                    >
                      <ExternalLink size={13} className="text-emerald-500 flex-shrink-0" />
                      {key}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Errors */}
            {result.errors.length > 0 && (
              <div>
                <p className="text-xs font-bold text-brand-rose uppercase tracking-widest mb-2">Erreurs</p>
                <ul className="space-y-2">
                  {result.errors.map((err, idx) => (
                    <li
                      key={idx}
                      className="px-4 py-2.5 rounded-xl text-sm"
                      style={{
                        background: 'rgba(244,63,94,0.06)',
                        border: '1px solid rgba(244,63,94,0.2)',
                        color: '#be123c',
                      }}
                    >
                      {err}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="px-5 pb-5">
            <Button type="button" variant="primary" fullWidth onClick={onClose}>
              <Upload size={14} />
              Fermer
            </Button>
          </div>
        </div>
      </div>
    </>
  )
}
