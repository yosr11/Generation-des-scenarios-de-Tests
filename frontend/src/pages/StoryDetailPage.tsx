import React, { useEffect, useState, useCallback } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useStory, useAnalysisHistory } from '../hooks'
import { apiClient, StoredStory } from '../api/client'
import { useToast } from '../contexts/ToastContext'
import {
  ArrowLeft, Trash2, FileText, CheckCircle2, Cpu, Clock, XCircle,
  TestTube, FileBarChart2, HelpCircle, AlertTriangle, ArrowRight, Printer, Sparkles, Upload
} from 'lucide-react'
import { Badge } from '../components/ui/Badge'
import { Alert } from '../components/ui/Alert'

// ── Colors & Styles matching PipelinePage ──────────────────────────────────
const NAV       = '#0B1E3E'
const NAV_LIGHT = '#1A3A6B'
const ROSE      = '#DB2777'
const ORANGE    = '#EA580C'
const VIOLET    = '#1D4ED8'

const MAIN_GRADIENT = `linear-gradient(90deg, ${NAV}, ${NAV_LIGHT}, ${VIOLET}, ${ROSE}, ${ORANGE})`
const CARD_GRADIENT = `linear-gradient(135deg, ${NAV}, ${NAV_LIGHT}, ${VIOLET})`

const AGENT_INFO: Record<string, { label: string; desc: string; icon: React.ElementType; gradient: string }> = {
  'Agent 1': { label: 'Agent 1 — Analyse',              desc: 'Analyse sémantique de la user story',     icon: FileText,      gradient: CARD_GRADIENT },
  'Agent 2': { label: 'Agent 2 — Génération des tests', desc: 'Création des scénarios de tests manuels', icon: TestTube,      gradient: CARD_GRADIENT },
  'Agent 3': { label: 'Agent 3 — Validation',           desc: 'Couverture, ambiguïtés & cas limites',    icon: CheckCircle2,  gradient: CARD_GRADIENT },
  'Agent 5': { label: 'Agent 5 — Rapport',              desc: 'Rapport qualité & recommandations',       icon: FileBarChart2, gradient: CARD_GRADIENT },
}

