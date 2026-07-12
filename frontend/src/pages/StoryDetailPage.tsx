import React, { useEffect, useState, useCallback } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useStory } from '../hooks'
import { apiClient, StoredStory } from '../api/client'
import { useToast } from '../contexts/ToastContext'
import {
  ArrowLeft, Trash2, FileText, CheckCircle2, XCircle,
  TestTube, FileBarChart2, ArrowRight, Workflow,
  GitBranch, ChevronDown, Printer, HelpCircle , BarChart3
} from 'lucide-react'
import { Badge } from '../components/ui/Badge'
import { Alert } from '../components/ui/Alert'
import { ManualTestsTable } from '../components/tests/ManualTestsTable'
import { AgentRichOutput, AgentSectionTitle } from '../components/agents/AgentOutputs'

// ── Colors & Styles matching PipelinePage ────────────────────────
const NAV       = '#0a0f2e'
const NAV_LIGHT = '#1a2060'
const ROSE      = '#f43f5e'
const ORANGE    = '#f97316'
const VIOLET    = '#7c3aed'

const CARD_GRADIENT = `linear-gradient(135deg, #6366f1, #ec4899)`
// Dégradé premium inspiré de la page landing : bleu marine profond vers rose/violet
const HEADER_GRADIENT = 'linear-gradient(135deg, #0a0f2e 0%, #13113c 50%, #2d1334 100%)'
const HEADER_SHADOW   = '0 8px 30px rgba(10, 15, 46, 0.22)'
// Dégradé des boutons d'action (violet → rose → orange) — image 1 & 2
const BUTTON_GRADIENT = `linear-gradient(90deg, #4338ca, ${ROSE})`
const ICON_GRADIENT = `linear-gradient(135deg, #6366f1, #ec4899)`
// Dégradé bleu marine pur pour les headers de tableau — image 5
const NAVY_GRADIENT   = `linear-gradient(135deg, ${NAV}, ${NAV_LIGHT})`
// Dégradé KPI inspiré de la landing — marine dominant, transition rose/orange en fin
const KPI_GRADIENT = `linear-gradient(135deg, ${NAV} 0%, ${ROSE} 70%, ${ORANGE} 100%)`
const KPI_SHADOW    = '0 8px 24px rgba(10, 15, 46, 0.18)'

const AGENT_INFO: Record<string, { label: string; desc: string; icon: React.ElementType; gradient: string; accent: string }> = {
  'Agent 1':   { label: 'Agent 1 — Analyse',              desc: 'Analyse sémantique de la user story',             icon: FileText,      gradient: ICON_GRADIENT, accent: VIOLET },
  'Agent 1.5': { label: 'Agent 1.5 — Business Modeling',  desc: 'Goals métier & workflows end-to-end',              icon: GitBranch,     gradient: ICON_GRADIENT, accent: VIOLET },
  'Agent 2':   { label: 'Agent 2 — Génération des tests', desc: 'Création des scénarios de tests manuels',         icon: TestTube,      gradient: ICON_GRADIENT, accent: ROSE },
  'Agent 3':   { label: 'Agent 3 — Validation',           desc: 'Couverture, ambiguïtés & cas limites',            icon: CheckCircle2,  gradient: ICON_GRADIENT, accent: ORANGE },
  'Agent 4':   { label: 'Agent 4 — Classification',       desc: 'Classification auto/manuel',                      icon: BarChart3,     gradient: ICON_GRADIENT, accent: VIOLET },
  'Agent 5':   { label: 'Agent 5 — Rapport',              desc: 'Rapport qualité & recommandations',               icon: FileBarChart2, gradient: ICON_GRADIENT, accent: NAV },
}

// SectionTitle â€” replaced by AgentSectionTitle from AgentOutputs.tsx

const resolveImageUrl = (url?: string) => {
  if (!url) return undefined
  if (url.startsWith('http') || url.startsWith('data:') || url.startsWith('/api')) return url
  if (url.startsWith('/documents/')) return `/api${url}`
  return url
}

