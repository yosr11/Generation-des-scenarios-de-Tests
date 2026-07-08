import React, { useState, useCallback, useMemo, useEffect, useRef } from 'react'
import { useToast } from '../contexts/ToastContext'
import { useOrchestrator } from '../hooks'
import { ManualTestsTable } from '../components/tests/ManualTestsTable'
import { Alert } from '../components/ui/Alert'
import { AgentRichOutput, AgentSectionTitle } from '../components/agents/AgentOutputs'
import {
  Play, Square, GitBranch, CheckCircle2, XCircle,
  Clock, Cpu, AlertTriangle, AlertCircle, ChevronRight, Bot,
  FileText, TestTube, BarChart3, FileBarChart2,
  Sparkles, Hash, Maximize2,
  ChevronDown, ChevronUp, Edit2, Upload, Printer
} from 'lucide-react'

// ── Constants ──────────────────────────────────────────────────────────────────

const NAV       = '#0a0f2e'
const NAV_LIGHT = '#1a2060'
const ROSE      = '#f43f5e'
const ORANGE    = '#f97316'
const VIOLET    = '#7c3aed'

const MAIN_GRADIENT = `linear-gradient(90deg, ${NAV}, ${NAV_LIGHT}, ${VIOLET}, ${ROSE}, ${ORANGE})`
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

// FIX #6 — inject print CSS inside a useEffect (SSR-safe, no duplicate injection)
const PRINT_STYLE = `
@media print {
  nav, aside, [class*="sidebar"], [class*="navigation"],
  [class*="Sidebar"], [class*="Navigation"],
  .sidebar, .nav, .navigation { display: none !important; }
  body { margin: 0 !important; }
  .modal-print-area { position: static !important; box-shadow: none !important; }
}
`

function usePrintStyle() {
  useEffect(() => {
    if (document.getElementById('pipeline-print-css')) return
    const style = document.createElement('style')
    style.id = 'pipeline-print-css'
    style.textContent = PRINT_STYLE
    document.head.appendChild(style)
  }, [])
}

// ── Step / Agent metadata ─────────────────────────────────────────────────────

const STEP_STYLE: Record<string, { bg: string; border: string; icon: React.ElementType; spin?: boolean }> = {
  completed: { bg: 'rgba(10,22,40,0.04)',   border: 'rgba(10,22,40,0.15)',  icon: CheckCircle2 },
  failed:    { bg: 'rgba(244,63,94,0.06)',  border: 'rgba(244,63,94,0.2)',  icon: XCircle },
  running:   { bg: 'rgba(249,115,22,0.06)', border: 'rgba(249,115,22,0.2)', icon: Cpu, spin: true },
  pending:   { bg: 'rgba(10,22,40,0.02)',   border: 'rgba(10,22,40,0.08)',  icon: Clock },
}

const AGENT_INFO: Record<string, { label: string; desc: string; icon: React.ElementType; gradient: string; accent: string }> = {
  'Agent 1':   { label: 'Agent 1 — Analyse',              desc: 'Analyse sémantique de la user story',             icon: FileText,      gradient: ICON_GRADIENT, accent: VIOLET },
  'Agent 1.5': { label: 'Agent 1.5 — Business Modeling',  desc: 'Goals métier & workflows end-to-end',              icon: GitBranch,     gradient: ICON_GRADIENT, accent: VIOLET },
  'Agent 2':   { label: 'Agent 2 — Génération des tests', desc: 'Création des scénarios de tests manuels',         icon: TestTube,      gradient: ICON_GRADIENT, accent: ROSE },
  'Agent 3':   { label: 'Agent 3 — Validation',           desc: 'Couverture, ambiguïtés & cas limites',            icon: CheckCircle2,  gradient: ICON_GRADIENT, accent: ORANGE },
  'Agent 4':   { label: 'Agent 4 — Classification',       desc: 'Classification auto/manuel',                      icon: BarChart3,     gradient: ICON_GRADIENT, accent: VIOLET },
  'Agent 5':   { label: 'Agent 5 — Rapport',              desc: 'Rapport qualité & recommandations',               icon: FileBarChart2, gradient: ICON_GRADIENT, accent: NAV },
}

