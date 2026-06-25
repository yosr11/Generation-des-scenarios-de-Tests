import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useStory, useAnalysisHistory } from '../hooks'
import { apiClient, StoredStory } from '../api/client'
import { useToast } from '../contexts/ToastContext'
import { ArrowLeft, Trash2, FileText, Layers, Sparkles, Search } from 'lucide-react'
import { Badge } from '../components/ui/Badge'
import { Alert } from '../components/ui/Alert'

export const StoryDetailPage: React.FC = () => {
  const { storyId } = useParams<{ storyId: string }>()
  const navigate = useNavigate()
  const toast = useToast()

  const story = useStory<StoredStory>(storyId || '', true)
  const analyses = useAnalysisHistory(storyId || '')
  const [selectedIndex, setSelectedIndex] = useState(0)

  useEffect(() => {
    if (analyses.data && analyses.data.length > 0) {
      setSelectedIndex(0)
    }
  }, [analyses.data])

  const handleDeleteStory = async () => {
    if (!storyId) return
    const confirmed = window.confirm(`Supprimer la story ${storyId} et toutes ses données enregistrées ?`)
    if (!confirmed) return

    try {
      await apiClient.db.deleteStory(storyId)
      toast.success(`Story ${storyId} supprimée`)
      navigate('/history')
    } catch (error: any) {
      toast.error(error?.message || 'Échec de la suppression')
    }
  }

  const selectedAnalysis = analyses.data?.[selectedIndex]

  return (
    <div className="space-y-5 animate-fade-in max-w-6xl mx-auto">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-3">
          <button
            type="button"
            onClick={() => navigate('/history')}
            className="inline-flex items-center gap-2 text-sm font-semibold text-brand-rose"
          >
            <ArrowLeft size={16} /> Retour à l'historique
          </button>
          <div>
            <p className="text-xs uppercase tracking-widest text-brand-violet/80 font-bold">Story enregistrée</p>
            <h1 className="text-3xl font-extrabold text-brand-navy">{storyId}</h1>
          </div>
        </div>
        <button
          type="button"
          onClick={handleDeleteStory}
          className="inline-flex items-center gap-2 rounded-2xl bg-brand-rose/10 px-4 py-3 text-sm font-semibold text-brand-rose transition hover:bg-brand-rose/15"
        >
          <Trash2 size={16} /> Supprimer
        </button>
      </div>

      {story.error && (
        <Alert type="error" title="Impossible de charger la story" description={story.error.message || 'Vérifiez l\'ID et réessayez.'} />
      )}

      <div className="grid gap-6 lg:grid-cols-[1.4fr_0.9fr]">
        <div className="space-y-6">
          <div className="bg-white rounded-3xl border border-gray-100 shadow-card p-6">
            <div className="flex flex-col gap-4">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-2 mb-4">
                    <span className="font-mono text-xs font-bold uppercase tracking-[0.2em] px-3 py-1 rounded-full bg-brand-rose/10 text-brand-rose">
                      {storyId}
                    </span>
                    {story.data?.status && (
                      <Badge variant="success">{story.data.status}</Badge>
                    )}
                  </div>
                  <h2 className="text-xl font-bold text-brand-navy">{story.data?.summary || 'Aucune synthèse disponible'}</h2>
                  <p className="mt-3 text-sm text-brand-muted leading-relaxed">
                    {story.data?.description_clean || story.data?.description_raw || 'Aucune description enregistrée.'}
                  </p>
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-3">
                <div className="rounded-3xl bg-slate-50 p-4">
                  <p className="text-[11px] uppercase tracking-[0.18em] text-brand-navy/60">Créée le</p>
                  <p className="mt-2 text-sm font-semibold text-brand-navy">
                    {story.data?.created_at
                      ? new Date(story.data.created_at).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })
                      : '—'}
                  </p>
                </div>
                <div className="rounded-3xl bg-slate-50 p-4">
                  <p className="text-[11px] uppercase tracking-[0.18em] text-brand-navy/60">Critères</p>
                  <p className="mt-2 text-sm text-brand-muted">
                    {story.data?.acceptance_criteria_clean
                      ? `${story.data.acceptance_criteria_clean}`
                      : 'Aucun critère enregistré'}
                  </p>
                </div>
                <div className="rounded-3xl bg-slate-50 p-4">
                  <p className="text-[11px] uppercase tracking-[0.18em] text-brand-navy/60">Étiquette(s)</p>
                  <p className="mt-2 text-sm text-brand-muted">
                    {story.data?.labels?.length ? story.data.labels.join(', ') : 'Aucune'}
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-3xl border border-gray-100 shadow-card p-6">
            <div className="flex items-center gap-3 mb-4">
              <Layers size={18} className="text-brand-violet" />
              <div>
                <p className="text-sm font-bold text-brand-navy">Résumé de l'analyse</p>
                <p className="text-xs text-brand-muted">Données stockées en base pour cette story</p>
              </div>
            </div>

            {analyses.loading ? (
              <div className="py-14 text-center">
                <div className="inline-block animate-spin mb-4">
                  <svg className="w-10 h-10 text-brand-rose" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                </div>
                <p className="text-sm text-brand-muted">Chargement des analyses...</p>
              </div>
            ) : analyses.error ? (
              <Alert type="error" title="Erreur" description={analyses.error.message || 'Impossible de charger les analyses.'} />
            ) : !analyses.data?.length ? (
              <div className="rounded-3xl border border-dashed border-slate-200 p-8 text-center text-sm text-brand-muted">
                Aucune analyse stockée pour cette story. Lancez le pipeline pour en créer une.
              </div>
            ) : selectedAnalysis ? (
              <div className="space-y-6">
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="rounded-3xl bg-slate-50 p-4">
                    <p className="text-[11px] uppercase tracking-[0.18em] text-brand-navy/60">Modèle</p>
                    <p className="mt-2 text-sm font-semibold text-brand-navy">{selectedAnalysis.model || '—'}</p>
                  </div>
                  <div className="rounded-3xl bg-slate-50 p-4">
                    <p className="text-[11px] uppercase tracking-[0.18em] text-brand-navy/60">Créée le</p>
                    <p className="mt-2 text-sm font-semibold text-brand-navy">
                      {selectedAnalysis.created_at
                        ? new Date(selectedAnalysis.created_at).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })
                        : '—'}
                    </p>
                  </div>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  {selectedAnalysis.story_type && (
                    <div className="rounded-3xl bg-white border border-slate-100 p-4">
                      <p className="text-xs uppercase tracking-[0.18em] text-brand-navy/60">Type de story</p>
                      <p className="mt-2 text-sm font-semibold text-brand-navy">{selectedAnalysis.story_type}</p>
                    </div>
                  )}
                  {selectedAnalysis.actors && selectedAnalysis.actors.length > 0 && (
                    <div className="rounded-3xl bg-white border border-slate-100 p-4">
                      <p className="text-xs uppercase tracking-[0.18em] text-brand-navy/60">Acteurs</p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {selectedAnalysis.actors.map((actor: string, index: number) => (
                          <span key={index} className="rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700">
                            {actor}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {selectedAnalysis.testable_points && selectedAnalysis.testable_points.length > 0 && (
                  <div className="rounded-3xl bg-white border border-slate-100 p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <Sparkles size={16} className="text-brand-orange" />
                      <p className="text-sm font-semibold text-brand-navy">Points testables</p>
                    </div>
                    <ul className="grid gap-2">
                      {selectedAnalysis.testable_points.map((point: string, index: number) => (
                        <li key={index} className="rounded-2xl bg-slate-50 px-4 py-3 text-sm text-brand-navy">
                          {point}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {(selectedAnalysis.acceptance_criteria_explicit || selectedAnalysis.acceptance_criteria_inferred) && (
                  <div className="rounded-3xl bg-white border border-slate-100 p-4">
                    <p className="text-sm font-semibold text-brand-navy mb-3">Critères d'acceptation</p>
                    {selectedAnalysis.acceptance_criteria_explicit && (
                      <div className="mb-3">
                        <p className="text-xs uppercase tracking-[0.18em] text-brand-navy/60">Explicites</p>
                        <p className="mt-2 text-sm text-brand-muted leading-relaxed">{selectedAnalysis.acceptance_criteria_explicit}</p>
                      </div>
                    )}
                    {selectedAnalysis.acceptance_criteria_inferred && (
                      <div>
                        <p className="text-xs uppercase tracking-[0.18em] text-brand-navy/60">Inférés</p>
                        <p className="mt-2 text-sm text-brand-muted leading-relaxed">{selectedAnalysis.acceptance_criteria_inferred}</p>
                      </div>
                    )}
                  </div>
                )}

                <div className="rounded-3xl bg-slate-50 p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <FileText size={16} className="text-brand-violet" />
                    <p className="text-sm font-semibold text-brand-navy">Données brutes</p>
                  </div>
                  <pre className="max-h-64 overflow-auto rounded-3xl bg-white p-4 text-xs text-slate-700">
                    {JSON.stringify(selectedAnalysis, null, 2)}
                  </pre>
                </div>
              </div>
            ) : null}
          </div>
        </div>

        <div className="space-y-4">
          <div className="bg-white rounded-3xl border border-gray-100 shadow-card p-6">
            <div className="flex items-center gap-3 mb-4">
              <Search size={18} className="text-brand-rose" />
              <div>
                <p className="text-sm font-bold text-brand-navy">Analyses disponibles</p>
                <p className="text-xs text-brand-muted">Sélectionnez une version enregistrée</p>
              </div>
            </div>

            {analyses.data?.map((analysis, index) => (
              <button
                key={`${analysis.model}-${analysis.created_at}-${index}`}
                type="button"
                onClick={() => setSelectedIndex(index)}
                className={`w-full text-left rounded-3xl border px-4 py-4 mb-3 transition ${selectedIndex === index ? 'border-brand-rose bg-brand-rose/5' : 'border-slate-200 bg-white hover:border-brand-rose/60 hover:bg-slate-50'}`}
              >
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-brand-navy">{analysis.model || 'Analyse'}</p>
                    <p className="text-xs text-brand-muted mt-1">
                      {analysis.created_at
                        ? new Date(analysis.created_at).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })
                        : 'Date inconnue'}
                    </p>
                  </div>
                  <Badge variant={selectedIndex === index ? 'success' : 'default'}>
                    {analysis.story_type || 'Analyse'}
                  </Badge>
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