const ImageGallery: React.FC<{ images: any[] }> = ({ images }) => {
  if (!images || images.length === 0) return null
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {images.map((image, idx) => {
        const src = resolveImageUrl(image.url)
        return (
          <div key={idx} className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
            {src ? (
              <div className="h-48 overflow-hidden rounded-2xl bg-slate-100">
                <img
                  src={src}
                  alt={image.alt_text || image.caption || `Image ${idx + 1}`}
                  className="h-full w-full object-cover"
                />
              </div>
            ) : (
              <div className="h-48 rounded-2xl bg-slate-100 flex items-center justify-center text-slate-400 text-sm">
                Image sans URL
              </div>
            )}
            <div className="mt-4 space-y-2 text-slate-700 text-sm">
              {image.caption && <p className="font-semibold text-slate-900">{image.caption}</p>}
              {image.description && <p className="whitespace-pre-wrap">{image.description}</p>}
              {image.source && <p className="text-xs text-slate-400">Source: {image.source}</p>}
            </div>
          </div>
        )
      })}
    </div>
  )
}

const RagContextSection: React.FC<{ ragContext: any[] }> = ({ ragContext }) => {
  if (!ragContext || ragContext.length === 0) return null
  return (
    <div className="space-y-3">
      {ragContext.map((item, idx) => (
        <div key={idx} className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-sm font-semibold text-slate-900 mb-2">{item.source || `Document ${idx + 1}`}</p>
          <p className="text-sm text-slate-600 whitespace-pre-wrap">{item.text || item.content || JSON.stringify(item)}</p>
        </div>
      ))}
    </div>
  )
}

const JsonSectionContent: React.FC<{ content: any }> = ({ content }) => {
  if (!content) return null
  return (
    <div className="space-y-3">
      {(Array.isArray(content) ? content : [content]).map((item, idx) => (
        <div key={idx} className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
          <pre className="rounded-xl bg-slate-50 p-3 text-xs text-slate-700 overflow-auto">
            {JSON.stringify(item, null, 2)}
          </pre>
        </div>
      ))}
    </div>
  )
}

// â”€â”€ Agent components moved to src/components/agents/AgentOutputs.tsx â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// Agent1Result, Agent2Result, Agent3Result, Agent5Result, Agent15Result,
// BulletList, InfoTable, ReportSection, AgentRichOutput â€” all imported above.

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
      <div className="relative bg-white rounded-3xl w-full max-w-6xl shadow-2xl my-4 flex flex-col z-10">
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

