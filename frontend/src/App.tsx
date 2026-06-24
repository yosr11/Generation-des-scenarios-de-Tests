import React from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import { ToastProvider } from './contexts/ToastContext'
import { AppLayout } from './components/layout/AppLayout'
import { ProtectedRoute } from './components/auth/ProtectedRoute'
import { LoginPage } from './pages/LoginPage'
import { ProjectSelectPage } from './pages/ProjectSelectPage'
import { LandingPage } from './pages/LandingPage'
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
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AuthProvider>
        <ToastProvider>
          <Routes>
            {/* Public Routes */}
            <Route path="/"      element={<LandingPage />} />
            <Route path="/login" element={<LoginPage />} />

            {/* Authenticated Routes */}
            <Route element={<AuthenticatedLayout />}>
              <Route path="/home" element={<Navigate to="/pipeline" replace />} />
              <Route
                path="/pipeline"
                element={
                  <ProtectedRoute requireProject>
                    <PipelinePage />
                  </ProtectedRoute>
                }
              />
              <Route path="/analysis"  element={<AnalysisPage />} />
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/history"   element={<HistoryPage />} />
              <Route
                path="/projects"
                element={
                  <ProtectedRoute roles={['tester']}>
                    <ProjectSelectPage />
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
