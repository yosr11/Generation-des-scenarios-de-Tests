import React from 'react'
import { useAnalysisHistory } from '../hooks'
import { SkeletonLoader } from '../components/ui/Loader'
import { Badge } from '../components/ui/Badge'
import { Alert } from '../components/ui/Alert'
import { Button } from '../components/ui/Button'
import { Card, CardBody, CardHeader } from '../components/ui/Card'
import { useToast } from '../contexts/ToastContext'
import { History, Calendar, Cpu, ChevronRight, Clock, SearchX } from 'lucide-react'

export const HistoryPage: React.FC = () => {
  const [selectedStoryId, setSelectedStoryId] = React.useState<string>('')
  const [storySearch, setStorySearch] = React.useState('')
  const toast = useToast()

  const { data: analyses, loading: analysesLoading, error: analysesError } = useAnalysisHistory(
    selectedStoryId
  )

  const handleLoadHistory = () => {
    if (storySearch.trim()) {
      setSelectedStoryId(storySearch.trim().toUpperCase())
      toast.info(`Chargement de l'historique pour ${storySearch.trim().toUpperCase()}`)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleLoadHistory()
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-fade-in">

      {/* Page Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-2xl flex items-center justify-center flex-shrink-0"
          style={{ background: 'linear-gradient(135deg, #ec4899, #f97316)' }}>
          <History size={18} className="text-white" />
        </div>
        <div>
          <h1 className="text-2xl font-extrabold text-brand-navy">Historique</h1>
          <p className="text-sm text-brand-muted">Consultez les analyses passées et leurs résultats</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">

        {/* Search Panel */}
        <div className="lg:col-span-1 space-y-4">
          <Card>
            <CardHeader title="Rechercher" accent />
            <CardBody className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-brand-navy/70 uppercase tracking-widest mb-2">
                  Story ID
                </label>
                <input
                  type="text"
                  id="history-story-search"
                  placeholder="ex : NUXEPM-2144"
                  value={storySearch}
                  onChange={(e) => setStorySearch(e.target.value.toUpperCase())}
                  onKeyDown={handleKeyDown}
                  className="w-full px-4 py-3 border-2 border-gray-100 rounded-xl text-sm font-mono font-semibold text-brand-navy placeholder:text-gray-300 focus:border-brand-pink transition-all bg-white shadow-sm"
                />
              </div>
              <Button
                variant="primary"
                fullWidth
                onClick={handleLoadHistory}
                disabled={!storySearch.trim()}
                size="lg"
              >
                <History size={16} />
                Voir l'historique
              </Button>

              {selectedStoryId && (
                <div className="p-3 rounded-xl flex items-center gap-2"
                  style={{
                    background: 'rgba(236,72,153,0.06)',
                    border: '1px solid rgba(236,72,153,0.15)',
                  }}>
                  <Clock size={13} className="text-brand-pink flex-shrink-0" />
                  <div className="min-w-0">
                    <p className="text-[10px] text-brand-muted">Story active</p>
                    <p className="text-sm font-bold text-brand-navy font-mono truncate">{selectedStoryId}</p>
                  </div>
                </div>
              )}
            </CardBody>
          </Card>

          <div className="p-4 rounded-2xl text-sm"
            style={{
              background: 'linear-gradient(135deg, rgba(236,72,153,0.07), rgba(249,115,22,0.05))',
              border: '1px solid rgba(236,72,153,0.12)',
            }}>
            <p className="font-bold text-brand-navy mb-1 text-xs uppercase tracking-wider">📋 Historique</p>
            <p className="text-brand-muted text-xs leading-relaxed">
              Retrouvez toutes les analyses passées, leurs modèles utilisés et leurs statuts.
            </p>
          </div>
        </div>

        {/* Results */}
        <div className="lg:col-span-3">
          {selectedStoryId ? (
            <>
              {analysesError && (
                <Alert type="error" title="Erreur de chargement" description={analysesError.message} />
              )}
              {analysesLoading ? (
                <Card>
                  <CardBody className="p-6">
                    <SkeletonLoader />
                  </CardBody>
                </Card>
              ) : analyses && analyses.length > 0 ? (
                <Card>
                  <CardHeader
                    title={`Analyses — ${selectedStoryId}`}
                    accent
                    action={
                      <Badge variant="rose" dot size="sm">
                        {analyses.length} résultats
                      </Badge>
                    }
                  />
                  <div className="overflow-hidden">
                    <table className="premium-table w-full">
                      <thead>
                        <tr>
                          <th className="text-left">Modèle</th>
                          <th className="text-left">Date & Heure</th>
                          <th className="text-left">Statut</th>
                          <th className="text-left" />
                        </tr>
                      </thead>
                      <tbody>
                        {analyses.map((analysis: any, idx: number) => (
                          <tr key={idx} className="group">
                            <td>
                              <div className="flex items-center gap-3">
                                <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                                  style={{ background: 'linear-gradient(135deg, rgba(124,58,237,0.1), rgba(244,63,94,0.08))' }}>
                                  <Cpu size={13} className="text-brand-violet" />
                                </div>
                                <span className="font-semibold text-brand-navy text-sm">
                                  {analysis.model || 'N/A'}
                                </span>
                              </div>
                            </td>
                            <td>
                              <div className="flex items-center gap-2 text-brand-muted">
                                <Calendar size={13} className="text-gray-300" />
                                <span className="text-sm">
                                  {new Date(analysis.created_at).toLocaleString('fr-FR', {
                                    day: '2-digit', month: 'short', year: 'numeric',
                                    hour: '2-digit', minute: '2-digit',
                                  })}
                                </span>
                              </div>
                            </td>
                            <td>
                              <Badge
                                variant={analysis.status === 'success' ? 'success' : 'warning'}
                                dot
                                size="sm"
                              >
                                {analysis.status || 'en attente'}
                              </Badge>
                            </td>
                            <td>
                              <ChevronRight
                                size={14}
                                className="text-gray-200 group-hover:text-brand-violet transition-colors ml-auto"
                              />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Card>
              ) : (
                <Card>
                  <CardBody className="py-20 text-center">
                    <SearchX size={40} className="text-gray-200 mx-auto mb-3" />
                    <p className="text-brand-navy font-semibold mb-1">Aucune analyse trouvée</p>
                    <p className="text-brand-muted text-sm">Aucun résultat pour la story <span className="font-mono font-bold">{selectedStoryId}</span></p>
                  </CardBody>
                </Card>
              )}
            </>
          ) : (
            <Card>
              <CardBody className="py-24 text-center">
                <div className="w-16 h-16 mx-auto mb-4 rounded-3xl flex items-center justify-center"
                  style={{ background: 'linear-gradient(135deg, rgba(236,72,153,0.1), rgba(249,115,22,0.08))' }}>
                  <History size={28} className="text-brand-pink/50" />
                </div>
                <p className="text-brand-navy font-semibold mb-1">Sélectionnez une story</p>
                <p className="text-brand-muted text-sm">Entrez un ID de story pour consulter son historique d'analyses</p>
              </CardBody>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
