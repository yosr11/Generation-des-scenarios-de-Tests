import React, { useEffect, useState } from 'react'
import { apiClient } from '../api/client'
import { History, GitBranch, ChevronRight, Search, RefreshCw, Trash2 } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useToast } from '../contexts/ToastContext'

interface StoredStory {
  id: string
  summary: string
  status: string | null
  created_at: string
  tests_count?: number
}

export const HistoryPage: React.FC = () => {
  const [stories, setStories] = useState<StoredStory[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const navigate = useNavigate()
  const toast = useToast()

  const loadStories = async () => {
    setLoading(true)
    try {
      const data = await apiClient.db.listStories()
      setStories((data as unknown as StoredStory[]) || [])
    } catch (error: any) {
      toast.error(error?.message || 'Impossible de charger l\'historique')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadStories()
  }, [])

  const handleDelete = async (storyId: string) => {
    const confirmed = window.confirm(`Supprimer la story ${storyId} et toutes ses données enregistrées ?`)
    if (!confirmed) return

    try {
      await apiClient.db.deleteStory(storyId)
      setStories((current) => current.filter((story) => story.id !== storyId))
      toast.success(`Story ${storyId} supprimée`)
    } catch (error: any) {
      toast.error(error?.message || 'Échec de la suppression')
    }
  }

  const filtered = stories.filter(s =>
    s.id.toLowerCase().includes(search.toLowerCase()) ||
    (s.summary || '').toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Controls */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
          <input type="text" value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Rechercher une story…"
            className="w-full pl-10 pr-4 py-2.5 border-2 border-gray-100 rounded-xl text-sm text-brand-navy focus:border-brand-rose transition-all" />
        </div>
        <button type="button" onClick={() => { setLoading(true); apiClient.db.listStories().then((data: any) => setStories(data || [])).finally(() => setLoading(false)) }}
          className="p-2.5 rounded-xl border-2 border-gray-100 text-brand-muted hover:text-brand-navy hover:border-gray-200 transition-all">
          <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      {/* List */}
      <div className="bg-white rounded-3xl border border-gray-100 shadow-card overflow-hidden">
        <div className="h-1" style={{ background: 'linear-gradient(90deg,#ef4444,#f43f5e,#f97316)' }} />
        <div className="px-6 py-4 border-b border-gray-100 flex items-center gap-3">
          <History size={16} className="text-brand-rose" />
          <h3 className="font-bold text-brand-navy">Stories Traitées</h3>
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
          <div className="py-20 text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-3xl flex items-center justify-center"
              style={{ background: 'rgba(244,63,94,0.06)' }}>
              <GitBranch size={28} className="text-brand-rose/40" />
            </div>
            <p className="text-brand-navy font-semibold mb-1">
              {search ? 'Aucun résultat' : 'Aucune story traitée'}
            </p>
            <p className="text-brand-muted text-sm">
              {search
                ? 'Modifiez votre recherche.'
                : 'Lancez votre premier pipeline pour voir l\'historique ici.'}
            </p>
            {!search && (
              <button type="button" onClick={() => navigate('/pipeline')}
                className="mt-5 px-6 py-3 rounded-xl text-sm font-bold text-white transition-all hover:-translate-y-0.5"
                style={{ background: 'linear-gradient(135deg,#ef4444,#f43f5e,#f97316)', boxShadow: '0 4px 16px rgba(244,63,94,0.35)' }}>
                → Lancer un pipeline
              </button>
            )}
          </div>
        ) : (
          <ul className="divide-y divide-gray-50">
            {filtered.map(story => (
              <li key={story.id}
                className="flex items-center gap-4 px-6 py-4 hover:bg-gray-50/70 transition-colors cursor-pointer group"
                onClick={() => navigate(`/history/${story.id}`)}>
                <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
                  style={{ background: 'rgba(244,63,94,0.08)', border: '1px solid rgba(244,63,94,0.15)' }}>
                  <GitBranch size={16} className="text-brand-rose" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold px-2 py-0.5 rounded-lg"
                      style={{ background: 'rgba(244,63,94,0.08)', color: '#f43f5e' }}>
                      {story.id}
                    </span>
                    {story.status && (
                      <span className="text-xs text-brand-muted capitalize">{story.status}</span>
                    )}
                  </div>
                  {story.summary && (
                    <p className="text-sm text-brand-navy font-medium mt-0.5 truncate">{story.summary}</p>
                  )}
                </div>
                <div className="flex items-center gap-3 flex-shrink-0">
                  <div className="text-right">
                    <p className="text-xs text-brand-muted">
                      {story.created_at
                        ? new Date(story.created_at).toLocaleDateString('fr-FR')
                        : '—'}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation()
                      handleDelete(story.id)
                    }}
                    className="rounded-full p-2 text-brand-muted hover:text-brand-rose hover:bg-red-50 transition"
                    aria-label={`Supprimer ${story.id}`}
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
                <ChevronRight size={16} className="text-gray-300 group-hover:text-brand-muted transition-colors flex-shrink-0" />
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
