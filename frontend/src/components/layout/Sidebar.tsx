import React from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard,
  GitBranch,
  Search,
  History,
  LogOut,
  FolderKanban,
} from 'lucide-react'
import { useAuth } from '../../contexts/AuthContext'

const navItems = [
  { to: '/pipeline', label: 'Pipeline', icon: GitBranch },
  { to: '/analysis', label: 'Analysis', icon: Search },
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/history', label: 'History', icon: History },
]

export const Sidebar: React.FC = () => {
  const { user, selectedProject, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  return (
    <aside className="w-64 min-h-screen bg-brand-navy text-white flex flex-col shrink-0">
      <div className="px-6 py-5 border-b border-white/10">
        <h1 className="text-lg font-bold tracking-tight">Agent Test</h1>
        <p className="text-xs text-white/60 mt-1">Sopra HR — QA Platform</p>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-white/15 text-white'
                  : 'text-white/75 hover:bg-white/10 hover:text-white'
              }`
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}

        {user?.role === 'tester' && (
          <NavLink
            to="/projects"
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-white/15 text-white'
                  : 'text-white/75 hover:bg-white/10 hover:text-white'
              }`
            }
          >
            <FolderKanban size={18} />
            Projects
          </NavLink>
        )}
      </nav>

      <div className="px-4 py-4 border-t border-white/10">
        {selectedProject && (
          <div className="mb-3 px-3 py-2 rounded-lg bg-white/10 text-xs">
            <span className="text-white/60 block">Active project</span>
            <span className="font-semibold">{selectedProject.key}</span>
          </div>
        )}
        <div className="px-3 mb-3">
          <p className="text-xs text-white/60">Signed in as</p>
          <p className="text-sm font-medium truncate">
            {user?.display_name || user?.email || user?.jira_username}
          </p>
          <span className="inline-block mt-1 text-[10px] uppercase tracking-wide bg-brand-orange/90 text-white px-2 py-0.5 rounded">
            {user?.role}
          </span>
        </div>
        <button
          type="button"
          onClick={handleLogout}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm text-white/80 hover:bg-white/10 hover:text-white transition-colors"
        >
          <LogOut size={16} />
          Sign out
        </button>
      </div>
    </aside>
  )
}