// â”€â”€ MAIN StoryDetailPage Component â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export const StoryDetailPage: React.FC = () => {
  const { storyId } = useParams<{ storyId: string }>()
  const navigate = useNavigate()
  const toast = useToast()

  const story = useStory<StoredStory>(storyId || '', true)
  const storedStory = story.data as StoredStory | null

  const [agent1Output,  setAgent1Output]  = useState<any | null>(null)
  const [agent15Output, setAgent15Output] = useState<any | null>(null)
  const [agent2Output,  setAgent2Output]  = useState<any | null>(null)
  const [agent3Output,  setAgent3Output]  = useState<any | null>(null)
  const [agent5Output,  setAgent5Output]  = useState<any | null>(null)
  const [openAgent,     setOpenAgent]     = useState<string | null>(null)
  const [showJsonHistory, setShowJsonHistory] = useState(false)

  const fetchHistoricalOutputs = useCallback(async () => {
    if (!storyId) return
    try { const ana   = await apiClient.db.getLatestAnalysis(storyId);       setAgent1Output(ana)   } catch {}
    try { const bm    = await apiClient.agent15.getLatest(storyId);           setAgent15Output(bm)   } catch {}
    try { const tests = await apiClient.db.getManualTests(storyId);           setAgent2Output(tests) } catch {}
    try { const val   = await apiClient.db.getValidations(storyId);           setAgent3Output(val)   } catch {}
    try { const rep   = await apiClient.agent5.getReportSummary(storyId);     setAgent5Output(rep)   } catch {}
  }, [storyId])

  useEffect(() => { fetchHistoricalOutputs() }, [fetchHistoricalOutputs])

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

  const renderCard = (agentName: string, isAvailable: boolean) => {
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
    <div className="space-y-6 animate-fade-in max-w-7xl mx-auto">
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
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={handleDeleteStory}
            className="inline-flex items-center gap-2 rounded-2xl bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-600 border border-rose-100 transition hover:bg-rose-100"
          >
            <Trash2 size={16} /> Supprimer la story
          </button>
          <button
            type="button"
            onClick={() => setShowJsonHistory(s => !s)}
            className="inline-flex items-center gap-2 rounded-2xl bg-white px-4 py-3 text-sm font-medium border transition hover:bg-slate-50"
            style={{ borderColor: 'rgba(11,30,62,0.08)' }}
          >
            {showJsonHistory ? 'Masquer JSON' : 'Afficher JSON'}
          </button>
        </div>
      </div>

      {story.error && (
        <Alert type="error" title="Impossible de charger la story" description={story.error.message || "Vérifiez l'ID."} />
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

      {/* Agent cards */}
      <div className="space-y-3">
        <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400 px-1">Statut des Agents de la Story</h3>
        <div className="flex flex-col gap-3">
          {renderCard('Agent 1',   !!agent1Output)}
          {renderCard('Agent 1.5', !!agent15Output)}
          {renderCard('Agent 2',   !!agent2Output)}
          {renderCard('Agent 3',   !!agent3Output)}
          {renderCard('Agent 5',   !!agent5Output)}
        </div>
      </div>

      {/* JSON raw view */}
      {showJsonHistory && (
        <div className="mt-6 space-y-4">
          <AgentSectionTitle>Données JSON — Historique</AgentSectionTitle>

          {storedStory?.images && storedStory.images.length > 0 && (
            <div className="rounded-3xl border bg-white p-5 shadow-sm">
              <p className="text-xs uppercase tracking-widest text-slate-400 mb-2">Images</p>
              <ImageGallery images={storedStory.images} />
            </div>
          )}

          {storedStory?.rag_context && storedStory.rag_context.length > 0 && (
            <div className="rounded-3xl border bg-white p-5 shadow-sm">
              <p className="text-xs uppercase tracking-widest text-slate-400 mb-2">Contexte RAG</p>
              <RagContextSection ragContext={storedStory.rag_context} />
            </div>
          )}

          {agent2Output?.legacy_examples && agent2Output.legacy_examples.length > 0 && (
            <div className="rounded-3xl border bg-white p-5 shadow-sm">
              <p className="text-xs uppercase tracking-widest text-slate-400 mb-2">Exemples RAG legacy (Agent 2)</p>
              <JsonSectionContent content={agent2Output.legacy_examples} />
            </div>
          )}

          {agent2Output?.rag_context && agent2Output.rag_context.length > 0 && (
            <div className="rounded-3xl border bg-white p-5 shadow-sm">
              <p className="text-xs uppercase tracking-widest text-slate-400 mb-2">Contexte RAG (Agent 2)</p>
              <RagContextSection ragContext={agent2Output.rag_context} />
            </div>
          )}

          {agent2Output?.images && agent2Output.images.length > 0 && (
            <div className="rounded-3xl border bg-white p-5 shadow-sm">
              <p className="text-xs uppercase tracking-widest text-slate-400 mb-2">Images (Agent 2)</p>
              <ImageGallery images={agent2Output.images} />
            </div>
          )}

          <div className="rounded-3xl border bg-white p-5 shadow-sm">
            <p className="text-xs uppercase tracking-widest text-slate-400 mb-2">JSON complet</p>
            <pre className="rounded-2xl bg-slate-50 p-3 text-xs text-slate-700 overflow-auto" style={{ maxHeight: 420 }}>
              {JSON.stringify({ story: story.data || {}, agent1: agent1Output, agent15: agent15Output, agent2: agent2Output, agent3: agent3Output, agent5: agent5Output }, null, 2)}
            </pre>
          </div>
        </div>
      )}

      {/* Modals */}
      {openAgent === 'Agent 1' && agent1Output && (
        <AgentResultModal agentKey="Agent 1" output={agent1Output} storyId={storyId} onClose={() => setOpenAgent(null)} />
      )}
      {openAgent === 'Agent 1.5' && agent15Output && (
        <AgentResultModal agentKey="Agent 1.5" output={agent15Output} storyId={storyId} onClose={() => setOpenAgent(null)} />
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
