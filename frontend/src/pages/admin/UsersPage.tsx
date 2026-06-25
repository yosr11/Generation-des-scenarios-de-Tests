import React, { useCallback, useEffect, useState } from 'react'
import { apiClient } from '../../api/client'
import { useToast } from '../../contexts/ToastContext'
import {
  Plus, Pencil, Trash2, UserCheck, UserX, X, Save, Eye, EyeOff,
  Users, Search, RefreshCw
} from 'lucide-react'
import { Badge } from '../../components/ui/Badge'

interface User {
  id: number
  email: string
  role: string
  display_name: string | null
  jira_username: string | null
  is_active: boolean
  last_login_at: string | null
  created_at: string | null
}

/* ── Modal ── */
const UserModal: React.FC<{
  user?: User | null
  onClose: () => void
  onSaved: () => void
}> = ({ user, onClose, onSaved }) => {
  const toast = useToast()
  const isEdit = !!user
  const [form, setForm] = useState({
    email: user?.email || '',
    password: '',
    role: user?.role || 'tester',
    display_name: user?.display_name || '',
    jira_username: user?.jira_username || '',
  })
  const [showPwd, setShowPwd] = useState(false)
  const [saving, setSaving] = useState(false)

  const set = (k: string, v: string) => setForm(p => ({ ...p, [k]: v }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      if (isEdit) {
        await apiClient.admin.updateUser(user!.id, {
          display_name: form.display_name || undefined,
          jira_username: form.jira_username || undefined,
          password: form.password || undefined,
          role: form.role,
        })
        toast.success('Utilisateur modifié !')
      } else {
        await apiClient.admin.createUser({
          email: form.email,
          password: form.password || '__jira__',
          role: form.role,
          display_name: form.display_name || undefined,
          jira_username: form.jira_username || undefined,
        })
        toast.success('Utilisateur créé !')
      }
      onSaved()
    } catch (err: any) {
      toast.error(err?.message || 'Erreur')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[9999]" onClick={(e) => { e.stopPropagation() }}>
      <div className="absolute inset-0 bg-brand-navy/50 backdrop-blur-sm" onClick={onClose} />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-md bg-white rounded-3xl overflow-hidden"
        style={{ boxShadow: '0 25px 60px rgba(10,15,46,0.3)', zIndex: 1 }}
        onClick={(e) => e.stopPropagation()}>

        {/* Header */}
        <div className="px-6 py-5 flex items-center gap-3"
          style={{ background: 'linear-gradient(135deg,#0a0f2e,#1a1f4e)' }}>
          <div className="flex-1">
            <h3 className="font-bold text-white">{isEdit ? 'Modifier l\'utilisateur' : 'Créer un utilisateur'}</h3>
            <p className="text-xs text-white/40 mt-0.5">{isEdit ? user!.email : 'Nouveau compte'}</p>
          </div>
          <button type="button" onClick={onClose}
            className="p-2 rounded-xl text-white/40 hover:text-white hover:bg-white/10 transition-all">
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Email — only on create */}
          {!isEdit && (
            <div>
              <label className="block text-xs font-bold text-brand-navy/60 uppercase tracking-widest mb-2">Email *</label>
              <input type="email" required value={form.email} onChange={e => set('email', e.target.value)}
                placeholder="user@soprahr.com"
                className="w-full px-4 py-3 border-2 border-gray-100 rounded-xl text-sm text-brand-navy focus:border-brand-rose transition-all" />
            </div>
          )}

          {/* Display name */}
          <div>
            <label className="block text-xs font-bold text-brand-navy/60 uppercase tracking-widest mb-2">Nom d'affichage</label>
            <input type="text" value={form.display_name} onChange={e => set('display_name', e.target.value)}
              placeholder="Prénom Nom"
              className="w-full px-4 py-3 border-2 border-gray-100 rounded-xl text-sm text-brand-navy focus:border-brand-violet transition-all" />
          </div>

          {/* Jira username */}
          <div>
            <label className="block text-xs font-bold text-brand-navy/60 uppercase tracking-widest mb-2">
              Identifiant Jira
              <span className="ml-2 text-[10px] text-brand-muted normal-case font-normal">(pour les testeurs)</span>
            </label>
            <input type="text" value={form.jira_username} onChange={e => set('jira_username', e.target.value)}
              placeholder="prenom.nom"
              className="w-full px-4 py-3 border-2 border-gray-100 rounded-xl text-sm font-mono text-brand-navy focus:border-brand-orange transition-all" />
          </div>

          {/* Role */}
          <div>
            <label className="block text-xs font-bold text-brand-navy/60 uppercase tracking-widest mb-2">Rôle</label>
            <div className="flex gap-3">
              {(['tester', 'admin'] as const).map(r => (
                <button key={r} type="button" onClick={() => set('role', r)}
                  className={`flex-1 py-3 rounded-xl text-sm font-semibold border-2 transition-all ${
                    form.role === r
                      ? 'text-white border-transparent'
                      : 'text-brand-navy border-gray-100 hover:border-gray-200'
                  }`}
                  style={form.role === r ? {
                    background: r === 'admin'
                      ? 'linear-gradient(135deg,#ef4444,#f43f5e)'
                      : 'linear-gradient(135deg,#7c3aed,#ec4899)',
                  } : {}}>
                  {r === 'admin' ? '👑 Admin' : '👤 Testeur'}
                </button>
              ))}
            </div>
          </div>

          {/* Password */}
          <div>
            <label className="block text-xs font-bold text-brand-navy/60 uppercase tracking-widest mb-2">
              {isEdit ? 'Nouveau mot de passe (laisser vide pour ne pas changer)' : 'Mot de passe'}
            </label>
            <div className="relative">
              <input type={showPwd ? 'text' : 'password'} value={form.password}
                onChange={e => set('password', e.target.value)}
                placeholder={isEdit ? '••••••••' : 'Min. 6 caractères'}
                className="w-full pl-4 pr-11 py-3 border-2 border-gray-100 rounded-xl text-sm text-brand-navy focus:border-brand-rose transition-all" />
              <button type="button" onClick={() => setShowPwd(!showPwd)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-brand-muted hover:text-brand-navy transition-colors">
                {showPwd ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="flex-1 py-3 rounded-xl border-2 border-gray-100 text-sm font-semibold text-brand-navy hover:border-gray-200 transition-all">
              Annuler
            </button>
            <button type="submit" disabled={saving}
              className="flex-1 py-3 rounded-xl text-sm font-bold text-white flex items-center justify-center gap-2 transition-all hover:-translate-y-0.5 disabled:opacity-50"
              style={{ background: 'linear-gradient(135deg,#ef4444,#f43f5e,#f97316)', boxShadow: '0 4px 16px rgba(244,63,94,0.35)' }}>
              {saving
                ? <><span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Sauvegarde…</>
                : <><Save size={15} /> {isEdit ? 'Modifier' : 'Créer'}</>}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

/* ── Main Page ── */
export const UsersPage: React.FC = () => {
  const toast = useToast()
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [modalUser, setModalUser] = useState<User | null | undefined>(undefined) // undefined=closed, null=new, User=edit
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const [togglingId, setTogglingId] = useState<number | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try { setUsers(await apiClient.admin.listUsers()) }
    catch (err: any) { toast.error(err?.message || 'Erreur chargement') }
    finally { setLoading(false) }
  }, [toast])

  useEffect(() => { load() }, [load])

  const handleToggle = async (user: User) => {
    setTogglingId(user.id)
    try {
      if (user.is_active) await apiClient.admin.deactivateUser(user.id)
      else await apiClient.admin.activateUser(user.id)
      toast.success(user.is_active ? 'Compte désactivé' : 'Compte activé')
      await load()
    } catch (err: any) { toast.error(err?.message || 'Erreur') }
    finally { setTogglingId(null) }
  }

  const handleDelete = async (user: User) => {
    if (!confirm(`Supprimer ${user.email} ? Cette action est irréversible.`)) return
    setDeletingId(user.id)
    try {
      await apiClient.admin.deleteUser(user.id)
      toast.success('Utilisateur supprimé')
      await load()
    } catch (err: any) { toast.error(err?.message || 'Erreur') }
    finally { setDeletingId(null) }
  }

  const filtered = users.filter(u =>
    [u.email, u.display_name, u.jira_username, u.role].some(v =>
      v?.toLowerCase().includes(search.toLowerCase())
    )
  )

  return (
    <>
      <div className="space-y-5 animate-fade-in">
        {/* Header actions */}
        <div className="flex items-center gap-3">
          <div className="relative flex-1 max-w-xs">
            <Search size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
            <input type="text" value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Rechercher un utilisateur…"
              className="w-full pl-10 pr-4 py-2.5 border-2 border-gray-100 rounded-xl text-sm text-brand-navy focus:border-brand-rose transition-all" />
          </div>
          <button type="button" onClick={load} disabled={loading}
            className="p-2.5 rounded-xl border-2 border-gray-100 text-brand-muted hover:text-brand-navy hover:border-gray-200 transition-all">
            <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
          </button>
          <button type="button" onClick={() => setModalUser(null)}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-bold text-white transition-all hover:-translate-y-0.5"
            style={{ background: 'linear-gradient(135deg,#ef4444,#f43f5e,#f97316)', boxShadow: '0 4px 16px rgba(244,63,94,0.35)' }}>
            <Plus size={15} /> Créer un utilisateur
          </button>
        </div>

        {/* Table */}
        <div className="bg-white rounded-3xl border border-gray-100 shadow-card overflow-hidden">
          <div className="h-1" style={{ background: 'linear-gradient(90deg,#ef4444,#f43f5e,#ec4899,#7c3aed)' }} />
          <div className="px-6 py-4 border-b border-gray-100 flex items-center gap-3">
            <Users size={16} className="text-brand-rose" />
            <h3 className="font-bold text-brand-navy">Utilisateurs</h3>
            <span className="ml-auto px-2.5 py-0.5 rounded-full text-xs font-bold"
              style={{ background: 'rgba(244,63,94,0.08)', color: '#f43f5e' }}>
              {filtered.length}
            </span>
          </div>

          {loading ? (
            <div className="py-16 text-center">
              <div className="w-8 h-8 mx-auto border-2 border-t-brand-rose border-transparent rounded-full animate-spin mb-3" />
              <p className="text-brand-muted text-sm">Chargement…</p>
            </div>
          ) : filtered.length === 0 ? (
            <div className="py-16 text-center text-brand-muted text-sm">
              {search ? 'Aucun résultat pour cette recherche.' : 'Aucun utilisateur enregistré.'}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 bg-gray-50/60">
                    {['Utilisateur', 'Jira ID', 'Rôle', 'Statut', 'Dernière connexion', 'Actions'].map(h => (
                      <th key={h} className="text-left py-3 px-4 text-[10px] font-bold text-brand-navy/50 uppercase tracking-widest">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filtered.map(u => (
                    <tr key={u.id} className="border-b border-gray-50 hover:bg-gray-50/60 transition-colors">
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-lg flex items-center justify-center text-white text-xs font-bold flex-shrink-0"
                            style={{ background: u.role === 'admin' ? 'linear-gradient(135deg,#ef4444,#f43f5e)' : 'linear-gradient(135deg,#7c3aed,#ec4899)' }}>
                            {(u.display_name || u.email || 'U').split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase()}
                          </div>
                          <div>
                            <p className="font-semibold text-brand-navy">{u.display_name || u.email}</p>
                            <p className="text-xs text-brand-muted">{u.email}</p>
                          </div>
                        </div>
                      </td>
                      <td className="py-3.5 px-4">
                        <span className="font-mono text-xs text-brand-navy">{u.jira_username || '—'}</span>
                      </td>
                      <td className="py-3.5 px-4">
                        <span className="inline-block px-2.5 py-1 rounded-full text-[10px] font-bold uppercase"
                          style={{
                            background: u.role === 'admin' ? 'rgba(244,63,94,0.08)' : 'rgba(124,58,237,0.08)',
                            color: u.role === 'admin' ? '#f43f5e' : '#7c3aed',
                          }}>
                          {u.role === 'admin' ? '👑 Admin' : '👤 Testeur'}
                        </span>
                      </td>
                      <td className="py-3.5 px-4">
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase"
                          style={{
                            background: u.is_active ? 'rgba(16,185,129,0.08)' : 'rgba(100,116,139,0.08)',
                            color: u.is_active ? '#10b981' : '#64748b',
                          }}>
                          <span className={`w-1.5 h-1.5 rounded-full ${u.is_active ? 'bg-emerald-500' : 'bg-gray-400'}`} />
                          {u.is_active ? 'Actif' : 'Désactivé'}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-xs text-brand-muted">
                        {u.last_login_at
                          ? new Date(u.last_login_at).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })
                          : 'Jamais'}
                      </td>
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-1.5">
                          {/* Edit */}
                          <button type="button" onClick={() => setModalUser(u)}
                            className="p-2 rounded-xl text-brand-muted hover:text-brand-violet hover:bg-brand-violet/08 transition-all"
                            title="Modifier">
                            <Pencil size={14} />
                          </button>
                          {/* Toggle active */}
                          <button type="button" onClick={() => handleToggle(u)} disabled={togglingId === u.id}
                            className={`p-2 rounded-xl transition-all ${u.is_active ? 'text-amber-500 hover:bg-amber-50' : 'text-emerald-600 hover:bg-emerald-50'}`}
                            title={u.is_active ? 'Désactiver' : 'Activer'}>
                            {togglingId === u.id
                              ? <span className="w-3.5 h-3.5 border-2 border-current/30 border-t-current rounded-full animate-spin block" />
                              : u.is_active ? <UserX size={14} /> : <UserCheck size={14} />}
                          </button>
                          {/* Delete */}
                          <button type="button" onClick={() => handleDelete(u)} disabled={deletingId === u.id}
                            className="p-2 rounded-xl text-brand-muted hover:text-brand-rose hover:bg-brand-rose/08 transition-all"
                            title="Supprimer">
                            {deletingId === u.id
                              ? <span className="w-3.5 h-3.5 border-2 border-brand-rose/30 border-t-brand-rose rounded-full animate-spin block" />
                              : <Trash2 size={14} />}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Modal */}
      {modalUser !== undefined && (
        <UserModal
          user={modalUser}
          onClose={() => setModalUser(undefined)}
          onSaved={() => { setModalUser(undefined); load() }}
        />
      )}
    </>
  )
}
