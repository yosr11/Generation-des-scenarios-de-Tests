import React, { useEffect, useMemo, useState } from 'react'
import { ChevronDown, FolderKanban, Search } from 'lucide-react'
import { useAuth, JiraProject } from '../../contexts/AuthContext'
import { apiClient } from '../../api/client'

interface ProjectPickerProps {
  value?: string
  onChange: (project: JiraProject) => void
  className?: string
  label?: string
  hint?: string
}

export const ProjectPicker: React.FC<ProjectPickerProps> = ({
  value,
  onChange,
  className = '',
  label = 'Projet Jira (intégration Xray)',
  hint = 'Utilisé uniquement pour exporter les tests vers Xray',
}) => {
  const { projects, selectedProject, setSelectedProject, setAuth, user } = useAuth()
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (user?.role !== 'tester' || projects.length) return
    const load = async () => {
      setLoading(true)
      try {
        const resp = await apiClient.auth.projects()
        if (resp.projects?.length && user) {
          setAuth(user, resp.projects)
        }
      } catch {
        /* projects stay empty */
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [user, projects.length, setAuth])

  const activeKey = value || selectedProject?.key

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    if (!q) return projects
    return projects.filter(
      (p) =>
        p.key.toLowerCase().includes(q) ||
        (p.name || '').toLowerCase().includes(q)
    )
  }, [projects, search])

  const activeProject =
    projects.find((p) => p.key === activeKey) || selectedProject || null

  const handleSelect = (project: JiraProject) => {
    setSelectedProject(project)
    onChange(project)
    setOpen(false)
    setSearch('')
  }

  return (
    <div className={`relative ${className}`}>
      <p className="syn-label mb-2">{label}</p>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-3 px-4 py-3 rounded-2xl border-2 border-brand-navy/[0.08] bg-white text-left transition-all hover:border-brand-violet/35 focus:outline-none focus:border-brand-violet focus:shadow-[0_0_0_3px_rgba(124,58,237,0.1)]"
      >
        <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 bg-grad-violet shadow-glow-violet">
          <FolderKanban size={16} className="text-white" />
        </div>
        <div className="flex-1 min-w-0">
          {loading ? (
            <p className="text-sm text-brand-muted">Chargement des projets…</p>
          ) : activeProject ? (
            <>
              <p className="text-sm font-bold text-brand-navy font-mono">{activeProject.key}</p>
              <p className="text-xs text-brand-muted truncate">{activeProject.name}</p>
            </>
          ) : (
            <p className="text-sm text-brand-muted">Sélectionner un projet Jira</p>
          )}
        </div>
        <ChevronDown
          size={16}
          className={`text-gray-400 transition-transform ${open ? 'rotate-180' : ''}`}
        />
      </button>
      {hint && (
        <p className="text-[11px] text-brand-muted mt-1.5 ml-1">{hint}</p>
      )}

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div
            className="absolute z-50 mt-2 w-full syn-surface rounded-2xl overflow-hidden shadow-elevated"
          >
            <div className="p-3 border-b border-gray-50">
              <div className="relative">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Rechercher un projet…"
                  className="w-full pl-9 pr-3 py-2.5 text-sm rounded-xl border border-gray-100 focus:border-brand-violet focus:outline-none"
                  autoFocus
                />
              </div>
            </div>
            <ul className="max-h-56 overflow-y-auto py-1">
              {filtered.length === 0 ? (
                <li className="px-4 py-6 text-center text-sm text-brand-muted">
                  {projects.length === 0
                    ? 'Aucun projet accessible'
                    : 'Aucun résultat'}
                </li>
              ) : (
                filtered.map((project) => (
                  <li key={project.key}>
                    <button
                      type="button"
                      onClick={() => handleSelect(project)}
                      className={`w-full px-4 py-3 text-left flex items-center gap-3 transition-colors hover:bg-brand-violet/5 ${
                        project.key === activeKey ? 'bg-brand-violet/8' : ''
                      }`}
                    >
                      <span className="text-sm font-bold font-mono text-brand-navy">
                        {project.key}
                      </span>
                      <span className="text-xs text-brand-muted truncate flex-1">
                        {project.name}
                      </span>
                    </button>
                  </li>
                ))
              )}
            </ul>
          </div>
        </>
      )}
    </div>
  )
}
