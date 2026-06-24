import React from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Bell, Search } from 'lucide-react'
import { useAuth } from '../../contexts/AuthContext'

const PAGE_TITLES: Record<string, { title: string; subtitle: string }> = {
  '/pipeline':  { title: 'Pipeline Orchestrator', subtitle: 'Générez vos tests avec les agents IA' },
  '/analysis':  { title: 'Analyse & Rapport', subtitle: 'Analyse détaillée et génération de rapports' },
  '/dashboard': { title: 'Dashboard', subtitle: 'Vue d\'ensemble et activité récente' },
  '/history':   { title: 'Historique', subtitle: 'Consultez les analyses passées' },
  '/projects':  { title: 'Projets Jira', subtitle: 'Sélectionnez votre projet' },
}

export const AppLayout: React.FC = () => {
  const location = useLocation()
  const { user } = useAuth()
  const meta = PAGE_TITLES[location.pathname] || { title: 'Synaptest', subtitle: '' }

  const initials = (user?.display_name || user?.email || 'U')
    .split(' ')
    .map((w: string) => w[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()

  return (
    <div className="flex min-h-screen bg-brand-bg">
      <Sidebar />

      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Header */}
        <header className="h-16 bg-white border-b border-gray-100 flex items-center px-6 gap-4 shrink-0 shadow-sm">
          {/* Page info */}
          <div className="flex-1">
            <h2 className="text-base font-bold text-brand-navy leading-tight">{meta.title}</h2>
            <p className="text-xs text-brand-muted leading-none mt-0.5">{meta.subtitle}</p>
          </div>

          {/* Search bar */}
          <div className="hidden md:flex items-center gap-2 px-4 py-2 bg-brand-bg rounded-xl border border-gray-100 w-64">
            <Search size={14} className="text-gray-400" />
            <input
              type="text"
              placeholder="Rechercher une story..."
              className="bg-transparent text-sm text-brand-navy placeholder:text-gray-400 outline-none w-full"
            />
          </div>

          {/* Notifications */}
          <button className="relative p-2.5 rounded-xl hover:bg-brand-bg transition-colors">
            <Bell size={18} className="text-brand-muted" />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-brand-rose rounded-full" />
          </button>

          {/* User Avatar */}
          <div className="flex items-center gap-3">
            <div
              className="w-9 h-9 rounded-xl flex items-center justify-center text-white text-xs font-bold"
              style={{ background: 'var(--grad-cta)' }}
            >
              {initials}
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 overflow-auto p-6 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
