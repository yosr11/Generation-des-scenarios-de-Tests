import React, { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { apiClient } from '../api/client'
import { useToast } from '../contexts/ToastContext'
import { Lock, Eye, EyeOff, CheckCircle, RefreshCw } from 'lucide-react'

export const ResetPasswordPage: React.FC = () => {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')
  const navigate = useNavigate()
  const toast = useToast()

  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-brand-navy p-6">
        <div className="bg-white rounded-3xl p-8 max-w-md w-full shadow-2xl text-center space-y-4">
          <p className="text-rose-600 font-bold text-lg">Lien invalide</p>
          <p className="text-sm text-slate-500">Ce lien de réinitialisation est incomplet ou expiré.</p>
          <button
            onClick={() => navigate('/login')}
            className="w-full py-3 bg-brand-navy text-white rounded-xl font-bold text-sm hover:opacity-90"
          >
            Retourner à la connexion
          </button>
        </div>
      </div>
    )
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (newPassword.length < 6) {
      toast.error('Le mot de passe doit contenir au moins 6 caractères.')
      return
    }
    if (newPassword !== confirmPassword) {
      toast.error('Les mots de passe ne correspondent pas.')
      return
    }

    setLoading(true)
    try {
      await apiClient.auth.confirmPasswordReset({
        token,
        new_password: newPassword,
      })
      toast.success('Mot de passe mis à jour avec succès.')
      setSuccess(true)
    } catch (err: any) {
      toast.error(err?.message || 'Une erreur est survenue.')
    } finally {
      setLoading(false)
    }
  }

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-brand-navy p-6">
        <div className="bg-white rounded-3xl p-8 max-w-md w-full shadow-2xl text-center space-y-6 animate-scale-in">
          <div className="w-16 h-16 rounded-full bg-green-50 text-green-500 border border-green-100 flex items-center justify-center mx-auto">
            <CheckCircle size={32} />
          </div>
          <div>
            <h2 className="text-xl font-bold text-brand-navy">Succès !</h2>
            <p className="text-sm text-slate-500 mt-2">Votre mot de passe a été modifié avec succès. Vous pouvez désormais vous connecter.</p>
          </div>
          <button
            onClick={() => navigate('/login')}
            className="w-full py-3.5 text-white rounded-xl font-bold text-sm transition hover:-translate-y-0.5 hover:shadow-lg"
            style={{ background: 'linear-gradient(135deg, #ef4444, #f43f5e, #f97316)' }}
          >
            Se connecter
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-brand-navy p-6 relative overflow-hidden">
      {/* Background Orbs */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="orb orb-rose w-[300px] h-[300px] top-[-100px] left-[-100px] animate-pulse-glow" />
        <div className="orb orb-orange w-[200px] h-[200px] bottom-[-50px] right-[-50px] animate-pulse-glow" style={{ animationDelay: '1s' }} />
      </div>

      <div className="bg-white rounded-3xl p-8 max-w-md w-full shadow-2xl space-y-6 z-10 animate-scale-in">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-brand-navy">Nouveau mot de passe</h2>
          <p className="text-sm text-slate-500 mt-1">Définissez votre nouveau mot de passe de connexion.</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1">
            <label className="block text-xs font-bold text-brand-navy/70 uppercase tracking-widest">
              Nouveau mot de passe
            </label>
            <div className="relative">
              <Lock size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-brand-muted" />
              <input
                type={showPassword ? 'text' : 'password'}
                placeholder="Au moins 6 caractères"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                className="w-full pl-11 pr-12 py-3.5 bg-white border-2 border-gray-100 rounded-xl text-sm font-medium text-brand-navy placeholder:text-gray-300 focus:border-brand-violet transition-all shadow-sm"
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

          <div className="space-y-1">
            <label className="block text-xs font-bold text-brand-navy/70 uppercase tracking-widest">
              Confirmer le mot de passe
            </label>
            <div className="relative">
              <Lock size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-brand-muted" />
              <input
                type={showPassword ? 'text' : 'password'}
                placeholder="Confirmez votre mot de passe"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                className="w-full pl-11 pr-12 py-3.5 bg-white border-2 border-gray-100 rounded-xl text-sm font-medium text-brand-navy placeholder:text-gray-300 focus:border-brand-violet transition-all shadow-sm"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-4 rounded-xl font-bold text-white text-sm flex items-center justify-center gap-2 transition hover:-translate-y-0.5"
            style={{ background: 'linear-gradient(135deg, #ef4444, #f43f5e, #f97316)', boxShadow: '0 4px 14px rgba(244,63,94,0.3)' }}
          >
            {loading ? <RefreshCw size={16} className="animate-spin" /> : 'Réinitialiser le mot de passe'}
          </button>
        </form>
      </div>
    </div>
  )
}
