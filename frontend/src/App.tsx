import React from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import { ToastProvider } from './contexts/ToastContext'
import { AppLayout } from './components/layout/AppLayout'
import { ProtectedRoute } from './components/auth/ProtectedRoute'
import { LoginPage } from './pages/LoginPage'
import { ProjectSelectPage } from './pages/ProjectSelectPage'
import { DashboardPage, PipelinePage, AnalysisPage, HistoryPage } from './pages'

function AuthenticatedLayout() {
  return (
    <ProtectedRoute>
      <AppLayout />
    </ProtectedRoute>
  )
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ToastProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route element={<AuthenticatedLayout />}>
              <Route path="/" element={<Navigate to="/pipeline" replace />} />
              <Route
                path="/pipeline"
                element={
                  <ProtectedRoute requireProject>
                    <PipelinePage />
                  </ProtectedRoute>
                }
              />
              <Route path="/analysis" element={<AnalysisPage />} />
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/history" element={<HistoryPage />} />
              <Route
                path="/projects"
                element={
                  <ProtectedRoute roles={['tester']}>
                    <ProjectSelectPage />
                  </ProtectedRoute>
                }
              />
            </Route>
            <Route path="*" element={<Navigate to="/pipeline" replace />} />
          </Routes>
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