// ── Agent 1 Result ────────────────────────────────────────────────────────────
const Agent1Result: React.FC<{ output: any }> = ({ output }) => {
  if (!output) return null
  const points = output.testable_points || []
  const actors = output.actors || []
  return (
    <div className="space-y-6 w-full text-slate-900">
      <div className="grid gap-4 sm:grid-cols-2">
        {output.story_type && (
          <div className="rounded-2xl p-4 bg-slate-50 border">
            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Type de Story</p>
            <p className="mt-1 font-bold text-sm" style={{ color: NAV }}>{output.story_type}</p>
          </div>
        )}
        {actors.length > 0 && (
          <div className="rounded-2xl p-4 bg-slate-50 border">
            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Acteurs</p>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {actors.map((actor: string, i: number) => (
                <span key={i} className="px-2 py-0.5 rounded-lg text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-100">
                  {actor}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
      {points.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-bold uppercase tracking-widest text-slate-500">Points Testables Identifiés</p>
          <div className="space-y-2">
            {points.map((pt: string, i: number) => (
              <div key={i} className="flex gap-3 items-start p-3 bg-white border rounded-xl">
                <span className="font-bold text-xs px-2 py-0.5 rounded bg-slate-100">{i+1}</span>
                <p className="text-xs leading-relaxed font-medium">{pt}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Test Accordion ────────────────────────────────────────────────────────────
const TestAccordion: React.FC<{ test: any; idx: number; storyId?: string }> = ({ test, idx, storyId }) => {
  const [open, setOpen] = useState(false)
  const steps = test.steps || test.étapes?.flatMap((e: any) => e.steps || []) || []
  return (
    <div className="border rounded-2xl overflow-hidden bg-white shadow-sm transition hover:shadow-md">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between p-4 text-left font-semibold text-sm"
        style={{ color: NAV }}
      >
        <div className="flex items-center gap-3">
          <span className="px-2 py-0.5 rounded text-xs font-bold text-white uppercase" style={{ background: ORANGE }}>
            {test.scenario_type || 'NOM'}
          </span>
          <span>{test.test_name || test.title || `Test #${idx + 1}`}</span>
        </div>
        <span className="text-slate-400">{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div className="p-4 border-t bg-slate-50 space-y-3">
          {test.objective && (
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Objectif</p>
              <p className="text-xs font-medium text-slate-700 mt-1">{test.objective}</p>
            </div>
          )}
          <div>
            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2">Étapes ({steps.length})</p>
            <div className="space-y-2">
              {steps.map((st: any, i: number) => (
                <div key={i} className="p-2.5 bg-white border rounded-xl space-y-1">
                  <div className="flex gap-2 items-center text-xs font-bold" style={{ color: NAV }}>
                    <span className="w-5 h-5 rounded-full bg-slate-100 flex items-center justify-center text-[10px]">{i+1}</span>
                    <span>{st.titre || st.action || 'Étape'}</span>
                  </div>
                  {st.expected_result && (
                    <p className="text-xs text-slate-500 pl-7">Attendu : {st.expected_result}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Agent 2 Result ────────────────────────────────────────────────────────────
const Agent2Result: React.FC<{ output: any; storyId?: string }> = ({ output, storyId }) => {
  const tests = Array.isArray(output) ? output : output?.tests || output?.agent2_tests || []
  if (!tests.length) return (
    <div className="py-12 text-center">
      <TestTube size={32} className="mx-auto mb-3 opacity-30" style={{ color: NAV }} />
      <p className="text-sm font-medium text-slate-400">Aucun test généré</p>
    </div>
  )
  return (
    <div className="space-y-4 w-full">
      <p className="text-xs font-bold text-slate-500 mb-2">
        {tests.length} test{tests.length > 1 ? 's' : ''} généré{tests.length > 1 ? 's' : ''}
      </p>
      {tests.map((test: any, idx: number) => (
        <TestAccordion key={idx} test={test} idx={idx} storyId={storyId} />
      ))}
    </div>
  )
}

// ── Agent 3 Result ────────────────────────────────────────────────────────────
const Agent3Result: React.FC<{ output: any }> = ({ output }) => {
  if (!output) return null
  const report = output?.report || output
  const coverage = report?.coverage_rate ?? report?.coverage_percentage ?? 0
  const validationStatus = report?.validation_status
  const ambiguities = report?.ambiguities || []
  const duplicates = report?.duplicate_tests || report?.duplicates || []
  const covPct = Math.round(coverage * 100)

  return (
    <div className="space-y-6 w-full text-slate-900">
      <div className="grid grid-cols-3 gap-4">
        <div className="rounded-2xl p-4 text-center text-white" style={{ background: `linear-gradient(135deg, ${ORANGE}, ${ROSE})` }}>
          <p className="text-3xl font-extrabold">{covPct}%</p>
          <p className="text-xs font-bold text-white/80 uppercase tracking-widest mt-1">Couverture</p>
        </div>
        <div className="rounded-2xl p-4 text-center border" style={{ borderColor: `${ROSE}25`, background: `${ROSE}08` }}>
          <p className="text-3xl font-extrabold" style={{ color: ROSE }}>{ambiguities.length}</p>
          <p className="text-xs font-bold uppercase tracking-widest mt-1" style={{ color: `${ROSE}80` }}>Ambiguïtés</p>
        </div>
        <div className="rounded-2xl p-4 text-center border" style={{ borderColor: `${ORANGE}25`, background: `${ORANGE}08` }}>
          <p className="text-3xl font-extrabold" style={{ color: ORANGE }}>{duplicates.length}</p>
          <p className="text-xs font-bold uppercase tracking-widest mt-1" style={{ color: `${ORANGE}80` }}>Doublons</p>
        </div>
      </div>

      {validationStatus && (
        <div className="flex items-center gap-3">
          <span className="text-xs font-bold uppercase tracking-widest text-slate-500">Statut Validation :</span>
          <span className="px-3 py-1 rounded-full text-xs font-bold"
            style={{
              background: validationStatus === 'VALID' ? `${ORANGE}18` : `${ROSE}18`,
              color: validationStatus === 'VALID' ? ORANGE : ROSE,
              border: `1px solid ${validationStatus === 'VALID' ? ORANGE : ROSE}40`,
            }}>
            {validationStatus}
          </span>
        </div>
      )}
    </div>
  )
}

// ── Agent 5 Result ────────────────────────────────────────────────────────────
const BulletList: React.FC<{ items: string[]; color?: string }> = ({ items, color = NAV }) => (
  <ul className="space-y-1.5 list-disc list-inside pl-1 text-xs" style={{ color: NAV }}>
    {items.map((it, i) => (
      <li key={i} className="leading-relaxed">
        <span className="font-medium">{it}</span>
      </li>
    ))}
  </ul>
)
const InfoTable: React.FC<{ rows: [string, string][] }> = ({ rows }) => (
  <div className="rounded-xl overflow-hidden border">
    <table className="w-full text-xs text-left">
      <tbody>
        {rows.map(([k, v], i) => (
          <tr key={i} className="border-t first:border-0">
            <td className="px-3 py-2.5 font-bold uppercase tracking-wider bg-slate-50 w-1/3 text-slate-500">{k}</td>
            <td className="px-3 py-2.5 font-medium text-slate-900">{v}</td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
)
const ReportSection: React.FC<{ icon: string; title: string; children: React.ReactNode }> = ({ icon, title, children }) => (
  <div className="space-y-3">
    <div className="flex items-center gap-2 pb-2 border-b">
      <span className="font-extrabold text-sm text-slate-400">{icon}</span>
      <h4 className="text-xs font-extrabold uppercase tracking-widest text-slate-700">{title}</h4>
    </div>
    {children}
  </div>
)

const Agent5Result: React.FC<{ output: any; storyId?: string }> = ({ output, storyId }) => {
  if (!output) return null
  const [downloading, setDownloading] = useState(false)

  const reportObj     = output.report || output
  const reportTitle   = reportObj.report_title
  const version       = reportObj.report_version
  const timestamp     = reportObj.generated_timestamp
  const reportStoryId = reportObj.story_id || storyId

  const exec         = reportObj.executive_summary || {}
  const globalStatus = exec.overall_status
  const findings     = exec.key_findings || []
  const nextSteps    = exec.next_steps || []

  const storySynth      = reportObj.story_summary || {}
  const testSuite       = reportObj.test_suite || {}
  const coverage        = reportObj.coverage_metrics || {}
  const validation      = reportObj.quality_assurance || {}
  const recommendations = reportObj.recommendations || []
  const pipeline        = reportObj.processing_notes || []

  const normalizedStatus = String(globalStatus || '').toUpperCase()
  const statusColor = (normalizedStatus === 'APPROVED') ? ORANGE : ROSE

  const handleDownloadMarkdown = async () => {
    if (!reportStoryId) return
    setDownloading(true)
    try {
      const { apiClient } = await import('../api/client')
      const md = await apiClient.agent5.getReportMarkdown(reportStoryId)
      const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `rapport-qa-${reportStoryId}.md`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (err: any) {
      console.error('Download failed:', err)
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div className="w-full space-y-8 text-slate-900">
      <div className="rounded-2xl p-6" style={{ background: CARD_GRADIENT, boxShadow: '0 8px 32px rgba(10,22,40,0.3)' }}>
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <p className="text-xs font-bold uppercase tracking-widest text-white/50 mb-2">Rapport QA Final</p>
            <h2 className="text-2xl font-extrabold text-white leading-tight mb-3">
              {reportTitle || `Rapport QA — ${reportStoryId}`}
            </h2>
            <div className="flex flex-wrap gap-3">
              {reportStoryId && (
                <span className="px-3 py-1 rounded-full text-xs font-bold text-white bg-white/20 border border-white/20">
                  {reportStoryId}
                </span>
              )}
              {version && <span className="px-3 py-1 rounded-full text-xs font-bold text-white/70 bg-white/10">v{version}</span>}
              {timestamp && <span className="px-3 py-1 rounded-full text-xs text-white/50 bg-white/5">{new Date(timestamp).toLocaleString('fr-FR')}</span>}
            </div>
          </div>
          {globalStatus && (
            <div className="flex-shrink-0 text-center">
              <div className="w-24 h-24 rounded-2xl flex flex-col items-center justify-center bg-white/10 border border-white/20">
                <CheckCircle2 size={28} style={{ color: 'white' }} />
                <p className="text-xs font-extrabold mt-1 text-white">{globalStatus}</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {(findings.length > 0 || nextSteps.length > 0) && (
        <ReportSection icon="■" title="Résumé Exécutif">
          {findings.length > 0 && <BulletList items={findings} />}
          {nextSteps.length > 0 && (
            <div className="mt-2">
              <p className="text-xs font-bold text-slate-500 mb-1">Prochaines étapes :</p>
              <BulletList items={nextSteps} />
            </div>
          )}
        </ReportSection>
      )}

      {Object.keys(storySynth).length > 0 && (
        <ReportSection icon="■" title="Synthèse User Story">
          <InfoTable rows={
            Object.entries(storySynth)
              .filter(([, v]) => typeof v === 'string' || typeof v === 'number')
              .map(([k, v]) => [k.replace(/_/g, ' '), String(v)])
          } />
        </ReportSection>
      )}

      {Object.keys(testSuite).length > 0 && (
        <ReportSection icon="■" title="Suite de Tests">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4">
            {[
              { label: 'Total', value: testSuite.total_tests },
              { label: 'NOM', value: testSuite.nom_count },
              { label: 'ALT', value: testSuite.alt_count },
              { label: 'EXC', value: testSuite.exc_count },
            ].filter(r => r.value !== undefined).map((item, i) => (
              <div key={i} className="rounded-xl p-3 bg-slate-50 border text-center">
                <p className="text-xl font-extrabold" style={{ color: NAV }}>{item.value}</p>
                <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mt-0.5">{item.label}</p>
              </div>
            ))}
          </div>
        </ReportSection>
      )}

      <div className="flex items-center justify-between pt-4 border-t text-xs text-slate-400">
        <span>Rapport d'historique</span>
        <button
          type="button"
          onClick={handleDownloadMarkdown}
          disabled={downloading}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-bold text-white transition-all hover:-translate-y-0.5 disabled:opacity-50"
          style={{ background: CARD_GRADIENT }}>
          {downloading ? 'Génération...' : 'Télécharger .md'}
        </button>
      </div>
    </div>
  )
}

// ── Agent Rich Output Dispatcher ──────────────────────────────────────────────
const AgentRichOutput: React.FC<{ agentKey: string; output: any; storyId?: string }> = ({ agentKey, output, storyId }) => {
  if (!output) return null
  if (agentKey === 'Agent 1') return <Agent1Result output={output} />
  if (agentKey === 'Agent 2') return <Agent2Result output={output} storyId={storyId} />
  if (agentKey === 'Agent 3') return <Agent3Result output={output} />
  if (agentKey === 'Agent 5') return <Agent5Result output={output} storyId={storyId} />
  return <pre className="text-xs p-4 rounded-xl bg-slate-50 overflow-x-auto">{JSON.stringify(output, null, 2)}</pre>
}

// ── Agent Result Modal ────────────────────────────────────────────────────────
const AgentResultModal: React.FC<{
  agentKey: string
  output: any
  storyId?: string
  onClose: () => void
}> = ({ agentKey, output, storyId, onClose }) => {
  const info = AGENT_INFO[agentKey] || { label: agentKey, icon: HelpCircle, gradient: CARD_GRADIENT }
  const Icon = info.icon

  return (
    <div className="fixed inset-0 z-[9999] flex items-start justify-center p-4 md:p-8 overflow-y-auto">
      <div className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white rounded-3xl w-full max-w-5xl shadow-2xl my-4 flex flex-col z-10">
        <div className="flex items-center gap-4 px-6 py-5 sticky top-0 bg-white z-10 border-b rounded-t-3xl">
          <div className="w-11 h-11 rounded-2xl flex items-center justify-center text-white" style={{ background: info.gradient }}>
            <Icon size={20} />
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-extrabold" style={{ color: NAV }}>{info.label}</h3>
            <p className="text-sm text-slate-500">{info.desc}</p>
          </div>
          <button onClick={onClose} className="p-2 rounded-xl transition hover:bg-slate-100 text-slate-400">
            <XCircle size={22} />
          </button>
        </div>
        <div className="p-6 md:p-8 overflow-y-auto max-h-[70vh]">
          <AgentRichOutput agentKey={agentKey} output={output} storyId={storyId} />
        </div>
      </div>
    </div>
  )
}

// ── MAIN StoryDetailPage Component ─────────────────────────────────────────────
export const StoryDetailPage: React.FC = () => {
  const { storyId } = useParams<{ storyId: string }>()
  const navigate = useNavigate()
  const toast = useToast()

  const story = useStory<StoredStory>(storyId || '', true)
  const analyses = useAnalysisHistory(storyId || '')
  
  // Stored snapshots
  const [agent1Output, setAgent1Output] = useState<any | null>(null)
  const [agent2Output, setAgent2Output] = useState<any | null>(null)
  const [agent3Output, setAgent3Output] = useState<any | null>(null)
  const [agent5Output, setAgent5Output] = useState<any | null>(null)
  
  // Modal controllers
  const [openAgent, setOpenAgent] = useState<string | null>(null)

  const fetchHistoricalOutputs = useCallback(async () => {
    if (!storyId) return
    try {
      // 1. Fetch Agent 1 latest analysis
      const ana = await apiClient.db.getLatestAnalysis(storyId)
      setAgent1Output(ana)
    } catch {}

    try {
      // 2. Fetch Agent 2 latest manual tests
      const tests = await apiClient.db.getManualTests(storyId)
      setAgent2Output(tests)
    } catch {}

    try {
      // 3. Fetch Agent 3 latest validation
      const val = await apiClient.db.getValidations(storyId)
      setAgent3Output(val)
    } catch {}

    try {
      // 4. Fetch Agent 5 latest report
      const rep = await apiClient.agent5.generateReport(storyId)
      setAgent5Output(rep)
    } catch {}
  }, [storyId])

  useEffect(() => {
    fetchHistoricalOutputs()
  }, [fetchHistoricalOutputs])

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

  const renderCard = (agentName: string, output: any, isAvailable: boolean) => {
    const info = AGENT_INFO[agentName]
    if (!info) return null
    const Icon = info.icon

    return (
      <div
        onClick={() => isAvailable && setOpenAgent(agentName)}
        className={`group relative rounded-3xl border p-6 transition-all bg-white ${isAvailable ? 'cursor-pointer hover:shadow-lg hover:border-slate-300' : 'opacity-50 cursor-not-allowed'}`}
        style={{ borderColor: isAvailable ? 'rgba(11,30,62,0.12)' : 'rgba(11,30,62,0.06)' }}
      >
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-2xl flex items-center justify-center text-white transition-transform group-hover:scale-105"
            style={{ background: info.gradient }}>
            <Icon size={22} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-[10px] font-extrabold uppercase tracking-widest text-slate-400 mb-1">{agentName}</p>
            <h3 className="text-base font-extrabold text-slate-800 leading-snug group-hover:text-brand-rose">{info.label.split('—')[1]?.trim() || info.label}</h3>
            <p className="text-xs text-slate-500 mt-1 leading-relaxed">{info.desc}</p>
          </div>
          {isAvailable ? (
            <div className="w-7 h-7 rounded-full bg-slate-50 border flex items-center justify-center text-slate-400 group-hover:bg-slate-100 group-hover:text-slate-900">
              <ArrowRight size={14} />
            </div>
          ) : (
            <span className="text-xs font-semibold text-slate-400">Non dispo</span>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-fade-in max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-2">
          <button
            type="button"
            onClick={() => navigate('/history')}
            className="inline-flex items-center gap-2 text-sm font-semibold transition hover:-translate-x-0.5"
            style={{ color: ROSE }}
          >
            <ArrowLeft size={16} /> Retour à l'historique
          </button>
          <div>
            <p className="text-xs uppercase tracking-widest font-bold text-slate-400">Historique User Story</p>
            <h1 className="text-3xl font-extrabold" style={{ color: NAV }}>{storyId}</h1>
          </div>
        </div>
        <button
          type="button"
          onClick={handleDeleteStory}
          className="inline-flex items-center gap-2 rounded-2xl bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-600 border border-rose-100 transition hover:bg-rose-100"
        >
          <Trash2 size={16} /> Supprimer la story
        </button>
      </div>

      {story.error && (
        <Alert type="error" title="Impossible de charger la story" description={story.error.message || 'Vérifiez l\'ID.'} />
      )}

      {/* Main Details block */}
      <div className="bg-white rounded-3xl border shadow-sm p-6" style={{ borderColor: 'rgba(11,30,62,0.12)' }}>
        <div className="flex flex-col gap-4">
          <div className="flex flex-wrap items-center gap-2 mb-2">
            <span className="font-mono text-xs font-bold uppercase tracking-[0.2em] px-3 py-1 rounded-full bg-slate-100" style={{ color: NAV }}>
              {storyId}
            </span>
            {story.data?.status && (
              <Badge variant="success">{story.data.status}</Badge>
            )}
          </div>
          <h2 className="text-xl font-bold" style={{ color: NAV }}>{story.data?.summary || 'Aucune synthèse'}</h2>
          <p className="text-sm text-slate-600 leading-relaxed max-w-4xl">
            {story.data?.description_clean || story.data?.description_raw || 'Aucune description enregistrée.'}
          </p>

          <div className="grid gap-3 sm:grid-cols-3 mt-4">
            <div className="rounded-2xl bg-slate-50 p-4 border">
              <p className="text-[11px] uppercase tracking-[0.18em] text-slate-400 font-bold">Créée le</p>
              <p className="mt-1.5 text-sm font-bold text-slate-800">
                {story.data?.created_at
                  ? new Date(story.data.created_at).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })
                  : '—'}
              </p>
            </div>
            <div className="rounded-2xl bg-slate-50 p-4 border">
              <p className="text-[11px] uppercase tracking-[0.18em] text-slate-400 font-bold">Critères d'acceptation</p>
              <p className="mt-1.5 text-xs text-slate-600 truncate">
                {story.data?.acceptance_criteria_clean || 'Aucun critère enregistré'}
              </p>
            </div>
            <div className="rounded-2xl bg-slate-50 p-4 border">
              <p className="text-[11px] uppercase tracking-[0.18em] text-slate-400 font-bold">Étiquettes</p>
              <p className="mt-1.5 text-sm text-slate-600">
                {story.data?.labels?.length ? story.data.labels.join(', ') : 'Aucune'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Progress & Pipeline emulation bar */}
      <div className="space-y-3">
        <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400 px-1">Statut des Agents de la Story</h3>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {renderCard('Agent 1', agent1Output, !!agent1Output)}
          {renderCard('Agent 2', agent2Output, !!agent2Output)}
          {renderCard('Agent 3', agent3Output, !!agent3Output)}
          {renderCard('Agent 5', agent5Output, !!agent5Output)}
        </div>
      </div>

      {/* Modals for outputs */}
      {openAgent === 'Agent 1' && agent1Output && (
        <AgentResultModal agentKey="Agent 1" output={agent1Output} storyId={storyId} onClose={() => setOpenAgent(null)} />
      )}
      {openAgent === 'Agent 2' && agent2Output && (
        <AgentResultModal agentKey="Agent 2" output={agent2Output} storyId={storyId} onClose={() => setOpenAgent(null)} />
      )}
      {openAgent === 'Agent 3' && agent3Output && (
        <AgentResultModal agentKey="Agent 3" output={agent3Output} storyId={storyId} onClose={() => setOpenAgent(null)} />
      )}
      {openAgent === 'Agent 5' && agent5Output && (
        <AgentResultModal agentKey="Agent 5" output={agent5Output} storyId={storyId} onClose={() => setOpenAgent(null)} />
      )}
    </div>
  )
}
