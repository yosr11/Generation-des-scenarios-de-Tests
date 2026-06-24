import React, { createContext, useCallback, useContext, useMemo, useState } from 'react'

export type UserRole = 'admin' | 'tester'

export interface AuthUser {
  email: string
  role: UserRole
  display_name?: string
  jira_username?: string
}

export interface JiraProject {
  key: string
  name: string
  id?: string
  project_type?: string
}

interface AuthContextValue {
  user: AuthUser | null
  projects: JiraProject[]
  selectedProject: JiraProject | null
  loading: boolean
  setAuth: (user: AuthUser, projects?: JiraProject[]) => void
  setSelectedProject: (project: JiraProject | null) => void
  logout: () => Promise<void>
  refreshMe: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

const PROJECT_KEY = 'agent_test_selected_project'

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [projects, setProjects] = useState<JiraProject[]>([])
  const [selectedProject, setSelectedProjectState] = useState<JiraProject | null>(() => {
    const raw = localStorage.getItem(PROJECT_KEY)
    return raw ? JSON.parse(raw) : null
  })
  const [loading, setLoading] = useState(true)

  const setSelectedProject = useCallback((project: JiraProject | null) => {
    setSelectedProjectState(project)
    if (project) {
      localStorage.setItem(PROJECT_KEY, JSON.stringify(project))
    } else {
      localStorage.removeItem(PROJECT_KEY)
    }
  }, [])

  const setAuth = useCallback((nextUser: AuthUser, nextProjects: JiraProject[] = []) => {
    setUser(nextUser)
    setProjects(nextProjects)
    if (nextUser.role === 'tester' && nextProjects.length === 1) {
      setSelectedProject(nextProjects[0])
    }
  }, [setSelectedProject])

  const refreshMe = useCallback(async () => {
    try {
      const { apiClient } = await import('../api/client')
      const me = await apiClient.auth.me()
      setUser({
        email: me.email,
        role: me.role as UserRole,
        display_name: me.display_name,
        jira_username: me.jira_username,
      })
      if (me.role === 'tester') {
        const projResp = await apiClient.auth.projects()
        setProjects(projResp.projects || [])
      }
    } catch {
      setUser(null)
      setProjects([])
    } finally {
      setLoading(false)
    }
  }, [])

  React.useEffect(() => {
    refreshMe()
  }, [refreshMe])

  const logout = useCallback(async () => {
    try {
      const { apiClient } = await import('../api/client')
      await apiClient.auth.logout()
    } catch {
      /* ignore */
    }
    setUser(null)
    setProjects([])
    setSelectedProject(null)
  }, [setSelectedProject])

  const value = useMemo(
    () => ({
      user,
      projects,
      selectedProject,
      loading,
      setAuth,
      setSelectedProject,
      logout,
      refreshMe,
    }),
    [user, projects, selectedProject, loading, setAuth, setSelectedProject, logout, refreshMe]
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
