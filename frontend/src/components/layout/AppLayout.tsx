import React, { useState, useRef, useEffect } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Bell, LogOut, User, ChevronDown, Settings } from 'lucide-react'
import { useAuth } from '../../contexts/AuthContext'

const PAGE_TITLES: Record<string, { title: string; subtitle: string }> = {
  '/pipeline':          { title: 'Pipeline IA', subtitle: 'Générez vos tests depuis vos user stories Jira' },
  '/history':           { title: 'Historique', subtitle: 'Stories déjà traitées' },
  '/projects':          { title: 'Mes projets Jira', subtitle: 'Projets accessibles — utilisés pour l\'intégration Xray' },
  '/admin/dashboard':   { title: 'Dashboard Admin', subtitle: 'Vue d\'ensemble de la plateforme' },
  '/admin/users':       { title: 'Gestion Utilisateurs', subtitle: 'Créer, modifier, activer/désactiver les comptes' },
  '/admin/pipelines':   { title: 'Historique Pipelines', subtitle: 'Qui a lancé quoi, quand et avec quel résultat' },
  '/admin/audit':       { title: 'Journal d\'Audit', subtitle: 'Traçabilité complète des actions utilisateurs' },
}

export const AppLayout: React.FC = () => {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  const meta = PAGE_TITLES[location.pathname] || { title: 'Synaptest', subtitle: '' }

  const initials = (user?.display_name || user?.email || 'U')
    .split(' ').map((w: string) => w[0]).slice(0, 2).join('').toUpperCase()

  const isAdmin = user?.role === 'admin'

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const handleLogout = async () => {
    setDropdownOpen(false)
    await logout()
    navigate('/login')
  }

  return (
    <div className="flex min-h-screen bg-brand-bg">
      <Sidebar />

      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Header */}
        <header className="h-16 bg-white border-b border-gray-100 flex items-center px-6 gap-4 shrink-0 shadow-sm">
          {/* Page info */}
          <div className="flex-1 min-w-0">
            <h2 className="text-base font-bold text-brand-navy leading-tight">{meta.title}</h2>
            {meta.subtitle && (
              <p className="text-xs text-brand-muted leading-none mt-0.5">{meta.subtitle}</p>
            )}
          </div>

          {/* Role badge */}
          {isAdmin && (
            <div className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold"
              style={{ background: 'rgba(244,63,94,0.08)', border: '1px solid rgba(244,63,94,0.2)', color: '#f43f5e' }}>
              👑 Administrateur
            </div>
          )}

          {/* Profile Dropdown */}
          <div ref={dropdownRef} className="relative">
            <button
              type="button"
              onClick={() => setDropdownOpen(!dropdownOpen)}
              className="flex items-center gap-2.5 px-3 py-2 rounded-xl hover:bg-gray-50 transition-all group"
            >
              <div
                className="w-9 h-9 rounded-xl flex items-center justify-center text-white text-xs font-bold flex-shrink-0"
                style={{
                  background: 'linear-gradient(135deg, #ef4444, #f43f5e, #f97316)',
                  boxShadow: '0 6px 24px rgba(244,63,94,0.4)'
                }}
              >
                {initials}
              </div>
              <div className="hidden md:block text-left">
                <p className="text-sm font-semibold text-brand-navy leading-tight">
                  {user?.display_name || user?.email || user?.jira_username}
                </p>
                <p className="text-[10px] text-brand-muted capitalize">{user?.role}</p>
              </div>
              <ChevronDown
                size={14}
                className={`text-brand-muted transition-transform duration-200 ${dropdownOpen ? 'rotate-180' : ''}`}
              />
            </button>

            {/* Dropdown menu */}
            {dropdownOpen && (
              <div
                className="absolute right-0 top-full mt-2 w-56 bg-white rounded-2xl border border-gray-100 shadow-float z-50 overflow-hidden animate-scale-in"
              >
                {/* User info */}
                <div className="px-4 py-3 border-b border-gray-100"
                  style={{ background: isAdmin ? 'linear-gradient(135deg,rgba(244,63,94,0.04),rgba(249,115,22,0.02))' : 'rgba(124,58,237,0.03)' }}>
                  <p className="text-sm font-bold text-brand-navy">
                    {user?.display_name || user?.email || user?.jira_username}
                  </p>
                  <p className="text-xs text-brand-muted mt-0.5">{user?.email || user?.jira_username}</p>
                  <span className="inline-block mt-1.5 text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full"
                    style={{
                      background: isAdmin ? 'rgba(244,63,94,0.1)' : 'rgba(124,58,237,0.1)',
                      color: isAdmin ? '#f43f5e' : '#7c3aed',
                    }}>
                    {user?.role}
                  </span>
                </div>

                {/* Menu items */}
                <div className="p-2">
                  <button type="button"
                    onClick={() => { setDropdownOpen(false) }}
                    className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-brand-navy hover:bg-gray-50 transition-colors">
                    <User size={15} className="text-brand-muted" />
                    Mon profil
                  </button>

                  <div className="my-1 h-px bg-gray-100" />

                  {/* LOGOUT — prominent */}
                  <button
                    type="button"
                    onClick={handleLogout}
                    className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-semibold text-brand-rose hover:bg-brand-rose/06 transition-colors group"
                  >
                    <LogOut size={15} className="group-hover:translate-x-0.5 transition-transform" />
                    Se déconnecter
                  </button>
                </div>
              </div>
            )}
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
