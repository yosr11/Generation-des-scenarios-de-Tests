import React, { useState } from 'react'
import { useNavigate, Navigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import { apiClient } from '../api/client'
import { Zap, Mail, Lock, User, Eye, EyeOff, ArrowRight, Shield } from 'lucide-react'

type LoginMode = 'tester' | 'admin'

export const LoginPage: React.FC = () => {
  const [mode, setMode] = useState<LoginMode>('tester')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [email, setEmail] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const { setAuth, user, loading: authLoading } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()

  if (authLoading) return (
    <div className="min-h-screen flex items-center justify-center bg-brand-navy">
      <div className="flex flex-col items-center gap-4">
        <div className="w-12 h-12 rounded-full bg-grad-cta animate-pulse-glow" />
        <p className="text-white/60 text-sm">Chargement...</p>
      </div>
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
    <div className="min-h-screen flex bg-brand-navy overflow-hidden">

      {/* ── Left Panel — Branding ─────────────────── */}
      <div className="hidden lg:flex lg:w-[55%] relative flex-col justify-between p-12 overflow-hidden">

        {/* Orbs */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="orb orb-rose w-[500px] h-[500px] top-[-100px] left-[-100px] animate-pulse-glow" />
          <div className="orb orb-violet w-[400px] h-[400px] bottom-[-80px] right-[-80px] animate-pulse-glow" style={{ animationDelay: '2s' }} />
          <div className="orb orb-orange w-[300px] h-[300px] top-[40%] right-[10%] animate-pulse-glow" style={{ animationDelay: '1s' }} />
          {/* Grid */}
          <div className="absolute inset-0" style={{
            backgroundImage: 'linear-gradient(rgba(255,255,255,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.04) 1px, transparent 1px)',
            backgroundSize: '50px 50px',
          }} />
        </div>

        {/* Logo */}
        <div className="relative z-10 animate-fade-in">
          <div className="flex items-center gap-3">
            <img src="/logo_sopra.png" alt="Sopra HR"
              className="h-9 w-auto object-contain"
              style={{ filter: 'brightness(0) invert(1)', opacity: 0.9 }} />
            <div className="w-px h-6 bg-white/20" />
            <span className="text-2xl font-bold text-white">
              Synap<span style={{ color: '#f43f5e' }}>test</span>
            </span>
          </div>
        </div>

        {/* Center Content */}
        <div className="relative z-10 flex-1 flex flex-col justify-center">
          <div className="animate-slide-up">
            <h1 className="text-5xl font-extrabold text-white mb-6 leading-tight">
              Générez vos tests<br />
              <span className="text-gradient-hero">avec l'IA</span>
            </h1>
            <p className="text-white/55 text-lg mb-10 leading-relaxed max-w-md">
              Transformez vos user stories Jira en scénarios de tests exhaustifs
              grâce à une orchestration multi-agents intelligente.
            </p>

            {/* Feature Chips */}
            <div className="flex flex-wrap gap-3">
              {['Multi-agent', 'Automatisé', 'LangGraph', 'RAG Context'].map((tag, i) => (
                <span
                  key={tag}
                  className="glass-card px-4 py-2 text-sm text-white/80 font-medium animate-fade-in"
                  style={{ animationDelay: `${i * 0.1 + 0.3}s` }}
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>

          {/* Stats Row */}
          <div className="animate-slide-up delay-300 mt-10 grid grid-cols-3 gap-4">
            {[
              { v: '5', l: 'Agents IA' },
              { v: '3', l: 'Itérations' },
              { v: '70%', l: 'Couverture' },
            ].map((s) => (
              <div key={s.l} className="glass-card p-4 text-center">
                <p className="text-3xl font-extrabold text-gradient-warm">{s.v}</p>
                <p className="text-xs text-white/50 mt-1 font-medium">{s.l}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Bottom Brand */}
        <div className="relative z-10 animate-fade-in delay-500">
          <p className="text-white/30 text-xs">
            © 2025 · <span className="text-brand-rose font-semibold">Sopra HR Software</span> · Synaptest Platform
          </p>
        </div>
      </div>

      {/* ── Right Panel — Form ───────────────────── */}
      <div className="w-full lg:w-[45%] flex items-center justify-center p-6 lg:p-12 relative bg-brand-offwhite">

        {/* Subtle bg texture */}
        <div className="absolute inset-0 opacity-30" style={{
          backgroundImage: 'radial-gradient(circle at 20% 20%, rgba(124,58,237,0.08) 0%, transparent 50%), radial-gradient(circle at 80% 80%, rgba(244,63,94,0.06) 0%, transparent 50%)',
        }} />

        <div className="relative z-10 w-full max-w-md animate-scale-in">

          {/* Mobile Logo */}
          <div className="lg:hidden flex items-center gap-3 mb-8">
            <img src="/logo_sopra.png" alt="Sopra HR" className="h-7 w-auto object-contain opacity-90" />
            <div className="w-px h-5 bg-gray-300" />
            <span className="text-xl font-bold text-brand-navy">
              Synap<span style={{ color: '#f43f5e' }}>test</span>
            </span>
          </div>

          {/* Header */}
          <div className="mb-8">
            <h2 className="text-3xl font-extrabold text-brand-navy mb-2">Bienvenue 👋</h2>
            <p className="text-brand-muted">Connectez-vous pour continuer</p>
          </div>

          {/* Role Tabs */}
          <div className="flex gap-2 p-1.5 bg-brand-navy/08 rounded-2xl mb-8">
            {(['tester', 'admin'] as LoginMode[]).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => setMode(m)}
                className={`flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-xl text-sm font-semibold transition-all duration-250 ${
                  mode === m
                    ? m === 'tester'
                      ? 'bg-brand-navy text-white shadow-card'
                      : 'bg-grad-cta text-white shadow-glow-rose'
                    : 'text-brand-navy/60 hover:text-brand-navy'
                }`}
              >
                {m === 'tester' ? <User size={15} /> : <Shield size={15} />}
                {m === 'tester' ? 'Testeur' : 'Admin'}
              </button>
            ))}
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-5">
            {mode === 'tester' ? (
              <div className="animate-fade-in space-y-5">
                <div>
                  <label className="block text-xs font-bold text-brand-navy/70 uppercase tracking-widest mb-2">
                    Identifiant Jira
                  </label>
                  <div className="relative">
                    <User size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-brand-muted" />
                    <input
                      type="text"
                      id="login-username"
                      placeholder="yomahfoudh"
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      required
                      className="w-full pl-11 pr-4 py-3.5 bg-white border-2 border-gray-100 rounded-xl text-sm font-medium text-brand-navy placeholder:text-gray-300 focus:border-brand-violet transition-all shadow-sm"
                    />
                  </div>
                </div>
              </div>
            ) : (
              <div className="animate-fade-in space-y-5">
                <div>
                  <label className="block text-xs font-bold text-brand-navy/70 uppercase tracking-widest mb-2">
                    Email Admin
                  </label>
                  <div className="relative">
                    <Mail size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-brand-muted" />
                    <input
                      type="email"
                      id="login-email"
                      placeholder="admin@soprahr.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                      className="w-full pl-11 pr-4 py-3.5 bg-white border-2 border-gray-100 rounded-xl text-sm font-medium text-brand-navy placeholder:text-gray-300 focus:border-brand-rose transition-all shadow-sm"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Password */}
            <div>
              <label className="block text-xs font-bold text-brand-navy/70 uppercase tracking-widest mb-2">
                Mot de passe
              </label>
              <div className="relative">
                <Lock size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-brand-muted" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  id="login-password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className={`w-full pl-11 pr-12 py-3.5 bg-white border-2 border-gray-100 rounded-xl text-sm font-medium text-brand-navy placeholder:text-gray-300 transition-all shadow-sm ${
                    mode === 'tester' ? 'focus:border-brand-violet' : 'focus:border-brand-rose'
                  }`}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-brand-muted hover:text-brand-navy transition-colors"
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {/* Submit */}
            <button
              type="submit"
              id="login-submit"
              disabled={loading}
              className="w-full py-4 rounded-xl font-bold text-white text-sm flex items-center justify-center gap-2.5 transition-all duration-250 disabled:opacity-60 disabled:cursor-not-allowed mt-2 hover:-translate-y-0.5"
              style={{
                background: 'linear-gradient(135deg, #ef4444, #f43f5e, #f97316)',
                boxShadow: '0 6px 24px rgba(244,63,94,0.4)',
              }}
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Connexion...
                </>
              ) : (
                <>
                  {mode === 'tester' ? <User size={16} /> : <Shield size={16} />}
                  Se connecter
                  <ArrowRight size={15} />
                </>
              )}
            </button>
          </form>

          {/* Divider */}
          <div className="flex items-center gap-4 my-6">
            <div className="flex-1 h-px bg-gray-100" />
            <span className="text-xs text-gray-400 font-medium">ou</span>
            <div className="flex-1 h-px bg-gray-100" />
          </div>

          {/* Toggle */}
          <button
            type="button"
            onClick={() => setMode(mode === 'tester' ? 'admin' : 'tester')}
            className="w-full py-3.5 px-4 border-2 border-gray-100 rounded-xl text-sm font-semibold text-brand-navy hover:border-brand-violet hover:text-brand-violet hover:bg-brand-violet/5 transition-all flex items-center justify-center gap-2"
          >
            {mode === 'tester' ? (
              <><Shield size={15} /> Connexion Admin</>
            ) : (
              <><User size={15} /> Connexion Testeur</>
            )}
          </button>

          {/* Footer */}
          <p className="text-center text-xs text-gray-400 mt-8">
            Accès sécurisé · <span className="font-bold text-brand-navy">Sopra HR Software</span> · 2025
          </p>
        </div>
      </div>
    </div>
  )
}