import React, { useState } from 'react'
import { useNavigate, Navigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import { apiClient, API_BASE_URL } from '../api/client'
import { Mail, Lock, User, Eye, EyeOff, ArrowRight, Shield } from 'lucide-react'

export const LoginPage: React.FC = () => {
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const { setAuth, user, loading: authLoading } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()

  React.useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const err = params.get('error')
    if (err) {
      if (err === 'unauthorized') {
        toast.error("Votre compte Microsoft n'est pas autorisé.")
      } else if (err === 'disabled') {
        toast.error("Ce compte est désactivé. Contactez un administrateur.")
      } else if (err === 'oauth_failed') {
        toast.error("Échec de l'authentification Microsoft.")
      } else {
        toast.error("Une erreur est survenue lors de la connexion.")
      }
      navigate('/login', { replace: true })
    }
  }, [toast, navigate])

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
      const { user: loginUser, role, projects } = await apiClient.auth.login(identifier, password)
      setAuth(loginUser, projects || [])

      if (role === 'admin') {
        toast.success('Connexion admin réussie')
        navigate('/pipeline')
        return
      }

      toast.success(`Bienvenue, ${loginUser.display_name || loginUser.jira_username}`)
      if ((projects?.length || 0) > 1) {
        navigate('/projects')
      } else if ((projects?.length || 0) === 1) {
        navigate('/pipeline')
      } else {
        toast.error('Aucun projet accessible. Contactez votre administrateur.')
      }
    } catch (err: any) {
      toast.error(err?.message || 'Échec de connexion')
    } finally {
      setLoading(false)
    }
  }

  const handleMicrosoftLogin = () => {
    window.location.href = `${API_BASE_URL}/auth/microsoft/login?next=${encodeURIComponent('/pipeline')}`
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
            © 2026 · <span className="text-brand-rose font-semibold">Sopra HR Software</span> · Synaptest Platform
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
          <div className="mb-6">
            <h2 className="text-3xl font-extrabold text-brand-navy mb-2">Bienvenue 👋</h2>
            <p className="text-brand-muted">Connectez-vous pour continuer</p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-xs font-bold text-brand-navy/70 uppercase tracking-widest mb-2">
                Identifiant Jira ou Email Admin
              </label>
              <div className="relative">
                <User size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-brand-muted" />
                <input
                  type="text"
                  id="login-identifier"
                  placeholder="yomahfoudh ou admin@soprahr.com"
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  required
                  className="w-full pl-11 pr-4 py-3.5 bg-white border-2 border-gray-100 rounded-xl text-sm font-medium text-brand-navy placeholder:text-gray-300 focus:border-brand-violet transition-all shadow-sm"
                />
              </div>
            </div>

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
                  className="w-full pl-11 pr-12 py-3.5 bg-white border-2 border-gray-100 rounded-xl text-sm font-medium text-brand-navy placeholder:text-gray-300 transition-all shadow-sm focus:border-brand-violet"
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
                  <User size={16} />
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
  onClick={handleMicrosoftLogin}
  className="w-full py-3.5 px-4 border-2 border-gray-100 rounded-xl text-sm font-semibold text-brand-navy hover:border-brand-violet hover:text-brand-violet hover:bg-brand-violet/5 transition-all flex items-center justify-center gap-2"
>
  <svg
    width="16"
    height="16"
    viewBox="0 0 23 23"
    fill="currentColor"
    className="mr-2"
  >
    <path fill="#F25022" d="M1 1h10v10H1z"/>
    <path fill="#7FBA00" d="M12 1h10v10H12z"/>
    <path fill="#00A4EF" d="M1 12h10v10H1z"/>
    <path fill="#FFB900" d="M12 12h10v10H12z"/>
  </svg>
  Se connecter avec Microsoft
</button>
<div className="mt-3 p-3 border border-amber-200 bg-amber-50 text-amber-900 text-xs flex items-start gap-2 rounded-lg">
  <span className="text-amber-600 font-bold">!</span>
  <p>
    Vous n’avez pas de compte ? Contactez l’administrateur pour obtenir vos identifiants.
  </p>
</div>
          
          {/* Footer */}
          <p className="text-center text-xs text-gray-400 mt-8">
            Accès sécurisé · <span className="font-bold text-brand-navy">Sopra HR Software</span> · 2026
          </p>
        </div>
      </div>
    </div>
  )
}