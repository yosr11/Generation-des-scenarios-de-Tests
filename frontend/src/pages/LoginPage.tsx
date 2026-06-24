import React, { useState } from 'react'
import { useNavigate, Navigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import { apiClient } from '../api/client'

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

  if (authLoading) return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-brand-blue via-brand-pink to-brand-orange animate-fade-in">
      <div className="text-white text-lg font-semibold">Chargement...</div>
    </div>
  )

  if (user) return <Navigate to="/pipeline" replace />

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      if (mode === 'admin') {
        const resp = await apiClient.auth.loginAdmin(email, password)
        setAuth(resp.user)
        toast.success('Connexion admin réussie')
        navigate('/pipeline')
      } else {
        const resp = await apiClient.auth.loginTester(username, password)
        setAuth(resp.user, resp.projects || [])
        toast.success(`Bienvenue, ${resp.user.display_name || resp.user.jira_username}`)
        if ((resp.projects?.length || 0) > 1) navigate('/projects')
        else if ((resp.projects?.length || 0) === 1) navigate('/pipeline')
        else toast.error('Aucun projet accessible. Contactez votre administrateur.')
      }
    } catch (err: any) {
      toast.error(err?.message || 'Échec de connexion')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 via-blue-50 to-pink-50 p-4 animate-fade-in">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8 animate-slide-down">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gradient-to-br from-brand-blue to-brand-pink mb-4 shadow-lg">
            <div className="text-white text-2xl font-bold">◊</div>
          </div>
          <h1 className="text-3xl font-bold text-brand-navy mb-2">Synaptéest</h1>
          <p className="text-gray-600 text-sm">Plateforme de génération intelligente de tests</p>
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl shadow-xl overflow-hidden animate-scale-in">
          {/* Gradient Bar */}
          <div className="h-1 bg-gradient-to-r from-brand-blue via-brand-pink to-brand-orange"></div>

          <div className="p-8">
            {/* Welcome Text */}
            <h2 className="text-2xl font-bold text-brand-navy mb-1">Bienvenue</h2>
            <p className="text-gray-500 text-sm mb-6">Connectez-vous pour continuer</p>

            {/* Mode Tabs */}
            <div className="flex gap-2 mb-6 bg-gray-100 p-1 rounded-lg">
              <button
                type="button"
                onClick={() => setMode('tester')}
                className={`flex-1 py-2 px-4 rounded-md font-semibold text-sm transition-all ${
                  mode === 'tester'
                    ? 'bg-white text-brand-blue shadow-md'
                    : 'text-gray-600 hover:text-brand-navy'
                }`}
              >
                👤 Testeur
              </button>
              <button
                type="button"
                onClick={() => setMode('admin')}
                className={`flex-1 py-2 px-4 rounded-md font-semibold text-sm transition-all ${
                  mode === 'admin'
                    ? 'bg-white text-brand-pink shadow-md'
                    : 'text-gray-600 hover:text-brand-navy'
                }`}
              >
                🛡 Admin
              </button>
            </div>

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-4">
              {mode === 'tester' ? (
                <>
                  <div>
                    <label className="block text-xs font-bold text-gray-700 uppercase tracking-wide mb-2">
                      Identifiant Jira
                    </label>
                    <div className="relative">
                      <span className="absolute left-3 top-3 text-gray-400">👤</span>
                      <input
                        type="text"
                        placeholder="yomahfoudh"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        required
                        className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-brand-blue focus:border-transparent outline-none transition-all"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-gray-700 uppercase tracking-wide mb-2">
                      Mot de passe
                    </label>
                    <div className="relative">
                      <span className="absolute left-3 top-3 text-gray-400">🔒</span>
                      <input
                        type="password"
                        placeholder="••••••••"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                        className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-brand-blue focus:border-transparent outline-none transition-all"
                      />
                    </div>
                  </div>
                </>
              ) : (
                <>
                  <div>
                    <label className="block text-xs font-bold text-gray-700 uppercase tracking-wide mb-2">
                      Email Admin
                    </label>
                    <div className="relative">
                      <span className="absolute left-3 top-3 text-gray-400">✉️</span>
                      <input
                        type="email"
                        placeholder="admin@soprahr.com"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                        className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-brand-pink focus:border-transparent outline-none transition-all"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-gray-700 uppercase tracking-wide mb-2">
                      Mot de passe
                    </label>
                    <div className="relative">
                      <span className="absolute left-3 top-3 text-gray-400">🔒</span>
                      <input
                        type="password"
                        placeholder="••••••••"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                        className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-brand-pink focus:border-transparent outline-none transition-all"
                      />
                    </div>
                  </div>
                </>
              )}

              {/* Submit Button */}
              <button
                type="submit"
                disabled={loading}
                className={`w-full py-2 px-4 rounded-lg font-semibold text-white transition-all transform hover:scale-105 active:scale-95 ${
                  mode === 'tester'
                    ? 'bg-gradient-to-r from-brand-blue to-brand-blue hover:shadow-lg'
                    : 'bg-gradient-to-r from-brand-pink to-brand-orange hover:shadow-lg'
                } disabled:opacity-70 disabled:cursor-not-allowed disabled:transform-none`}
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <span className="inline-block animate-spin">⟳</span>
                    Connexion...
                  </span>
                ) : (
                  '→ Se connecter'
                )}
              </button>
            </form>

            {/* Divider */}
            <div className="flex items-center gap-3 my-5">
              <div className="flex-1 h-px bg-gray-200"></div>
              <span className="text-xs text-gray-400 font-medium">ou</span>
              <div className="flex-1 h-px bg-gray-200"></div>
            </div>

            {/* Toggle Button */}
            <button
              type="button"
              onClick={() => setMode(mode === 'tester' ? 'admin' : 'tester')}
              className="w-full py-2 px-4 border-2 border-gray-200 rounded-lg font-semibold text-brand-navy hover:border-brand-blue hover:bg-blue-50 transition-all"
            >
              ↺ {mode === 'tester' ? 'Connexion Admin' : 'Connexion Testeur'}
            </button>

            {/* Footer */}
            <p className="text-center text-xs text-gray-500 mt-6">
              Accès sécurisé · <span className="font-bold text-brand-navy">Sopra HR Software</span> · 2025
            </p>
          </div>
        </div>

        {/* Background Decoration */}
        <div className="absolute -z-10 inset-0 overflow-hidden">
          <div className="absolute top-20 right-10 w-72 h-72 bg-brand-blue rounded-full mix-blend-multiply filter blur-3xl opacity-10 animate-pulse"></div>
          <div className="absolute bottom-20 left-10 w-72 h-72 bg-brand-pink rounded-full mix-blend-multiply filter blur-3xl opacity-10 animate-pulse" style={{ animationDelay: '0.5s' }}></div>
        </div>
      </div>
    </div>
  )
}