import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FolderOpen, FolderKanban, ChevronRight, Layers, Sparkles } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import { apiClient } from '../api/client'
import { Loader } from '../components/ui/Loader'
import { Card, CardBody } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'

const PROJECT_COLORS = [
  { from: '#f43f5e', to: '#f97316', glow: 'rgba(244,63,94,0.2)' },
  { from: '#7c3aed', to: '#ec4899', glow: 'rgba(124,58,237,0.2)' },
  { from: '#f97316', to: '#fbbf24', glow: 'rgba(249,115,22,0.2)' },
  { from: '#ec4899', to: '#f43f5e', glow: 'rgba(236,72,153,0.2)' },
  { from: '#7c3aed', to: '#60a5fa', glow: 'rgba(96,165,250,0.2)' },
  { from: '#10b981', to: '#14b8a6', glow: 'rgba(16,185,129,0.2)' },
]

export const ProjectSelectPage: React.FC = () => {
  const { user, projects, setSelectedProject, setAuth } = useAuth()
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const toast = useToast()
  const navigate = useNavigate()

  useEffect(() => {
    if (user?.role !== 'tester') return
    const load = async () => {
      setLoading(true)
      try {
        const resp = await apiClient.auth.projects()
        if (!resp.projects?.length) {
          toast.error('Aucun accès projet. Contactez votre administrateur.')
          return
        }
        setAuth(user, resp.projects)
      } catch (err: any) {
        toast.error(err?.message || 'Échec du chargement des projets')
      } finally {
        setLoading(false)
      }
    }
    if (!projects.length) load()
  }, [user, projects.length, setAuth, toast])

  const handleSelect = (project: (typeof projects)[0]) => {
    setSelectedProject(project)
    toast.success(`Projet ${project.key} sélectionné`)
    navigate('/pipeline')
  }

  const filtered = projects.filter(
    (p) =>
      !search ||
      p.key.toLowerCase().includes(search.toLowerCase()) ||
      (p.name || '').toLowerCase().includes(search.toLowerCase())
  )

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-32 gap-4">
        <div className="relative w-16 h-16">
          <div className="absolute inset-0 rounded-full border-2 border-brand-violet/20" />
          <div className="absolute inset-0 rounded-full border-2 border-t-brand-violet border-r-transparent border-b-transparent border-l-transparent animate-spin" />
          <FolderKanban size={20} className="absolute inset-0 m-auto text-brand-violet" />
        </div>
        <p className="text-brand-navy font-semibold">Chargement des projets Jira...</p>
      </div>
    )
  }

  if (!projects.length) {
    return (
      <Card className="max-w-lg mx-auto">
        <CardBody className="text-center py-16">
          <FolderKanban size={40} className="text-brand-rose/40 mx-auto mb-3" />
          <p className="text-brand-red font-bold text-lg mb-1">Accès refusé</p>
          <p className="text-brand-muted text-sm">Aucun projet accessible. Contactez votre administrateur.</p>
        </CardBody>
      </Card>
    )
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6 animate-fade-in">

      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-2xl flex items-center justify-center flex-shrink-0"
          style={{ background: 'linear-gradient(135deg, #7c3aed, #ec4899)' }}>
          <FolderKanban size={18} className="text-white" />
        </div>
        <div>
          <h1 className="text-2xl font-extrabold text-brand-navy">Projets Jira</h1>
          <p className="text-sm text-brand-muted">Choisissez le projet sur lequel vous souhaitez travailler</p>
        </div>
        <div className="ml-auto">
          <Badge variant="violet" dot>
            {projects.length} projets
          </Badge>
        </div>
      </div>

      {/* Search */}
      <div className="relative">
        <FolderOpen size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          placeholder="Rechercher un projet..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-11 pr-4 py-3.5 bg-white border-2 border-gray-100 rounded-2xl text-sm text-brand-navy placeholder:text-gray-300 focus:border-brand-violet transition-all shadow-sm"
        />
      </div>

      {/* Project Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.map((project, idx) => {
          const colors = PROJECT_COLORS[idx % PROJECT_COLORS.length]
          return (
            <button
              key={project.key}
              type="button"
              onClick={() => handleSelect(project)}
              className="bg-white rounded-2xl border border-gray-100 p-5 text-left group transition-all duration-250 hover:-translate-y-1 animate-scale-in"
              style={{
                animationDelay: `${idx * 0.06}s`,
                boxShadow: '0 2px 12px rgba(10,15,46,0.06)',
              }}
              onMouseEnter={(e) => {
                ;(e.currentTarget as HTMLButtonElement).style.boxShadow = `0 8px 30px ${colors.glow}`
              }}
              onMouseLeave={(e) => {
                ;(e.currentTarget as HTMLButtonElement).style.boxShadow = '0 2px 12px rgba(10,15,46,0.06)'
              }}
            >
              {/* Color strip top */}
              <div className="h-1 -mx-5 -mt-5 mb-5 rounded-t-2xl"
                style={{ background: `linear-gradient(90deg, ${colors.from}, ${colors.to})` }} />

              <div className="flex items-start gap-3">
                <div
                  className="w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform"
                  style={{ background: `linear-gradient(135deg, ${colors.from}, ${colors.to})` }}
                >
                  <FolderOpen size={18} className="text-white" />
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <p className="font-extrabold text-brand-navy font-mono text-sm">{project.key}</p>
                    {project.project_type && (
                      <span
                        className="text-[10px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded"
                        style={{
                          background: `linear-gradient(135deg, ${colors.from}18, ${colors.to}12)`,
                          color: colors.from,
                        }}
                      >
                        {project.project_type}
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-brand-muted line-clamp-2 leading-snug">{project.name}</p>
                </div>

                <ChevronRight
                  size={16}
                  className="text-gray-200 group-hover:text-brand-violet group-hover:translate-x-0.5 transition-all flex-shrink-0 mt-0.5"
                />
              </div>

              <div className="mt-4 pt-3 border-t border-gray-50 flex items-center gap-1">
                <Sparkles size={11} className="text-gray-300" />
                <p className="text-[11px] text-gray-400">Cliquez pour sélectionner ce projet</p>
              </div>
            </button>
          )
        })}
      </div>

      {filtered.length === 0 && search && (
        <div className="text-center py-12">
          <FolderOpen size={32} className="text-gray-200 mx-auto mb-2" />
          <p className="text-brand-muted text-sm">Aucun projet trouvé pour « {search} »</p>
        </div>
      )}
    </div>
  )
}
