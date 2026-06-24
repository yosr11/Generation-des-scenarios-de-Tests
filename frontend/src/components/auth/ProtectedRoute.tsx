import React from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { Loader } from '../ui/Loader'
import { useAuth, UserRole } from '../../contexts/AuthContext'

interface ProtectedRouteProps {
  children: React.ReactNode
  roles?: UserRole[]
  requireProject?: boolean
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  roles,
  requireProject = false,
}) => {
  const { user, loading, selectedProject } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-brand-bg">
        <Loader size="lg" text="Loading session..." />
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  if (roles && !roles.includes(user.role)) {
    return <Navigate to="/pipeline" replace />
  }

  if (requireProject && user.role === 'tester' && !selectedProject) {
    return <Navigate to="/projects" replace />
  }

  return <>{children}</>
}
