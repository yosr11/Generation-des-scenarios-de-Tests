import React from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard,
  GitBranch,
  Search,
  History,
  LogOut,
  FolderKanban,
  ChevronRight,
} from 'lucide-react'
import { useAuth } from '../../contexts/AuthContext'

const navItems = [
  { to: '/pipeline',  label: 'Pipeline',   icon: GitBranch,      color: 'text-brand-rose' },
  { to: '/analysis',  label: 'Analyse',    icon: Search,         color: 'text-brand-orange' },
  { to: '/dashboard', label: 'Dashboard',  icon: LayoutDashboard, color: 'text-brand-violetlt' },
  { to: '/history',   label: 'Historique', icon: History,        color: 'text-brand-pinklt' },
]

export const Sidebar: React.FC = () => {
  const { user, selectedProject, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  const initials = (user?.display_name || user?.email || 'U')
    .split(' ')
    .map((w: string) => w[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()

  return (
    <aside
      className="w-64 min-h-screen flex flex-col shrink-0 relative overflow-hidden"
      style={{ background: 'var(--grad-sidebar)' }}
    >
      {/* Background orb */}
      <div
        className="absolute bottom-0 left-0 w-48 h-48 rounded-full pointer-events-none"
        style={{
          background: 'radial-gradient(circle, rgba(244,63,94,0.12) 0%, transparent 70%)',
          filter: 'blur(30px)',
        }}
      />
      <div
        className="absolute top-1/2 right-0 w-32 h-32 rounded-full pointer-events-none"
        style={{
          background: 'radial-gradient(circle, rgba(124,58,237,0.1) 0%, transparent 70%)',
          filter: 'blur(20px)',
        }}
      />

      {/* Logo */}
      <div className="relative z-10 px-5 py-5 border-b border-white/08">
        {/* Sopra HR logo */}
        <div className="flex items-center gap-3 mb-3">
          <img
            src="/logo_sopra.png"
            alt="Sopra HR"
            className="h-8 w-auto object-contain"
            style={{ filter: 'brightness(0) invert(1)', opacity: 0.9 }}
          />
          <div className="w-px h-6 bg-white/15" />
          <div>
            <h1 className="text-sm font-bold text-white leading-tight">
              Synap<span style={{ color: '#f43f5e' }}>test</span>
            </h1>
            <p className="text-[9px] text-white/35 leading-none">QA Platform</p>
          </div>
        </div>
        {/* Red accent bar */}
        <div className="h-0.5 rounded-full" style={{ background: 'linear-gradient(90deg,#ef4444,#f43f5e,transparent)' }} />
      </div>

      {/* Active Project badge */}
      {selectedProject && (
        <div className="relative z-10 mx-3 mt-4 px-3 py-2.5 rounded-xl flex items-center gap-2"
          style={{ background: 'rgba(244,63,94,0.12)', border: '1px solid rgba(244,63,94,0.2)' }}>
          <FolderKanban size={14} className="text-brand-rose flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-[10px] text-white/40 leading-none">Projet actif</p>
            <p className="text-xs font-bold text-white truncate mt-0.5">{selectedProject.key}</p>
          </div>
          <ChevronRight size={12} className="text-white/30" />
        </div>
      )}

      {/* Navigation */}
      <nav className="relative z-10 flex-1 px-3 py-4 space-y-1">
        <p className="text-[10px] font-bold text-white/25 uppercase tracking-widest px-2 mb-3">Navigation</p>

        {navItems.map(({ to, label, icon: Icon, color }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `nav-item ${isActive ? 'active' : ''}`
            }
          >
            {({ isActive }) => (
              <>
                <Icon
                  size={17}
                  className={isActive ? 'text-brand-rose' : `${color} opacity-70`}
                />
                <span className="flex-1">{label}</span>
                {isActive && (
                  <span className="w-1.5 h-1.5 rounded-full bg-brand-rose" />
                )}
              </>
            )}
          </NavLink>
        ))}

        {user?.role === 'tester' && (
          <NavLink
            to="/projects"
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            {({ isActive }) => (
              <>
                <FolderKanban size={17} className={isActive ? 'text-brand-rose' : 'text-brand-pinklt opacity-70'} />
                <span className="flex-1">Projets</span>
                {isActive && <span className="w-1.5 h-1.5 rounded-full bg-brand-rose" />}
              </>
            )}
          </NavLink>
        )}
      </nav>

      {/* User Section */}
      <div className="relative z-10 px-3 pb-4 border-t border-white/08 pt-4">
        <div className="flex items-center gap-3 px-2 mb-3">
          <div
            className="w-9 h-9 rounded-xl flex items-center justify-center text-white text-xs font-bold flex-shrink-0"
            style={{ background: 'var(--grad-violet)' }}
          >
            {initials}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-white truncate">
              {user?.display_name || user?.email || user?.jira_username}
            </p>
            <span
              className="inline-block text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full mt-0.5"
              style={{
                background: user?.role === 'admin' ? 'rgba(244,63,94,0.2)' : 'rgba(124,58,237,0.2)',
                color: user?.role === 'admin' ? '#fb7185' : '#a855f7',
                border: `1px solid ${user?.role === 'admin' ? 'rgba(244,63,94,0.3)' : 'rgba(124,58,237,0.3)'}`,
              }}
            >
              {user?.role}
            </span>
          </div>
        </div>

        <button
          type="button"
          onClick={handleLogout}
          className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl text-sm text-white/50 hover:text-brand-rose hover:bg-brand-rose/10 transition-all duration-200 group"
        >
          <LogOut size={15} className="group-hover:translate-x-0.5 transition-transform" />
          <span>Déconnexion</span>
        </button>
      </div>
    </aside>
  )
}
