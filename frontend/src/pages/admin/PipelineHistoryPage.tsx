import React, { useEffect, useState, useCallback } from 'react'
import { apiClient } from '../../api/client'
import { useToast } from '../../contexts/ToastContext'
import { CheckCircle2, XCircle, RefreshCw, Filter, GitBranch, Clock, User } from 'lucide-react'

interface PipelineRun {
  id: number
  story_id: string
  launched_by: string
  status: string
  use_rag: boolean
  use_legacy_rag: boolean
  run_agent4: boolean
  started_at: string
  finished_at: string | null
  tests_count: number
  error_message: string | null
}

const STATUS_STYLE: Record<string, { bg: string; color: string; icon: React.ElementType }> = {
  completed: { bg: 'rgba(16,185,129,0.08)', color: '#10b981', icon: CheckCircle2 },
  failed:    { bg: 'rgba(244,63,94,0.08)',  color: '#f43f5e', icon: XCircle },
  running:   { bg: 'rgba(249,115,22,0.08)', color: '#f97316', icon: Clock },
}

export const PipelineHistoryPage: React.FC = () => {
  const toast = useToast()
  const [runs, setRuns] = useState<PipelineRun[]>([])
  const [loading, setLoading] = useState(true)
  const [filterUser, setFilterUser] = useState('')
  const [uniqueUsers, setUniqueUsers] = useState<string[]>([])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await apiClient.admin.getPipelineHistory({ limit: 200 })
      setRuns(data.runs || [])
      const users = [...new Set((data.runs || []).map((r: PipelineRun) => r.launched_by))] as string[]
      setUniqueUsers(users)
    } catch (err: any) {
      toast.error(err?.message || 'Erreur chargement')
    } finally {
      setLoading(false)
    }
  }, [toast])

  useEffect(() => { load() }, [load])

  const filtered = filterUser ? runs.filter(r => r.launched_by === filterUser) : runs

  const duration = (r: PipelineRun) => {
    if (!r.finished_at || !r.started_at) return null
    const ms = new Date(r.finished_at).getTime() - new Date(r.started_at).getTime()
    const s = Math.round(ms / 1000)
    return s < 60 ? `${s}s` : `${Math.round(s / 60)}min ${s % 60}s`
  }

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Filters */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 px-4 py-2.5 rounded-xl border-2 border-gray-100 bg-white">
          <Filter size={14} className="text-gray-400" />
          <select
            value={filterUser}
            onChange={e => setFilterUser(e.target.value)}
            className="text-sm text-brand-navy bg-transparent outline-none"
          >
            <option value="">Tous les utilisateurs</option>
            {uniqueUsers.map(u => <option key={u} value={u}>{u}</option>)}
          </select>
        </div>
        <button type="button" onClick={load} disabled={loading}
          className="p-2.5 rounded-xl border-2 border-gray-100 text-brand-muted hover:text-brand-navy hover:border-gray-200 transition-all">
          <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
        </button>
        <div className="ml-auto text-sm text-brand-muted">
          <span className="font-bold text-brand-navy">{filtered.length}</span> pipeline(s)
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-3xl border border-gray-100 shadow-card overflow-hidden">
        <div className="h-1" style={{ background: 'linear-gradient(90deg,#ef4444,#7c3aed,#f97316)' }} />
        <div className="px-6 py-4 border-b border-gray-100 flex items-center gap-3">
          <GitBranch size={16} className="text-brand-rose" />
          <h3 className="font-bold text-brand-navy">Historique des Pipelines</h3>
        </div>

        {loading ? (
          <div className="py-16 text-center">
            <div className="w-8 h-8 mx-auto border-2 border-t-brand-rose border-transparent rounded-full animate-spin mb-3" />
            <p className="text-brand-muted text-sm">Chargement…</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="py-16 text-center text-brand-muted text-sm">Aucun pipeline trouvé.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50/60">
                  {['Story ID', 'Lancé par', 'Statut', 'Tests', 'Durée', 'Options', 'Date'].map(h => (
                    <th key={h} className="text-left py-3 px-4 text-[10px] font-bold text-brand-navy/50 uppercase tracking-widest">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map(run => {
                  const st = STATUS_STYLE[run.status] || STATUS_STYLE.failed
                  const Icon = st.icon
                  return (
                    <tr key={run.id} className="border-b border-gray-50 hover:bg-gray-50/60 transition-colors">
                      <td className="py-3.5 px-4">
                        <span className="font-mono font-bold text-brand-navy text-xs px-2 py-1 rounded-lg"
                          style={{ background: 'rgba(244,63,94,0.08)', color: '#f43f5e' }}>
                          {run.story_id}
                        </span>
                      </td>
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-2">
                          <User size={13} className="text-brand-muted flex-shrink-0" />
                          <span className="text-brand-navy font-medium">{run.launched_by}</span>
                        </div>
                      </td>
                      <td className="py-3.5 px-4">
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase"
                          style={{ background: st.bg, color: st.color }}>
                          <Icon size={10} />
                          {run.status}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 font-semibold text-brand-navy">{run.tests_count}</td>
                      <td className="py-3.5 px-4 text-brand-muted text-xs">{duration(run) || '—'}</td>
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-1">
                          {run.use_rag && (
                            <span className="px-1.5 py-0.5 rounded text-[9px] font-bold uppercase"
                              style={{ background: 'rgba(124,58,237,0.08)', color: '#7c3aed' }}>RAG</span>
                          )}
                          {run.run_agent4 && (
                            <span className="px-1.5 py-0.5 rounded text-[9px] font-bold uppercase"
                              style={{ background: 'rgba(249,115,22,0.08)', color: '#f97316' }}>A4</span>
                          )}
                        </div>
                      </td>
                      <td className="py-3.5 px-4 text-xs text-brand-muted">
                        {run.started_at
                          ? new Date(run.started_at).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })
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
