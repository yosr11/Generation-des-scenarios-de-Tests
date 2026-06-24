import React, { useState } from 'react'
import { useNavigate, Navigate } from 'react-router-dom'
import { Shield, User } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import { apiClient } from '../api/client'
import { Button } from '../components/ui/Button'
import { Loader } from '../components/ui/Loader'

type LoginMode = 'tester' | 'admin'

export const LoginPage: React.FC = () => {
  const [mode, setMode] = useState<LoginMode>('tester')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const { setAuth, user, loading: authLoading } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-brand-bg">
        <Loader size="lg" text="Loading..." />
      </div>
    )
  }

  if (user) {
    return <Navigate to="/pipeline" replace />
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      if (mode === 'admin') {
        const resp = await apiClient.auth.loginAdmin(email, password)
        setAuth(resp.user)
        toast.success('Admin login successful')
        navigate('/pipeline')
      } else {
        const resp = await apiClient.auth.loginTester(username, password)
        setAuth(resp.user, resp.projects || [])
        toast.success(`Welcome, ${resp.user.display_name || resp.user.jira_username}`)
        if ((resp.projects?.length || 0) > 1) {
          navigate('/projects')
        } else if ((resp.projects?.length || 0) === 1) {
          navigate('/pipeline')
        } else {
          toast.error('No project access. Contact your administrator.')
        }
      }
    } catch (err: any) {
      toast.error(err?.message || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-brand-bg flex items-center justify-center p-6">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-brand-navy">Agent Test Platform</h1>
          <p className="text-sm text-gray-600 mt-2">Sign in to continue</p>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="flex border-b border-gray-200">
            <button
              type="button"
              onClick={() => setMode('tester')}
              className={`flex-1 flex items-center justify-center gap-2 py-3 text-sm font-medium transition-colors ${
                mode === 'tester'
                  ? 'bg-brand-navy text-white'
                  : 'text-gray-600 hover:bg-gray-50'
              }`}
            >
              <User size={16} />
              Tester (Jira)
            </button>
            <button
              type="button"
              onClick={() => setMode('admin')}
              className={`flex-1 flex items-center justify-center gap-2 py-3 text-sm font-medium transition-colors ${
                mode === 'admin'
                  ? 'bg-brand-navy text-white'
                  : 'text-gray-600 hover:bg-gray-50'
              }`}
            >
              <Shield size={16} />
              Admin
            </button>
          </div>

          <form onSubmit={handleSubmit} className="p-6 space-y-4">
            {mode === 'admin' ? (
              <>
                <div>
                  <label className="block text-sm font-medium text-brand-navy mb-1.5">Email</label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm"
                    placeholder="admin@soprahr.com"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-brand-navy mb-1.5">Password</label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm"
                  />
                </div>
              </>
            ) : (
              <>
                <div>
                  <label className="block text-sm font-medium text-brand-navy mb-1.5">
                    Jira username
                  </label>
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    required
                    className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm"
                    placeholder="yomahfoudh"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-brand-navy mb-1.5">
                    Jira password
                  </label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm"
                  />
                </div>
              </>
            )}

            <Button type="submit" fullWidth isLoading={loading} variant="primary">
              Sign in
            </Button>
          </form>
        </div>

        {loading && (
          <div className="mt-4 flex justify-center">
            <Loader size="sm" text="Authenticating..." />
          </div>
        )}
      </div>
    </div>
  )
}
