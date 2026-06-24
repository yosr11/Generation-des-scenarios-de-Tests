import React from 'react'
import { useAnalysis, useAgent5Report } from '../hooks'
import { Loader } from '../components/ui/Loader'
import { Alert } from '../components/ui/Alert'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Card, CardBody, CardHeader } from '../components/ui/Card'
import { useToast } from '../contexts/ToastContext'
import {
  Search, CheckSquare, FileBarChart2, Sparkles,
  ChevronRight, Circle
} from 'lucide-react'

export const AnalysisPage: React.FC = () => {
  const [storyId, setStoryId] = React.useState('')
  const [submitted, setSubmitted] = React.useState(false)
  const toast = useToast()

  const analysis = useAnalysis(storyId)
  const report = useAgent5Report(submitted ? storyId : undefined)

  const handleAnalyze = async () => {
    if (!storyId.trim()) return
    setSubmitted(true)
    try {
      await analysis.run({ use_rag: true })
      toast.success('Analyse terminée !')
    } catch (err: any) {
      toast.error(err?.message || 'Échec de l\'analyse')
    }
  }

  const handleGenerateReport = async () => {
    try {
      await report.generate({ include_recommendations: true })
      toast.success('Rapport généré avec succès')
    } catch (err: any) {
      toast.error(err?.message || 'Échec de la génération du rapport')
    }
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-fade-in">

      {/* Page Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-2xl flex items-center justify-center flex-shrink-0"
          style={{ background: 'var(--grad-violet)' }}>
          <Search size={18} className="text-white" />
        </div>
        <div>
          <h1 className="text-2xl font-extrabold text-brand-navy">Analyse & Rapport</h1>
          <p className="text-sm text-brand-muted">Analyse approfondie et génération de rapports Agent 5</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">

        {/* Control Panel */}
        <div className="lg:col-span-1 space-y-4">
          <Card>
            <CardHeader title="Paramètres" accent />
            <CardBody className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-brand-navy/70 uppercase tracking-widest mb-2">
                  Story ID
                </label>
                <input
                  type="text"
                  id="analysis-story-id"
                  placeholder="ex : NUXEPM-2144"
                  value={storyId}
                  onChange={(e) => setStoryId(e.target.value.toUpperCase())}
                  className="w-full px-4 py-3 border-2 border-gray-100 rounded-xl text-sm font-mono font-semibold text-brand-navy placeholder:text-gray-300 focus:border-brand-violet transition-all bg-white shadow-sm"
                />
              </div>
              <Button
                variant="violet"
                fullWidth
                disabled={!storyId.trim()}
                isLoading={analysis.loading}
                onClick={handleAnalyze}
                size="lg"
              >
                <Search size={16} />
                Analyser
              </Button>
            </CardBody>
          </Card>

          {/* Tip */}
          <div className="p-4 rounded-2xl text-sm"
            style={{
              background: 'linear-gradient(135deg, rgba(124,58,237,0.07), rgba(236,72,153,0.05))',
              border: '1px solid rgba(124,58,237,0.12)',
            }}>
            <p className="font-bold text-brand-navy mb-1 text-xs uppercase tracking-wider">✨ Analyse IA</p>
            <p className="text-brand-muted text-xs leading-relaxed">
              L'agent analyse la story et identifie tous les points testables avec une précision maximale.
            </p>
          </div>
        </div>

        {/* Results */}
        <div className="lg:col-span-3 space-y-4">

          {analysis.error && (
            <Alert type="error" title="Erreur d'analyse" description={analysis.error.message} />
          )}

          {analysis.loading ? (
            <Card>
              <CardBody className="py-20">
                <div className="flex flex-col items-center gap-4">
                  <div className="relative w-16 h-16">
                    <div className="absolute inset-0 rounded-full border-2 border-brand-violet/20" />
                    <div className="absolute inset-0 rounded-full border-2 border-t-brand-violet border-r-transparent border-b-transparent border-l-transparent animate-spin" />
                    <Search size={20} className="absolute inset-0 m-auto text-brand-violet" />
                  </div>
                  <p className="text-brand-navy font-semibold">Analyse de la story en cours...</p>
                  <p className="text-brand-muted text-sm">L'agent IA scrute chaque détail</p>
                </div>
              </CardBody>
            </Card>
          ) : analysis.data ? (
            <>
              {/* Testable Points */}
              {analysis.data.testable_points && (
                <Card>
                  <CardHeader
                    title="Points Testables Identifiés"
                    accent
                    action={
                      <Badge variant="violet" dot size="sm">
                        {analysis.data.testable_points.length} points
                      </Badge>
                    }
                  />
                  <CardBody className="p-0">
                    <ul className="divide-y divide-gray-50">
                      {analysis.data.testable_points.map((point: string, idx: number) => (
                        <li
                          key={idx}
                          className="px-6 py-3.5 flex items-start gap-3 hover:bg-brand-violet/2 transition-colors group"
                        >
                          <div className="w-6 h-6 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5"
                            style={{ background: 'linear-gradient(135deg, rgba(244,63,94,0.12), rgba(249,115,22,0.08))' }}>
                            <CheckSquare size={12} className="text-brand-rose" />
                          </div>
                          <span className="text-sm text-brand-navy leading-relaxed group-hover:text-brand-violet transition-colors">
                            {point}
                          </span>
                          <ChevronRight size={14} className="text-gray-200 group-hover:text-brand-violet ml-auto flex-shrink-0 mt-0.5 transition-colors" />
                        </li>
                      ))}
                    </ul>
                  </CardBody>
                </Card>
              )}

              {/* Generate Report Button */}
              {submitted && !report.data && (
                <Card>
                  <CardBody className="flex items-center gap-4">
                    <div className="flex-1">
                      <p className="font-bold text-brand-navy text-sm">Générer le Rapport Agent 5</p>
                      <p className="text-brand-muted text-xs mt-0.5">Rapport complet avec recommandations</p>
                    </div>
                    <Button
                      variant="primary"
                      isLoading={report.loading}
                      onClick={handleGenerateReport}
                    >
                      <FileBarChart2 size={16} />
                      Générer
                    </Button>
                  </CardBody>
                </Card>
              )}

              {/* Report Results */}
              {report.data && (
                <Card>
                  <CardHeader
                    title="Rapport Généré"
                    accent
                    action={<Badge variant="success" dot>Complet</Badge>}
                  />
                  <CardBody className="space-y-5">
                    {/* Verdict */}
                    <div className="flex items-center gap-4 p-4 rounded-xl"
                      style={{
                        background: report.data.verdict === 'APPROVED'
                          ? 'rgba(16,185,129,0.06)'
                          : 'rgba(249,115,22,0.06)',
                        border: `1px solid ${report.data.verdict === 'APPROVED' ? 'rgba(16,185,129,0.2)' : 'rgba(249,115,22,0.2)'}`,
                      }}>
                      <Sparkles
                        size={20}
                        className={report.data.verdict === 'APPROVED' ? 'text-emerald-500' : 'text-brand-orange'}
                      />
                      <div className="flex-1">
                        <p className="text-xs font-bold text-brand-navy/60 uppercase tracking-widest mb-1">Verdict</p>
                        <Badge
                          variant={
                            report.data.verdict === 'APPROVED'       ? 'success' :
                            report.data.verdict === 'REQUIRES_REVIEW' ? 'warning' : 'error'
                          }
                          dot
                        >
                          {report.data.verdict}
                        </Badge>
                      </div>
                    </div>

                    {/* Summary */}
                    <div>
                      <p className="text-xs font-bold text-brand-navy/60 uppercase tracking-widest mb-2">Résumé</p>
                      <p className="text-sm text-brand-muted leading-relaxed bg-gray-50 rounded-xl p-4">
                        {report.data.summary}
                      </p>
                    </div>
                  </CardBody>
                </Card>
              )}
            </>
          ) : (
            <Card>
              <CardBody className="py-20 text-center">
                <div className="w-16 h-16 mx-auto mb-4 rounded-3xl flex items-center justify-center"
                  style={{ background: 'linear-gradient(135deg, rgba(124,58,237,0.1), rgba(236,72,153,0.08))' }}>
                  <Search size={28} className="text-brand-violet/50" />
                </div>
                <p className="text-brand-navy font-semibold mb-1">Prêt pour l'analyse</p>
                <p className="text-brand-muted text-sm">
                  {submitted ? 'Aucun résultat disponible' : 'Entrez un ID de story et cliquez sur « Analyser »'}
                </p>
              </CardBody>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
