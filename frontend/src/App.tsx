import React from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import { ToastProvider } from './contexts/ToastContext'
import { AppLayout } from './components/layout/AppLayout'
import { ProtectedRoute } from './components/auth/ProtectedRoute'
import { LoginPage } from './pages/LoginPage'
import { ProjectSelectPage } from './pages/ProjectSelectPage'
import { LandingPage } from './pages/LandingPage'
import { PipelinePage, HistoryPage } from './pages'
import { StoryDetailPage } from './pages/StoryDetailPage'
import { AdminDashboardPage } from './pages/admin/AdminDashboardPage'
import { UsersPage } from './pages/admin/UsersPage'
import { PipelineHistoryPage } from './pages/admin/PipelineHistoryPage'
import { AuditPage } from './pages/admin/AuditPage'

function AuthenticatedLayout() {
  return (
    <ProtectedRoute>
      <AppLayout />
    </ProtectedRoute>
  )
}

function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AuthProvider>
        <ToastProvider>
          <Routes>
            {/* Public Routes */}
            <Route path="/"      element={<LandingPage />} />
            <Route path="/login" element={<LoginPage />} />

            {/* Authenticated Routes */}
            <Route element={<AuthenticatedLayout />}>

              {/* ── Redirect /home to role-aware default ── */}
              <Route path="/home" element={<Navigate to="/pipeline" replace />} />

              {/* ── Tester Routes ── */}
              <Route
                path="/pipeline"
                element={
                  <ProtectedRoute roles={['tester']}>
                    <PipelinePage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/history"
                element={
                  <ProtectedRoute roles={['tester']}>
                    <HistoryPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/history/:storyId"
                element={
                  <ProtectedRoute roles={['tester']}>
                    <StoryDetailPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/projects"
                element={
                  <ProtectedRoute roles={['tester']}>
                    <ProjectSelectPage />
                  </ProtectedRoute>
                }
              />

              {/* ── Admin Routes ── */}
              <Route
                path="/admin/dashboard"
                element={
                  <ProtectedRoute roles={['admin']}>
                    <AdminDashboardPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/users"
                element={
                  <ProtectedRoute roles={['admin']}>
                    <UsersPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/pipelines"
                element={
                  <ProtectedRoute roles={['admin']}>
                    <PipelineHistoryPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/audit"
                element={
                  <ProtectedRoute roles={['admin']}>
                    <AuditPage />
                  </ProtectedRoute>
                }
              />

              {/* ── Admin default redirect ── */}
              <Route
                path="/admin"
                element={
                  <ProtectedRoute roles={['admin']}>
                    <Navigate to="/admin/dashboard" replace />
                  </ProtectedRoute>
                }
              />
            </Route>

            {/* Catch-all */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
