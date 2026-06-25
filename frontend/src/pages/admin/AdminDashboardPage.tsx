import React, { useEffect, useState } from 'react'
import { apiClient } from '../../api/client'
import { Users, BarChart3, CheckCircle2, XCircle, Activity, GitBranch, Clock } from 'lucide-react'

interface Stats {
  total_users: number
  active_users: number
  tester_count: number
  admin_count: number
  total_pipelines: number
  successful_pipelines: number
}

interface RecentRun {
  id: number
  story_id: string
  launched_by: string
  status: string
  started_at: string
  tests_count: number
}

const StatCard: React.FC<{
  label: string; value: number | string; icon: React.ElementType
  color: string; bg: string; border: string
}> = ({ label, value, icon: Icon, color, bg, border }) => (
  <div className="bg-white rounded-2xl p-5 border border-gray-100 shadow-sm flex items-center gap-4">
    <div className="w-12 h-12 rounded-2xl flex items-center justify-center flex-shrink-0"
      style={{ background: bg, border: `1px solid ${border}` }}>
      <Icon size={22} style={{ color }} />
    </div>
    <div>
      <p className="text-2xl font-extrabold text-brand-navy">{value}</p>
      <p className="text-sm text-brand-muted">{label}</p>
    </div>
  </div>
)

export const AdminDashboardPage: React.FC = () => {
  const [stats, setStats] = useState<Stats | null>(null)
  const [recentRuns, setRecentRuns] = useState<RecentRun[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      apiClient.admin.getStats(),
      apiClient.admin.getPipelineHistory({ limit: 8 }),
    ]).then(([s, h]) => {
      setStats(s)
      setRecentRuns(h.runs || [])
    }).catch(console.error).finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <div className="text-center">
          <div className="w-12 h-12 mx-auto mb-4 rounded-full border-2 border-t-brand-rose border-transparent animate-spin" />
          <p className="text-brand-muted text-sm">Chargement du tableau de bord…</p>
        </div>
      </div>
    )
  }

  const successRate = stats && stats.total_pipelines > 0
    ? Math.round((stats.successful_pipelines / stats.total_pipelines) * 100)
    : 0

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Stats grid */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        <StatCard label="Utilisateurs actifs" value={stats?.active_users ?? 0}
          icon={Users} color="#f43f5e" bg="rgba(244,63,94,0.08)" border="rgba(244,63,94,0.2)" />
        <StatCard label="Testeurs" value={stats?.tester_count ?? 0}
          icon={Activity} color="#f97316" bg="rgba(249,115,22,0.08)" border="rgba(249,115,22,0.2)" />
        <StatCard label="Pipelines lancés" value={stats?.total_pipelines ?? 0}
          icon={GitBranch} color="#7c3aed" bg="rgba(124,58,237,0.08)" border="rgba(124,58,237,0.2)" />
        <StatCard label="Succès" value={stats?.successful_pipelines ?? 0}
          icon={CheckCircle2} color="#10b981" bg="rgba(16,185,129,0.08)" border="rgba(16,185,129,0.2)" />
        <StatCard label="Taux de succès" value={`${successRate}%`}
          icon={BarChart3} color="#ec4899" bg="rgba(236,72,153,0.08)" border="rgba(236,72,153,0.2)" />
        <StatCard label="Administrateurs" value={stats?.admin_count ?? 0}
          icon={Users} color="#6366f1" bg="rgba(99,102,241,0.08)" border="rgba(99,102,241,0.2)" />
      </div>

      {/* Recent pipelines */}
      <div className="bg-white rounded-3xl border border-gray-100 shadow-card overflow-hidden">
        <div className="h-1" style={{ background: 'linear-gradient(90deg,#ef4444,#f43f5e,#7c3aed)' }} />
        <div className="px-6 py-4 border-b border-gray-100 flex items-center gap-3">
          <Clock size={16} className="text-brand-rose" />
          <h3 className="font-bold text-brand-navy">Derniers Pipelines</h3>
        </div>
        {recentRuns.length === 0 ? (
          <div className="py-12 text-center text-brand-muted text-sm">Aucun pipeline lancé</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50/60">
                  {['Story ID', 'Lancé par', 'Statut', 'Tests', 'Date'].map(h => (
                    <th key={h} className="text-left py-3 px-4 text-[10px] font-bold text-brand-navy/50 uppercase tracking-widest">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {recentRuns.map(run => (
                  <tr key={run.id} className="border-b border-gray-50 hover:bg-gray-50/60 transition-colors">
                    <td className="py-3 px-4 font-mono font-bold text-brand-navy text-xs">{run.story_id}</td>
                    <td className="py-3 px-4 text-brand-navy">{run.launched_by}</td>
                    <td className="py-3 px-4">
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase"
                        style={{
                          background: run.status === 'completed' ? 'rgba(16,185,129,0.08)' : run.status === 'failed' ? 'rgba(244,63,94,0.08)' : 'rgba(249,115,22,0.08)',
                          color: run.status === 'completed' ? '#10b981' : run.status === 'failed' ? '#f43f5e' : '#f97316',
                        }}>
                        {run.status === 'completed' ? <CheckCircle2 size={10} /> : <XCircle size={10} />}
                        {run.status}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-brand-muted font-semibold">{run.tests_count}</td>
                    <td className="py-3 px-4 text-brand-muted text-xs">
                      {run.started_at ? new Date(run.started_at).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' }) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
