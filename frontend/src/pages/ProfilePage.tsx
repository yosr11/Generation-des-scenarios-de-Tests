import React, { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { apiClient } from '../api/client'
import { useToast } from '../contexts/ToastContext'
import { User, Shield, Key, CheckCircle, RefreshCw, Mail, AtSign, Calendar, Clock } from 'lucide-react'
import { getRoleDisplayName } from '../utils/role'

export const ProfilePage: React.FC = () => {
  const { user, refreshMe } = useAuth()
  const toast = useToast()

  const [displayName, setDisplayName] = useState('')
  const [email, setEmail] = useState('')
  const [jiraUsername, setJiraUsername] = useState('')
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [dbProfile, setDbProfile] = useState<any>(null)

  useEffect(() => {
    if (user) {
      setDisplayName(user.display_name || '')
      setEmail(user.email || '')
      setJiraUsername(user.jira_username || '')
    }
    fetchProfile()
  }, [user])

  const fetchProfile = async () => {
    try {
      const data = await apiClient.auth.getProfile()
      setDbProfile(data)
      if (data.display_name) setDisplayName(data.display_name)
      if (data.email) setEmail(data.email)
      if (data.jira_username) setJiraUsername(data.jira_username)
    } catch (error) {
      console.error("Failed to load profile details", error)
    }
  }

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      // Seuls les admins peuvent modifier leur profil depuis cette page.
      const payload: any = {
        display_name: displayName.trim(),
        email: email.trim(),
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

  const isQaEngineer = user?.role === 'tester'

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-fade-in">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-brand-rose/10 text-brand-rose flex items-center justify-center border border-brand-rose/20">
          <User size={20} />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-brand-navy">Mon Profil</h1>
          <p className="text-xs text-brand-muted">Gérer vos informations personnelles et identifiants</p>
        </div>
      </div>

      {isQaEngineer ? (
        /* ── Ingénieur QA : profil détaillé en lecture seule, pleine largeur ────── */
        <div className="bg-white rounded-3xl border border-slate-100 p-8 shadow-sm">
          <div className="flex flex-col sm:flex-row sm:items-center gap-6 border-b border-gray-100 pb-8 mb-8">
            <div className="w-24 h-24 rounded-full flex items-center justify-center text-white text-3xl font-bold shadow-md shrink-0"
              style={{ background: 'linear-gradient(135deg, #ef4444, #f43f5e, #f97316)' }}>
              {displayName ? displayName.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase() : 'U'}
            </div>
            <div>
              <h3 className="font-bold text-brand-navy text-2xl">{displayName || user?.email || 'Utilisateur'}</h3>
              <span className="inline-block mt-2 text-xs font-bold uppercase tracking-wider px-3 py-1 rounded-full"
                style={{
                  background: 'rgba(124,58,237,0.08)',
                  color: '#7c3aed',
                  border: '1px solid rgba(124,58,237,0.15)'
                }}>
                🛠️ {getRoleDisplayName(user?.role)}
              </span>
            </div>
          </div>

          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <div className="flex items-start gap-3">
              <div className="w-9 h-9 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-center text-slate-400 shrink-0">
                <Mail size={16} />
              </div>
              <div>
                <p className="text-[10px] uppercase font-bold text-slate-400">Adresse email</p>
                <p className="text-sm font-semibold text-slate-700 mt-0.5">{user?.email || '—'}</p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="w-9 h-9 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-center text-slate-400 shrink-0">
                <AtSign size={16} />
              </div>
              <div>
                <p className="text-[10px] uppercase font-bold text-slate-400">Identifiant Jira</p>
                <p className="text-sm font-semibold text-slate-700 mt-0.5">{jiraUsername || '—'}</p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="w-9 h-9 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-center text-slate-400 shrink-0">
                <User size={16} />
              </div>
              <div>
                <p className="text-[10px] uppercase font-bold text-slate-400">Nom complet</p>
                <p className="text-sm font-semibold text-slate-700 mt-0.5">{displayName || '—'}</p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="w-9 h-9 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-center text-slate-400 shrink-0">
                <Calendar size={16} />
              </div>
              <div>
                <p className="text-[10px] uppercase font-bold text-slate-400">Créé le</p>
                <p className="text-sm font-semibold text-slate-700 mt-0.5">{formatDate(dbProfile?.created_at)}</p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="w-9 h-9 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-center text-slate-400 shrink-0">
                <Clock size={16} />
              </div>
              <div>
                <p className="text-[10px] uppercase font-bold text-slate-400">Dernière connexion</p>
                <p className="text-sm font-semibold text-slate-700 mt-0.5">{formatDate(dbProfile?.last_login_at)}</p>
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* ── Admin : formulaire modifiable ─────────────────────────────────── */
        <div className="grid gap-6 md:grid-cols-3">
          <div className="md:col-span-1 space-y-6">
            <div className="bg-white rounded-3xl border border-slate-100 p-6 shadow-sm flex flex-col items-center text-center">
              <div className="w-20 h-20 rounded-full flex items-center justify-center text-white text-2xl font-bold mb-4 shadow-md"
                style={{ background: 'linear-gradient(135deg, #ef4444, #f43f5e, #f97316)' }}>
                {displayName ? displayName.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase() : 'U'}
              </div>
              <h3 className="font-bold text-brand-navy text-lg">{displayName || user?.email || 'Utilisateur'}</h3>
              <span className="inline-block mt-1 text-xs font-bold uppercase tracking-wider px-3 py-1 rounded-full"
                style={{
                  background: 'rgba(244,63,94,0.08)',
                  color: '#f43f5e',
                  border: '1px solid rgba(244,63,94,0.15)'
                }}>
                👑 Administrateur
              </span>

              <div className="w-full border-t border-gray-100 my-5 pt-4 text-left space-y-3">
                <div>
                  <p className="text-[10px] uppercase font-bold text-slate-400">Adresse Email</p>
                  <p className="text-sm font-semibold text-slate-700 mt-0.5 truncate">{user?.email || '—'}</p>
                </div>
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
                <div className="space-y-1">
                  <label className="text-xs uppercase font-bold text-slate-500">Adresse email</label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 transition focus:border-brand-rose focus:outline-none"
                    placeholder="admin@soprahr.com"
                    required
                  />
                </div>
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
      )}
    </div>
  )
}