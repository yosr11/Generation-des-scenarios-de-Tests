import React, { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { apiClient } from '../api/client'
import { useToast } from '../contexts/ToastContext'
import { User, Shield, Key, CheckCircle, RefreshCw } from 'lucide-react'

export const ProfilePage: React.FC = () => {
  const { user, refreshMe } = useAuth()
  const toast = useToast()

  const [displayName, setDisplayName] = useState('')
  const [jiraUsername, setJiraUsername] = useState('')
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [dbProfile, setDbProfile] = useState<any>(null)

  useEffect(() => {
    if (user) {
      setDisplayName(user.display_name || '')
      setJiraUsername(user.jira_username || '')
    }
    fetchProfile()
  }, [user])

  const fetchProfile = async () => {
    try {
      const data = await apiClient.auth.getProfile()
      setDbProfile(data)
      if (data.display_name) setDisplayName(data.display_name)
      if (data.jira_username) setJiraUsername(data.jira_username)
    } catch (error) {
      console.error("Failed to load profile details", error)
    }
  }

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      const payload: any = {
        display_name: displayName.trim(),
      }

      if (user?.role === 'tester') {
        payload.jira_username = jiraUsername.trim()
      }

      if (newPassword) {
        if (newPassword !== confirmPassword) {
          toast.error('Les mots de passe ne correspondent pas.')
          setLoading(false)
          return
        }
        if (!currentPassword) {
          toast.error('Le mot de passe actuel est requis pour changer de mot de passe.')
          setLoading(false)
          return
        }
        payload.current_password = currentPassword
        payload.new_password = newPassword
      }

      await apiClient.auth.updateProfile(payload)
      toast.success('Profil mis à jour avec succès.')
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      await refreshMe()
      await fetchProfile()
    } catch (error: any) {
      toast.error(error?.message || 'Erreur lors de la mise à jour.')
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (isoString?: string) => {
    if (!isoString) return '—'
    return new Date(isoString).toLocaleDateString('fr-FR', {
      dateStyle: 'long',
    }) + ' à ' + new Date(isoString).toLocaleTimeString('fr-FR', {
      timeStyle: 'short',
    })
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-fade-in">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-brand-rose/10 text-brand-rose flex items-center justify-center border border-brand-rose/20">
          <User size={20} />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-brand-navy">Mon Profil</h1>
          <p className="text-xs text-brand-muted">Gérer vos informations personnelles et identifiants</p>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        {/* Left Card: Summary */}
        <div className="md:col-span-1 space-y-6">
          <div className="bg-white rounded-3xl border border-slate-100 p-6 shadow-sm flex flex-col items-center text-center">
            <div className="w-20 h-20 rounded-full flex items-center justify-center text-white text-2xl font-bold mb-4 shadow-md"
              style={{ background: 'linear-gradient(135deg, #ef4444, #f43f5e, #f97316)' }}>
              {displayName ? displayName.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase() : 'U'}
            </div>
            <h3 className="font-bold text-brand-navy text-lg">{displayName || user?.email || 'Utilisateur'}</h3>
            <span className="inline-block mt-1 text-xs font-bold uppercase tracking-wider px-3 py-1 rounded-full"
              style={{
                background: user?.role === 'admin' ? 'rgba(244,63,94,0.08)' : 'rgba(124,58,237,0.08)',
                color: user?.role === 'admin' ? '#f43f5e' : '#7c3aed',
                border: `1px solid ${user?.role === 'admin' ? 'rgba(244,63,94,0.15)' : 'rgba(124,58,237,0.15)'}`
              }}>
              {user?.role === 'admin' ? '👑 Administrateur' : '🛠️ Testeur QA'}
            </span>

            <div className="w-full border-t border-gray-100 my-5 pt-4 text-left space-y-3">
              <div>
                <p className="text-[10px] uppercase font-bold text-slate-400">Adresse Email</p>
                <p className="text-sm font-semibold text-slate-700 mt-0.5 truncate">{user?.email || '—'}</p>
              </div>
              {user?.role === 'tester' && (
                <div>
                  <p className="text-[10px] uppercase font-bold text-slate-400">Identifiant Jira</p>
                  <p className="text-sm font-semibold text-slate-700 mt-0.5">{jiraUsername || '—'}</p>
                </div>
              )}
              <div>
                <p className="text-[10px] uppercase font-bold text-slate-400">Créé le</p>
                <p className="text-xs text-slate-500 mt-0.5">{formatDate(dbProfile?.created_at)}</p>
              </div>
              <div>
                <p className="text-[10px] uppercase font-bold text-slate-400">Dernière connexion</p>
                <p className="text-xs text-slate-500 mt-0.5">{formatDate(dbProfile?.last_login_at)}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Right Form */}
        <div className="md:col-span-2 space-y-6">
          <form onSubmit={handleUpdateProfile} className="bg-white rounded-3xl border border-slate-100 p-6 shadow-sm space-y-6">
            <div className="flex items-center gap-2 border-b border-gray-100 pb-3">
              <Shield size={16} className="text-slate-400" />
              <h3 className="font-bold text-brand-navy">Mettre à jour le profil</h3>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1">
                <label className="text-xs uppercase font-bold text-slate-500">Nom affiché</label>
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 transition focus:border-brand-rose focus:outline-none"
                  placeholder="Ex: Jean Dupont"
                  required
                />
              </div>

              {user?.role === 'tester' && (
                <div className="space-y-1">
                  <label className="text-xs uppercase font-bold text-slate-500">Identifiant Jira</label>
                  <input
                    type="text"
                    value={jiraUsername}
                    onChange={(e) => setJiraUsername(e.target.value)}
                    className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 transition focus:border-brand-rose focus:outline-none"
                    placeholder="Ex: j.dupont"
                    required
                  />
                </div>
              )}
            </div>

            {/* Change Password Block */}
            <div className="bg-slate-50 rounded-2xl border border-slate-200/60 p-5 space-y-4">
              <div className="flex items-center gap-2 text-slate-800 font-bold text-sm">
                <Key size={14} className="text-slate-400" />
                <span>Modifier le mot de passe</span>
              </div>
              <p className="text-xs text-slate-500">Laissez les champs vides si vous ne souhaitez pas modifier votre mot de passe.</p>

              <div className="space-y-3">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-600">Nouveau mot de passe</label>
                  <input
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-900 transition focus:border-brand-rose focus:outline-none"
                    placeholder="Au moins 6 caractères"
                  />
                </div>

                {newPassword && (
                  <>
                    <div className="space-y-1">
                      <label className="text-xs font-semibold text-slate-600">Confirmer le nouveau mot de passe</label>
                      <input
                        type="password"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        className="w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-900 transition focus:border-brand-rose focus:outline-none"
                        placeholder="Retapez le mot de passe"
                        required
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-xs font-semibold text-slate-600">Mot de passe actuel</label>
                      <input
                        type="password"
                        value={currentPassword}
                        onChange={(e) => setCurrentPassword(e.target.value)}
                        className="w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-900 transition focus:border-brand-rose focus:outline-none"
                        placeholder="Obligatoire pour appliquer les changements"
                        required
                      />
                    </div>
                  </>
                )}
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                type="submit"
                disabled={loading}
                className="px-6 py-3 rounded-2xl font-bold text-white flex items-center gap-2 transition hover:-translate-y-0.5 hover:shadow-lg disabled:opacity-50"
                style={{ background: 'linear-gradient(90deg, #4338ca, #f43f5e)', boxShadow: '0 4px 14px rgba(244,63,94,0.3)' }}
              >
                {loading ? <RefreshCw size={15} className="animate-spin" /> : <CheckCircle size={15} />}
                Enregistrer les modifications
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
