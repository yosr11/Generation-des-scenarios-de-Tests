import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FolderOpen } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import { apiClient } from '../api/client'
import { Loader } from '../components/ui/Loader'
import { Card } from '../components/ui/Card'

export const ProjectSelectPage: React.FC = () => {
  const { user, projects, setSelectedProject, setAuth } = useAuth()
  const [loading, setLoading] = useState(false)
  const toast = useToast()
  const navigate = useNavigate()

  useEffect(() => {
    if (user?.role !== 'tester') return
    const load = async () => {
      setLoading(true)
      try {
        const resp = await apiClient.auth.projects()
        if (!resp.projects?.length) {
          toast.error('No project access. Contact your administrator.')
          return
        }
        setAuth(user, resp.projects)
      } catch (err: any) {
        toast.error(err?.message || 'Failed to load projects')
      } finally {
        setLoading(false)
      }
    }
    if (!projects.length) load()
  }, [user, projects.length, setAuth, toast])

  const handleSelect = (project: (typeof projects)[0]) => {
    setSelectedProject(project)
    toast.success(`Project ${project.key} selected`)
    navigate('/pipeline')
  }

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Loader size="lg" text="Loading Jira projects..." />
      </div>
    )
  }

  if (!projects.length) {
    return (
      <Card className="max-w-lg mx-auto text-center py-12">
        <p className="text-brand-red font-semibold text-lg">
          No project access. Contact your administrator.
        </p>
      </Card>
    )
  }

  return (
    <div className="max-w-4xl mx-auto">
      <h2 className="text-xl font-bold text-brand-navy mb-2">Select a Jira project</h2>
      <p className="text-sm text-gray-600 mb-6">
        Choose the project you want to work on. Projects are fetched live from Jira.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {projects.map((project) => (
          <button
            key={project.key}
            type="button"
            onClick={() => handleSelect(project)}
            className="bg-white rounded-xl border border-gray-200 p-5 text-left hover:border-brand-orange hover:shadow-md transition-all group"
          >
            <div className="flex items-start gap-3">
              <div className="p-2 rounded-lg bg-brand-bg group-hover:bg-brand-orange/10">
                <FolderOpen size={20} className="text-brand-navy group-hover:text-brand-orange" />
              </div>
              <div>
                <p className="font-bold text-brand-navy">{project.key}</p>
                <p className="text-sm text-gray-600 mt-1 line-clamp-2">{project.name}</p>
                {project.project_type && (
                  <span className="inline-block mt-2 text-[10px] uppercase tracking-wide bg-brand-orange/10 text-brand-orange px-2 py-0.5 rounded">
                    {project.project_type}
                  </span>
                )}
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
