import React, { useEffect, useState } from 'react'
import { apiClient } from '../../api/client'
import { Users, Activity } from 'lucide-react'

interface Stats {
  total_users: number
  active_users: number
  tester_count: number
  admin_count: number
  total_pipelines?: number
  successful_pipelines?: number
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
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiClient.admin.getStats()
      .then((s) => setStats(s))
      .catch(console.error)
      .finally(() => setLoading(false))
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

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Stats grid */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        <StatCard label="Utilisateurs actifs" value={stats?.active_users ?? 0}
          icon={Users} color="#f43f5e" bg="rgba(244,63,94,0.08)" border="rgba(244,63,94,0.2)" />
        <StatCard label="Ingénieurs QA" value={stats?.tester_count ?? 0}
          icon={Activity} color="#f97316" bg="rgba(249,115,22,0.08)" border="rgba(249,115,22,0.2)" />
        <StatCard label="Administrateurs" value={stats?.admin_count ?? 0}
          icon={Users} color="#6366f1" bg="rgba(99,102,241,0.08)" border="rgba(99,102,241,0.2)" />
        <StatCard label="Pipelines (total)" value={stats?.total_pipelines ?? 0}
          icon={Activity} color="#10b981" bg="rgba(16,185,129,0.08)" border="rgba(16,185,129,0.2)" />
      </div>

      {/* Recent pipelines */}
      <div className="bg-white rounded-3xl border border-gray-100 shadow-card overflow-hidden">
        <div className="h-1" style={{ background: 'linear-gradient(90deg,#ef4444,#f43f5e,#7c3aed)' }} />
        <div className="px-6 py-6 text-center">
          <h3 className="font-bold text-brand-navy">Activité des utilisateurs</h3>
          <p className="text-sm text-brand-muted mt-2">Consultez l'historique détaillé des pipelines sur la page <a href="/admin/pipelines" className="text-brand-rose underline">Historique des Pipelines</a>.</p>
        </div>
      </div>
    </div>
  )
}