const MODEL_OPTIONS = [
  'qwen3',
  'llama4',
  'gptoss',
  'gptoss120b',
  'qwen3.6',
  'nova-lite-2',
] as const

type ModelOption = (typeof MODEL_OPTIONS)[number]

// ── Shared small components ───────────────────────────────────────────────────

// FIX #9 — disabled state gets visual feedback
const ModelSelector: React.FC<{
  label: string
  value: ModelOption
  onChange: (value: ModelOption) => void
  disabled?: boolean
}> = ({ label, value, onChange, disabled }) => (
  <label className="block text-sm font-semibold text-slate-800">
    <span className="mb-2 block text-xs uppercase tracking-[0.18em] text-slate-500">{label}</span>
    <select
      value={value}
      disabled={disabled}
      onChange={(e) => onChange(e.target.value as ModelOption)}
      className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 transition focus:border-brand-violet focus:outline-none"
      style={disabled ? { opacity: 0.4, cursor: 'not-allowed', background: '#f8fafc' } : undefined}
    >
      {MODEL_OPTIONS.map((opt) => (
        <option key={opt} value={opt}>{opt}</option>
      ))}
    </select>
  </label>
)

const Toggle: React.FC<{
  checked: boolean
  onChange: (v: boolean) => void
  label: string
  desc?: string
}> = ({ checked, onChange, label, desc }) => (
  <label className="flex items-center gap-3 cursor-pointer group py-1">
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className="relative w-11 h-6 rounded-full flex-shrink-0 transition-all duration-200 focus:outline-none"
      style={checked
        ? { background: NAV, boxShadow: `0 0 0 3px rgba(11,30,62,0.18)` }
        : { background: '#e2e8f0' }
      }
    >
      <span className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-all duration-200 ${checked ? 'left-5' : 'left-0.5'}`} />
    </button>
    <div className="flex-1 min-w-0">
      <p className="text-sm font-semibold text-slate-800 group-hover:text-slate-900 leading-tight">{label}</p>
      {desc && <p className="text-xs text-slate-500 mt-0.5">{desc}</p>}
    </div>
  </label>
)

// SectionTitle removed — use AgentSectionTitle from AgentOutputs for agent panels

// ── Agent Result Modal ────────────────────────────────────────────────────────

// FIX #4 — modal lifted out of card; open state managed by parent to survive re-renders
const AgentResultModal: React.FC<{
  step: any
  storyId?: string
  onClose: () => void
}> = ({ step, storyId, onClose }) => {
  const info = AGENT_INFO[step.agent] || { label: step.agent, icon: Bot, gradient: CARD_GRADIENT }
  const Icon = info.icon

  return (
    <div className="fixed inset-0 z-[9999] flex items-start justify-center p-4 md:p-8 print:p-0 overflow-y-auto">
      <div className="absolute inset-0 backdrop-blur-sm print:hidden"
        style={{ background: 'rgba(10,22,40,0.6)' }}
        onClick={onClose} />
      <div className="relative bg-white rounded-3xl w-full max-w-5xl shadow-2xl my-4 print:shadow-none print:max-w-full print:rounded-none flex flex-col modal-print-area">
        <div className="flex items-center gap-4 px-6 py-5 sticky top-0 bg-white z-10 border-b rounded-t-3xl"
          style={{ borderColor: 'rgba(10,22,40,0.08)' }}>
          <div className="w-11 h-11 rounded-2xl flex items-center justify-center flex-shrink-0"
            style={{ background: info.gradient }}>
            <Icon size={20} className="text-white" />
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-extrabold" style={{ color: NAV }}>{info.label}</h3>
            <p className="text-sm" style={{ color: `${NAV}60` }}>{step.description || 'Détails du résultat'}</p>
          </div>
          <button onClick={onClose}
            className="p-2 rounded-xl transition-colors hover:bg-slate-100 print:hidden"
            style={{ color: `${NAV}50` }}>
            <XCircle size={22} />
          </button>
        </div>
        <div className="p-6 md:p-8 overflow-y-auto">
          <AgentRichOutput agentKey={step.agent} output={step.output} storyId={storyId} />
        </div>
      </div>
    </div>
  )
}

const AgentResultCard: React.FC<{
  step: any
  isSelected: boolean
  onSelect: () => void
  onExpand: () => void
}> = ({ step, isSelected, onSelect, onExpand }) => {
  const info        = AGENT_INFO[step.agent] || { label: step.agent, icon: Bot, gradient: CARD_GRADIENT, accent: VIOLET }
  const statusStyle = STEP_STYLE[step.status] || STEP_STYLE.pending
  const Icon        = info.icon
  const isReady     = step.status === 'completed' && step.output

  const statusBadgeClass =
    step.status === 'completed' ? 'syn-badge--navy'
    : step.status === 'failed' ? 'syn-badge--rose'
    : step.status === 'running' ? 'syn-badge--orange'
    : 'syn-badge--navy'

  return (
    <div
      className={`syn-agent-tab ${isSelected ? 'syn-agent-tab--active' : ''} ${isReady ? 'cursor-pointer' : 'syn-agent-tab--disabled'}`}
      style={{ ['--agent-accent' as string]: info.gradient }}
      onClick={() => isReady && onSelect()}
    >
      <div className="p-4 flex items-center gap-3">
        <div
          className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
          style={{
            background: isReady ? info.gradient : statusStyle.bg,
            boxShadow: isReady ? `0 4px 14px ${info.accent}35` : undefined,
          }}
        >
          {statusStyle.spin
            ? <statusStyle.icon size={16} className="animate-spin text-white" />
            : <Icon size={16} className={isReady ? 'text-white' : ''} style={{ color: isReady ? 'white' : NAV }} />
          }
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold truncate text-brand-navy">
              {step.agent}
            </span>
            <span className={`syn-badge ${statusBadgeClass}`}>
              {step.status}
            </span>
          </div>
          <p className="text-[11px] mt-1 truncate text-brand-muted">
            {step.agent === 'Agent 2' && step.status === 'completed'
              ? 'Voir les tests générés'
              : (step.description || info.desc)}
          </p>
        </div>
        {isReady && (
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); onExpand() }}
            className="p-1.5 rounded-lg hover:bg-brand-violet/8 text-brand-muted hover:text-brand-violet transition-colors flex-shrink-0"
            title="Ouvrir en plein écran"
          >
            <Maximize2 size={14} />
          </button>
        )}
      </div>
    </div>
  )
}

const AgentWorkspace: React.FC<{
  step: any | null
  storyId?: string
  manualTests: any[]
  onTestsChange: (tests: any[]) => void
}> = ({ step, storyId, manualTests, onTestsChange }) => {
  if (!step) {
    return (
      <div className="syn-empty">
        <div className="syn-icon-box mx-auto mb-4 opacity-60">
          <Bot size={22} />
        </div>
        <p className="text-sm font-semibold text-brand-navy">Aucun agent sélectionné</p>
        <p className="text-xs text-brand-muted mt-1">
          Cliquez sur une carte agent ci-dessus pour afficher ses résultats
        </p>
      </div>
    )
  }

  const info = AGENT_INFO[step.agent] || { label: step.agent, icon: Bot, gradient: CARD_GRADIENT, desc: '', accent: VIOLET }
  const Icon = info.icon

  const agent2Output = step.agent === 'Agent 2' && manualTests.length
    ? manualTests
    : step.output

  return (
    <div className="syn-surface-lg animate-fade-in">
      <div className="syn-strip" style={{ background: info.gradient }} />
      <div className="px-6 py-4 flex items-center gap-4 border-b border-brand-navy/[0.06] bg-gradient-to-r from-brand-offwhite/80 to-white">
        <div
          className="w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0"
          style={{ background: info.gradient, boxShadow: `0 4px 16px ${info.accent}30` }}
        >
          <Icon size={18} className="text-white" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-base font-extrabold text-brand-navy">{info.label}</h3>
          <p className="text-xs truncate text-brand-muted">{info.desc}</p>
        </div>
        {step.agent === 'Agent 2' && manualTests.length > 0 && (
          <span className="syn-badge syn-badge--rose">
            {manualTests.length} test{manualTests.length > 1 ? 's' : ''}
          </span>
        )}
      </div>
      <div className="p-6 bg-gradient-to-b from-white to-brand-offwhite/30">
        {step.status === 'running' && (
          <div className="py-10 text-center">
            <Cpu size={24} className="mx-auto mb-3 animate-spin opacity-40" style={{ color: ORANGE }} />
            <p className="text-sm font-medium" style={{ color: `${NAV}60` }}>Exécution en cours…</p>
          </div>
        )}
        {step.status === 'failed' && (
          <div className="rounded-2xl p-4" style={{ background: `${ROSE}08`, border: `1px solid ${ROSE}20` }}>
            <p className="text-sm font-semibold" style={{ color: ROSE }}>Échec de l'agent</p>
            <p className="text-sm mt-1" style={{ color: `${NAV}70` }}>{step.error || 'Erreur inconnue'}</p>
          </div>
        )}
        {step.status === 'completed' && (
          <AgentRichOutput
            agentKey={step.agent}
            output={agent2Output}
            storyId={storyId}
            onTestsChange={onTestsChange}
          />
        )}
        {step.status === 'pending' && (
          <p className="text-sm text-center py-8" style={{ color: `${NAV}50` }}>En attente d'exécution</p>
        )}
      </div>
    </div>
  )
}

// ── Main Pipeline Page ────────────────────────────────────────────────────────

export const PipelinePage: React.FC = () => {
  usePrintStyle() // FIX #6

  const [storyId,       setStoryId]       = useState('')
  const [inputValue,    setInputValue]    = useState('')
  const [useRag,        setUseRag]        = useState(true)
  const [useLegacyRag,  setUseLegacyRag]  = useState(false)
  const [forceRefresh,  setForceRefresh]  = useState(false)
  const [runAgent4,     setRunAgent4]     = useState(true)
  const [modelAgent1,   setModelAgent1]   = useState<ModelOption>('llama4')
  const [modelAgent15,  setModelAgent15]  = useState<ModelOption>('llama4')
  const [modelAgent2,   setModelAgent2]   = useState<ModelOption>('llama4')
  const [modelAgent3,   setModelAgent3]   = useState<ModelOption>('qwen3')
  const [modelAgent4,   setModelAgent4]   = useState<ModelOption>('qwen3')
  const [modelAgent5,   setModelAgent5]   = useState<ModelOption>('qwen3')
  const [manualTests,   setManualTests]   = useState<any[]>([])
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null)
  const [showJson, setShowJson] = useState(true)

  // FIX #4 — single open-modal slot tracked in the page, not inside cards
  const [openModalStep, setOpenModalStep] = useState<any | null>(null)
  const workspaceRef = useRef<HTMLDivElement>(null)

  const toast        = useToast()
  const orchestrator = useOrchestrator(storyId)
  const { data, loading, error, progress, isCompleted, isFailed, run, cancel } = orchestrator

  // FIX #10 — cancel on unmount to avoid state updates after unmount
  const cancelRef = useRef(cancel)
  cancelRef.current = cancel
  useEffect(() => () => { cancelRef.current?.() }, [])

  // FIX #3 — use a single ref-based launch trigger so re-using the same storyId still fires
  const launchParamsRef = useRef<any>(null)
  const [launchToken, setLaunchToken] = useState(0)

  const handleRun = useCallback(() => {
    const id = inputValue.trim().toUpperCase()
    if (!id) return
    setStoryId(id)
    setManualTests([])
    launchParamsRef.current = {
      id,
      use_rag: useRag,
      use_legacy_rag: useLegacyRag,
      run_agent4: runAgent4,
      force_refresh: forceRefresh,
      model_agent1: modelAgent1,
      model_agent15: modelAgent15,
      model_agent2: modelAgent2,
      model_agent3_quality: modelAgent3,
      model_agent4: modelAgent4,
      model_agent5: modelAgent5,
    }
    setLaunchToken(t => t + 1) // always increments → effect always fires
  }, [inputValue, useRag, useLegacyRag, runAgent4, forceRefresh, modelAgent1, modelAgent15, modelAgent2, modelAgent3, modelAgent4, modelAgent5])

  // FIX #5 — stable deps: run and toast are accessed via refs to avoid stale-closure warnings
  const runRef   = useRef(run)
  const toastRef = useRef(toast)
  runRef.current   = run
  toastRef.current = toast

  useEffect(() => {
    if (!launchToken || !launchParamsRef.current) return
    const params = launchParamsRef.current
    const launch = async () => {
      try {
        const resp = await runRef.current({
          use_rag:             params.use_rag,
          use_legacy_rag:      params.use_legacy_rag,
          force_refresh:       params.force_refresh,
          model_agent1:        params.model_agent1,
          model_agent15:       params.model_agent15,
          model_agent2:        params.model_agent2,
          model_agent3_quality: params.model_agent3_quality,
          model_agent5:        params.model_agent5,
        })
        const tests = (resp as any)?.result?.agent2_tests || (resp as any)?.agent2_tests || []
        setManualTests(tests)
        if ((resp as any)?.status === 'completed') toastRef.current.success('Pipeline terminé avec succès !')
      } catch (err: any) {
        toastRef.current.error(err?.message || 'Échec du pipeline')
      }
    }
    launch()
  }, [launchToken])

  useEffect(() => {
    if (data) {
      const tests = (data as any)?.result?.agent2_tests || (data as any)?.agent2_tests || []
      if (tests.length) setManualTests(tests)
    }
  }, [data])

  const steps          = useMemo(() => (data as any)?.steps || [], [data])
  const pipelineResult = (data as any)?.result
  const tokenUsage     = (pipelineResult?.token_usage || {}) as Record<string, any>
  const agent1Step     = steps.find((s: any) => s.agent === 'Agent 1')
  const agent2Step     = steps.find((s: any) => s.agent === 'Agent 2')
  const selectedStep   = steps.find((s: any) => s.agent === selectedAgent) || null

  useEffect(() => {
    if (agent2Step?.status === 'completed' && agent2Step.output) {
      setSelectedAgent('Agent 2')
    }
  }, [agent2Step?.status, agent2Step?.output])

  const handleSelectAgent = useCallback((agent: string) => {
    setSelectedAgent(agent)
    setTimeout(() => {
      workspaceRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }, 80)
  }, [])

  const pipelineWarnings = useMemo(() => {
    const warnings: Array<{ title: string; description: string }> = []
    const errorText =
      (data as any)?.error ||
      agent1Step?.error ||
      agent2Step?.error ||
      (Array.isArray(pipelineResult?.errors) ? pipelineResult.errors.join(' ') : '')

    if (errorText) {
      const normalized = String(errorText).toLowerCase()
      if (/introuvable|not found|story.*not.*found|404/.test(normalized)) {
        warnings.push({
          title: 'Story Jira introuvable',
          description: 'Le Story ID n\'a pas été trouvé dans Jira. Vérifiez l\'identifiant et réessayez.',
        })
      }
    }

    if (pipelineResult?.status === 'skipped' && pipelineResult.story_type) {
      const storyType = pipelineResult.story_type
      const defaultDescription = storyType === 'invalid_or_too_weak'
        ? `Cette story a été classée « ${storyType} », la story est sans description, on ne peut pas générer des tests, il faut contacter le PO pour qu’il explique le besoin.`
        : `Cette story a été classée « ${storyType} » et n'est pas traitée par le pipeline fonctionnel.`

      warnings.push({
        title: 'Story non fonctionnelle',
        description: pipelineResult.errors?.[0]
          ? pipelineResult.errors[0]
          : defaultDescription,
      })
    }

    if (pipelineResult?.status === 'failed') {
      const noTestError = Array.isArray(pipelineResult.errors)
        ? pipelineResult.errors.find((e: string) =>
            /agent 2 n'a pas pu générer|aucun test généré|pas de tests/.test(e.toLowerCase()))
        : undefined
      if (noTestError) {
        warnings.push({ title: 'Aucun test généré', description: noTestError })
      }
    }

    if (!pipelineResult?.story_type && pipelineResult?.status === 'failed' && !warnings.length && errorText) {
      warnings.push({ title: 'Erreur de pipeline', description: String(errorText) })
    }

    return warnings
  }, [data, pipelineResult, agent1Step, agent2Step])

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-fade-in">

      {/* Header */}
      <div className="flex items-center gap-4">
        <div className="syn-icon-box">
          <GitBranch size={20} />
        </div>
        <div>
          <h1 className="text-2xl font-extrabold text-brand-navy">Pipeline IA</h1>
          <p className="text-sm text-brand-muted">Génération automatique de tests depuis vos user stories Jira</p>
        </div>
        {storyId && (
          <div className="ml-auto flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold font-mono bg-brand-rose/10 border border-brand-rose/20 text-brand-rose">
            <Hash size={13} />
            {storyId}
          </div>
        )}
      </div>

      {/* Launch Form */}
      <div className="syn-surface-lg">
        <div className="syn-strip-hero" />
        <div className="p-6 space-y-6">
          <div className="grid md:grid-cols-2 gap-6">
            <div className="md:col-span-2">
              <label className="syn-label block mb-3">
                Identifiant de la Story Jira
              </label>
              <div className="flex gap-3">
                <div className="relative flex-1">
                  <Hash size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-brand-rose" />
                  <input
                    type="text"
                    placeholder="ex : NUXEPM-2144"
                    value={inputValue}
                    onChange={e => setInputValue(e.target.value.toUpperCase())}
                    onKeyDown={e => e.key === 'Enter' && !loading && handleRun()}
                    className="w-full pl-11 pr-4 py-4 border-2 rounded-2xl text-base font-mono font-bold text-brand-navy placeholder:text-gray-300 focus:outline-none transition-all bg-white border-gray-200 focus:border-brand-violet focus:shadow-[0_0_0_3px_rgba(124,58,237,0.12)]"
                  />
                </div>
                {loading ? (
                  <button type="button" onClick={cancel}
                    className="px-6 py-4 rounded-2xl font-bold text-white flex items-center gap-2 flex-shrink-0 transition-all hover:-translate-y-0.5"
                    style={{ background: 'linear-gradient(135deg,#dc2626,#b91c1c)', boxShadow: '0 4px 16px rgba(220,38,38,0.35)' }}>
                    <Square size={16} /> Arrêter
                  </button>
                ) : (
                  <div className="flex items-center gap-3">
                    <button type="button" onClick={handleRun}
                      disabled={!inputValue.trim()}
                      className="px-8 py-4 rounded-2xl font-bold text-white flex items-center gap-2 flex-shrink-0 transition-all hover:-translate-y-0.5 hover:shadow-lg disabled:opacity-40 disabled:cursor-not-allowed disabled:transform-none"
                      style={{ background: BUTTON_GRADIENT, boxShadow: `0 4px 18px rgba(219,39,119,0.38)` }}>
                      <Play size={16} /> Lancer le Pipeline
                    </button>
                  </div>
                )}
              </div>
              <p className="text-xs mt-2 ml-1" style={{ color: `${NAV}50` }}>Appuyez sur Entrée ou cliquez sur « Lancer »</p>
            </div>

            <div>
              <p className="text-xs font-bold uppercase tracking-widest mb-3" style={{ color: `${NAV}60` }}>⚙️ Options</p>
              <div className="space-y-4">
                <Toggle checked={useRag}       onChange={setUseRag}       label="Contexte RAG"              desc="Enrichissement par la base de connaissances" />
                <Toggle checked={useLegacyRag} onChange={setUseLegacyRag} label="RAG Legacy"                desc="Ancien système de récupération" />
                <Toggle checked={forceRefresh} onChange={setForceRefresh} label="Renforcer l'enrichissement" desc="Force le rechargement des données complet" />
                <Toggle checked={runAgent4}    onChange={setRunAgent4}    label="Rapport Agent 4"           desc="Génération du rapport qualité final" />
              </div>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 mt-2">
            <ModelSelector label="Modèle Agent 1"   value={modelAgent1}  onChange={setModelAgent1}  />
            <ModelSelector label="Modèle Agent 1.5" value={modelAgent15} onChange={setModelAgent15} />
            <ModelSelector label="Modèle Agent 2"   value={modelAgent2}  onChange={setModelAgent2}  />
            <ModelSelector label="Modèle Agent 3"   value={modelAgent3}  onChange={setModelAgent3}  />
            <ModelSelector label="Modèle Agent 5"   value={modelAgent5}  onChange={setModelAgent5}  />
            <ModelSelector label="Modèle Agent 4"   value={modelAgent4}  onChange={setModelAgent4}  disabled={!runAgent4} />
          </div>

          {showJson && (
            <div className="mt-4">
              <AgentSectionTitle>Données JSON — Pipeline</AgentSectionTitle>
              <pre className="rounded-2xl bg-slate-50 p-3 text-xs text-slate-700 overflow-auto" style={{ maxHeight: 360 }}>
                {JSON.stringify((data as any)?.result || (data as any) || {}, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>

      {error && <Alert type="error" title="Erreur Pipeline" description={error?.message || String(error)} />}

      {pipelineWarnings.length > 0 && (
        <div className="bg-orange-50 rounded-3xl border border-orange-200 p-5">
          {pipelineWarnings.map((warning, index) => (
            <div key={index} className={index > 0 ? 'mt-4' : ''}>
              <div className="flex items-start gap-3">
                <div className="w-9 h-9 rounded-2xl flex items-center justify-center flex-shrink-0 bg-orange-100 text-orange-600">
                  <AlertTriangle size={18} />
                </div>
                <div className="flex-1">
                  <h3 className="text-sm font-bold text-orange-900">{warning.title}</h3>
                  <p className="text-sm text-orange-800 mt-1">{warning.description}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {!data && !loading && !storyId && (
        <div className="syn-empty py-16">
          <div className="syn-icon-box mx-auto mb-4 opacity-50">
            <GitBranch size={22} />
          </div>
          <p className="font-bold text-lg text-brand-navy mb-2">Entrez un ID de Story pour commencer</p>
          <p className="text-sm text-brand-muted">Les agents IA vont analyser, générer et valider vos tests automatiquement</p>
        </div>
      )}

      {(loading || data) && (
        <div className="space-y-4">
          {/* Progress bar */}
          <div className="syn-surface p-5">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold text-brand-navy">Exécution du pipeline</span>
                {loading && (
                  <span className="flex items-center gap-1.5 text-xs font-semibold animate-pulse text-brand-orange">
                    <span className="w-1.5 h-1.5 rounded-full inline-block bg-brand-orange" />
                    En cours…
                  </span>
                )}
              </div>
              <div className="flex items-center gap-3">
                <span className="text-2xl font-extrabold text-brand-navy">{progress}%</span>
                {data && (
                  <span className={`syn-badge ${
                    isCompleted ? 'syn-badge--navy' : isFailed ? 'syn-badge--rose' : 'syn-badge--orange'
                  }`}>
                    {(data as any).status}
                  </span>
                )}
              </div>
            </div>
            <div className="h-2.5 rounded-full overflow-hidden bg-brand-navy/[0.06]">
              <div
                className="h-full rounded-full transition-all duration-700 syn-strip-hero"
                style={{ width: `${progress}%`, height: '100%' }}
              />
            </div>
            {data && (
              <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
                {[
                  { label: 'Agent 1',     value: modelAgent1 },
                  { label: 'Agent 1.5',   value: modelAgent15 },
                  { label: 'Agent 2',     value: modelAgent2 },
                  { label: 'Agent 3',     value: modelAgent3 },
                  { label: 'Agent 4 / 5', value: runAgent4 ? `${modelAgent4} / ${modelAgent5}` : modelAgent5 },
                ].map(({ label, value }) => (
                  <div key={label} className="rounded-2xl bg-slate-50 p-4 border border-slate-200">
                    <p className="text-[10px] uppercase tracking-[0.18em] text-slate-500">{label}</p>
                    <p className="mt-2 text-sm font-semibold text-slate-900">{value}</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Agent tabs + workspace */}
          {steps.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between px-1">
                <p className="syn-label">Résultats des agents</p>
                <p className="text-[11px] text-brand-muted">
                  Cliquez sur un agent · icône ⛶ pour le plein écran
                </p>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
                {steps.map((step: any, idx: number) => (
                  <AgentResultCard
                    key={idx}
                    step={step}
                    isSelected={selectedAgent === step.agent}
                    onSelect={() => handleSelectAgent(step.agent)}
                    onExpand={() => setOpenModalStep(step)}
                  />
                ))}
              </div>

              <div ref={workspaceRef}>
                <AgentWorkspace
                  step={selectedStep}
                  storyId={storyId}
                  manualTests={manualTests}
                  onTestsChange={setManualTests}
                />
              </div>
            </div>
          )}

          {/* Token usage */}
          {pipelineResult?.token_usage && (
            <div className="bg-white rounded-3xl border border-slate-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <p className="text-sm font-semibold text-slate-900">Utilisation des tokens</p>
                  <p className="text-xs text-slate-500">Détail par agent et par modèle</p>
                </div>
                <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">LLM</span>
              </div>
              <div className="grid gap-4 lg:grid-cols-2">
                <div className="rounded-3xl bg-slate-50 p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-500 mb-3">Totaux pipeline</p>
                  <div className="space-y-2 text-sm text-slate-700">
                    <p><strong>Appels :</strong> {pipelineResult.token_usage._totals?.calls ?? 0}</p>
                    <p><strong>Prompt :</strong> {pipelineResult.token_usage._totals?.prompt_tokens ?? 0}</p>
                    <p><strong>Completion :</strong> {pipelineResult.token_usage._totals?.completion_tokens ?? 0}</p>
                    <p><strong>Total :</strong> {pipelineResult.token_usage._totals?.total_tokens ?? 0}</p>
                  </div>
                </div>
                <div className="rounded-3xl bg-slate-50 p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-500 mb-3">Par agent</p>
                  <div className="space-y-3 text-sm text-slate-700">
                    {Object.entries(tokenUsage)
                      .filter(([key]) => key !== '_totals')
                      .map(([agent, agentUsage]) => {
                        const usage = agentUsage as Record<string, any>
                        return (
                          <div key={agent} className="rounded-2xl bg-white p-3 border border-slate-200">
                            <p className="font-semibold text-slate-900">{agent}</p>
                            <p className="text-xs text-slate-500 mt-1">
                              {usage._totals?.total_tokens ?? 0} tokens • {usage._totals?.calls ?? 0} appels
                            </p>
                          </div>
                        )
                      })}
                  </div>
                </div>
              </div>
            </div>
          )}

          {loading && steps.length === 0 && (
            <div className="bg-white rounded-3xl border py-16 text-center"
              style={{ borderColor: 'rgba(10,22,40,0.08)' }}>
              <div className="relative w-16 h-16 mx-auto mb-4">
                <div className="absolute inset-0 rounded-full border-2" style={{ borderColor: `${NAV}12` }} />
                <div className="absolute inset-0 rounded-full border-2 border-t-transparent animate-spin"
                  style={{ borderColor: `${VIOLET}50`, borderTopColor: 'transparent' }} />
                <div className="absolute inset-2 rounded-full border-2 border-t-transparent animate-spin"
                  style={{ borderColor: `${ROSE}50`, borderTopColor: 'transparent', animationDirection: 'reverse', animationDuration: '0.7s' }} />
              </div>
              <p className="font-semibold" style={{ color: NAV }}>Initialisation du pipeline…</p>
              <p className="text-sm mt-1" style={{ color: `${NAV}50` }}>Les agents démarrent</p>
            </div>
          )}

          {isCompleted && (
            <Alert type="success" title="✅ Pipeline terminé avec succès !"
              description="Tous les agents ont terminé. Consultez les résultats ci-dessous." />
          )}
          {isFailed && (
            <Alert type="error" title="Pipeline échoué"
              description="Une erreur est survenue lors de l'exécution." />
          )}
        </div>
      )}

      {/* Modal plein écran (optionnel) */}
      {openModalStep && (
        <AgentResultModal
          step={openModalStep}
          storyId={storyId}
          onClose={() => setOpenModalStep(null)}
        />
      )}
    </div>
  )
}
