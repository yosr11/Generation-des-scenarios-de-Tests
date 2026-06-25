import React, { useEffect, useState, useCallback } from 'react'
import { apiClient } from '../../api/client'
import { useToast } from '../../contexts/ToastContext'
import { ClipboardList, RefreshCw, LogIn, LogOut, Plus, Pencil, Trash2, Activity } from 'lucide-react'

interface AuditLog {
  id: number
  user_identifier: string
  role: string
  action: string
  resource: string | null
  details: string | null
  ip_address: string | null
  created_at: string
}

const ACTION_STYLE: Record<string, { bg: string; color: string; icon: React.ElementType }> = {
  login:   { bg: 'rgba(16,185,129,0.08)',  color: '#10b981', icon: LogIn },
  logout:  { bg: 'rgba(100,116,139,0.08)', color: '#64748b', icon: LogOut },
  create:  { bg: 'rgba(124,58,237,0.08)',  color: '#7c3aed', icon: Plus },
  update:  { bg: 'rgba(249,115,22,0.08)',  color: '#f97316', icon: Pencil },
  delete:  { bg: 'rgba(244,63,94,0.08)',   color: '#f43f5e', icon: Trash2 },
  pipeline:{ bg: 'rgba(236,72,153,0.08)',  color: '#ec4899', icon: Activity },
}

const getActionStyle = (action: string) =>
  ACTION_STYLE[action.toLowerCase()] || { bg: 'rgba(100,116,139,0.08)', color: '#64748b', icon: Activity }

export const AuditPage: React.FC = () => {
  const toast = useToast()
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await apiClient.admin.getAuditLog({ limit: 200 })
      setLogs(data.logs || [])
    } catch (err: any) {
      toast.error(err?.message || 'Erreur chargement')
    } finally {
      setLoading(false)
    }
  }, [toast])

  useEffect(() => { load() }, [load])

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Header */}
      <div className="flex items-center gap-3">
        <p className="text-sm text-brand-muted ml-auto">
          <span className="font-bold text-brand-navy">{logs.length}</span> entrées
        </p>
        <button type="button" onClick={load} disabled={loading}
          className="p-2.5 rounded-xl border-2 border-gray-100 text-brand-muted hover:text-brand-navy hover:border-gray-200 transition-all">
          <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      {/* Table */}
      <div className="bg-white rounded-3xl border border-gray-100 shadow-card overflow-hidden">
        <div className="h-1" style={{ background: 'linear-gradient(90deg,#ef4444,#f43f5e,#ec4899,#7c3aed)' }} />
        <div className="px-6 py-4 border-b border-gray-100 flex items-center gap-3">
          <ClipboardList size={16} className="text-brand-rose" />
          <h3 className="font-bold text-brand-navy">Journal d'Audit</h3>
          <span className="ml-auto text-xs text-brand-muted">Dernières 200 actions</span>
        </div>

        {loading ? (
          <div className="py-16 text-center">
            <div className="w-8 h-8 mx-auto border-2 border-t-brand-rose border-transparent rounded-full animate-spin mb-3" />
            <p className="text-brand-muted text-sm">Chargement…</p>
          </div>
        ) : logs.length === 0 ? (
          <div className="py-16 text-center text-brand-muted text-sm">Aucun log d'audit.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50/60">
                  {['Utilisateur', 'Rôle', 'Action', 'Ressource', 'Détails', 'IP', 'Date'].map(h => (
                    <th key={h} className="text-left py-3 px-4 text-[10px] font-bold text-brand-navy/50 uppercase tracking-widest">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {logs.map(log => {
                  const st = getActionStyle(log.action)
                  const Icon = st.icon
                  return (
                    <tr key={log.id} className="border-b border-gray-50 hover:bg-gray-50/60 transition-colors">
                      <td className="py-3 px-4 font-semibold text-brand-navy">{log.user_identifier}</td>
                      <td className="py-3 px-4">
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase"
                          style={{
                            background: log.role === 'admin' ? 'rgba(244,63,94,0.08)' : 'rgba(124,58,237,0.08)',
                            color: log.role === 'admin' ? '#f43f5e' : '#7c3aed',
                          }}>
                          {log.role}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase"
                          style={{ background: st.bg, color: st.color }}>
                          <Icon size={10} />
                          {log.action}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-brand-muted text-xs">{log.resource || '—'}</td>
                      <td className="py-3 px-4 text-brand-muted text-xs max-w-[200px] truncate" title={log.details || ''}>
                        {log.details || '—'}
                      </td>
                      <td className="py-3 px-4 text-brand-muted text-xs font-mono">{log.ip_address || '—'}</td>
                      <td className="py-3 px-4 text-brand-muted text-xs whitespace-nowrap">
                        {log.created_at
                          ? new Date(log.created_at).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })
                          : '—'}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
