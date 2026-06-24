import React, { useState, useCallback } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import { useOrchestrator } from '../hooks'
import { ManualTestsTable } from '../components/tests/ManualTestsTable'
import { Badge } from '../components/ui/Badge'
import { Alert } from '../components/ui/Alert'
import {
  Play, Square, GitBranch, CheckCircle2, XCircle,
  Clock, Cpu, AlertTriangle, ChevronRight, Bot,
  FileText, TestTube, BarChart3, FileBarChart2,
  Sparkles, Hash, ToggleLeft, ToggleRight
} from 'lucide-react'

/* ──────────────────────────────────────────────────────
   Types & constants
────────────────────────────────────────────────────── */
const STEP_STYLE: Record<string, { bg: string; border: string; icon: React.ElementType; spin?: boolean }> = {
  completed: { bg: 'rgba(16,185,129,0.06)',  border: 'rgba(16,185,129,0.2)',  icon: CheckCircle2 },
  failed:    { bg: 'rgba(244,63,94,0.06)',   border: 'rgba(244,63,94,0.2)',   icon: XCircle },
  running:   { bg: 'rgba(249,115,22,0.06)',  border: 'rgba(249,115,22,0.2)',  icon: Cpu, spin: true },
  pending:   { bg: 'rgba(100,116,139,0.05)', border: 'rgba(100,116,139,0.1)', icon: Clock },
}

const STEP_TEXT: Record<string, string> = {
  completed: 'text-emerald-600',
  failed:    'text-brand-rose',
  running:   'text-brand-orange',
  pending:   'text-brand-muted',
}

const AGENT_INFO: Record<string, { label: string; desc: string; icon: React.ElementType; color: string }> = {
  'Agent 1': { label: 'Récupération Story',  desc: 'Fetch Jira & RAG context',            icon: FileText,      color: '#7c3aed' },
  'Agent 2': { label: 'Génération Tests',    desc: 'Scénarios manuels & automatisés',     icon: TestTube,      color: '#f43f5e' },
  'Agent 3': { label: 'Validation',          desc: 'Couverture & cas limites',             icon: CheckCircle2, color: '#f97316' },
  'Agent 4': { label: 'Rapport Qualité',     desc: 'Score global & recommandations',       icon: FileBarChart2, color: '#ec4899' },
  'Agent 5': { label: 'Analyse Avancée',     desc: 'Métriques approfondies',               icon: BarChart3,     color: '#a855f7' },
}

/* ──────────────────────────────────────────────────────
   Toggle Switch component
────────────────────────────────────────────────────── */
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
      className={`relative w-11 h-6 rounded-full flex-shrink-0 transition-all duration-200 focus:outline-none ${
        checked ? 'bg-grad-cta shadow-glow-rose' : 'bg-gray-200'
      }`}
      style={checked ? { background: 'linear-gradient(135deg,#f43f5e,#f97316)' } : {}}
    >
      <span
        className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow-sm transition-all duration-200 ${
          checked ? 'left-5' : 'left-0.5'
        }`}
      />
    </button>
    <div className="flex-1 min-w-0">
      <p className="text-sm font-semibold text-brand-navy group-hover:text-brand-violet transition-colors leading-tight">
        {label}
      </p>
      {desc && <p className="text-xs text-brand-muted mt-0.5">{desc}</p>}
    </div>
  </label>
)

/* ──────────────────────────────────────────────────────
   Agent Result Card
────────────────────────────────────────────────────── */
const AgentResultCard: React.FC<{ step: any; index: number }> = ({ step, index }) => {
  const [expanded, setExpanded] = useState(false)
  const status = step.status as string
  const style = STEP_STYLE[status] || STEP_STYLE.pending
  const textColor = STEP_TEXT[status] || 'text-brand-muted'
  const Icon = style.icon
  const agentKey = Object.keys(AGENT_INFO).find(k =>
    (step.agent || '').toLowerCase().includes(k.toLowerCase().replace('agent ', ''))
    || (step.agent || '') === k
  )
  const info = agentKey ? AGENT_INFO[agentKey] : null

  return (
    <div
      className="rounded-2xl border transition-all duration-300"
      style={{ background: style.bg, borderColor: style.border }}
    >
      <div
        className="flex items-center gap-3 p-4 cursor-pointer"
        onClick={() => status === 'completed' && setExpanded(!expanded)}
      >
        {/* Index bubble */}
        <div
          className="w-8 h-8 rounded-xl flex items-center justify-center text-white text-xs font-bold flex-shrink-0"
          style={{ background: info ? info.color : 'var(--grad-cta)', opacity: status === 'pending' ? 0.4 : 1 }}
        >
          {index + 1}
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <p className="font-bold text-brand-navy text-sm">
              {info?.label || step.agent}
            </p>
            {info && (
              <span className="text-[10px] text-brand-muted font-medium hidden sm:inline">
                — {info.desc}
              </span>
            )}
          </div>
          {step.error && (
            <p className="text-xs text-brand-rose mt-0.5 flex items-center gap-1">
              <AlertTriangle size={11} /> {step.error}
            </p>
          )}
        </div>

        {/* Status */}
        <div className="flex items-center gap-2 flex-shrink-0">
          <Icon
            size={16}
            className={`${textColor} ${style.spin ? 'animate-spin-slow' : ''}`}
          />
          <Badge
            variant={status === 'completed' ? 'success' : status === 'failed' ? 'error' : status === 'running' ? 'orange' : 'default'}
            size="sm"
            dot
          >
            {status}
          </Badge>
          {status === 'completed' && (
            <ChevronRight
              size={14}
              className={`text-brand-muted transition-transform ${expanded ? 'rotate-90' : ''}`}
            />
          )}
        </div>
      </div>

      {/* Expanded output */}
      {expanded && step.output && (
        <div className="px-4 pb-4 pt-0 animate-fade-in">
          <div className="rounded-xl overflow-hidden border border-white/60">
            <div className="px-3 py-2 bg-white/60 border-b border-white/60 flex items-center gap-2">
              <Sparkles size={12} className="text-brand-violet" />
              <span className="text-[10px] font-bold text-brand-navy uppercase tracking-wider">
                Résultat de l'agent
              </span>
            </div>
            <div className="p-3 bg-white/40 text-xs text-brand-navy font-mono leading-relaxed max-h-48 overflow-y-auto whitespace-pre-wrap">
              {typeof step.output === 'string'
                ? step.output
                : JSON.stringify(step.output, null, 2)}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

/* ──────────────────────────────────────────────────────
   Main Pipeline Page
────────────────────────────────────────────────────── */
export const PipelinePage: React.FC = () => {
  const [storyId, setStoryId] = useState('')
  const [inputValue, setInputValue] = useState('')
  const [useRag, setUseRag] = useState(true)
  const [useLegacyRag, setUseLegacyRag] = useState(false)
  const [runAgent4, setRunAgent4] = useState(true)
  const [manualTests, setManualTests] = useState<any[]>([])
  const [hasLaunched, setHasLaunched] = useState(false)

  const toast = useToast()
  const orchestrator = useOrchestrator(storyId)
  const { data, loading, error, progress, isCompleted, isFailed, run, cancel } = orchestrator

  const handleRun = useCallback(async () => {
    const id = inputValue.trim().toUpperCase()
    if (!id) return
    setStoryId(id)
    setHasLaunched(true)
    setManualTests([])
  }, [inputValue])

  // Launch after storyId is set
  React.useEffect(() => {
    if (!storyId || !hasLaunched) return
    const launch = async () => {
      try {
        const resp = await run({ use_rag: useRag, use_legacy_rag: useLegacyRag, run_agent4: runAgent4, force_refresh: false })
        const tests = (resp as any)?.agent2_tests || (resp as any)?.result?.agent2_tests || []
        setManualTests(tests)
        if ((resp as any)?.status === 'completed') toast.success('Pipeline terminé avec succès !')
      } catch (err: any) {
        toast.error(err?.message || 'Échec du pipeline')
      }
    }
    launch()
    setHasLaunched(false)
  }, [storyId, hasLaunched])

  React.useEffect(() => {
    if (data) {
      const tests = (data as any)?.agent2_tests || (data as any)?.result?.agent2_tests || []
      if (tests.length) setManualTests(tests)
    }
  }, [data])

  const steps: any[] = (data as any)?.steps || []

  return (
    <div className="max-w-5xl mx-auto space-y-6 animate-fade-in">

      {/* ── Header ──────────────────────────────────── */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-2xl flex items-center justify-center flex-shrink-0"
          style={{ background: 'linear-gradient(135deg,#ef4444,#f43f5e,#f97316)' }}>
          <GitBranch size={18} className="text-white" />
        </div>
        <div>
          <h1 className="text-2xl font-extrabold text-brand-navy">Pipeline IA</h1>
          <p className="text-sm text-brand-muted">Génération automatique de tests depuis vos user stories Jira</p>
        </div>
        {storyId && (
          <div className="ml-auto flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold font-mono"
            style={{ background: 'rgba(244,63,94,0.08)', border: '1px solid rgba(244,63,94,0.2)', color: '#f43f5e' }}>
            <Hash size={13} />
            {storyId}
          </div>
        )}
      </div>

      {/* ── Launch Form ─────────────────────────────── */}
      <div className="bg-white rounded-3xl border border-gray-100 shadow-card overflow-hidden">
        {/* Color strip */}
        <div className="h-1.5" style={{ background: 'linear-gradient(90deg,#ef4444,#f43f5e,#ec4899,#7c3aed,#f97316)' }} />

        <div className="p-6">
          <div className="grid md:grid-cols-2 gap-6">
            {/* Story ID Input */}
            <div className="md:col-span-2">
              <label className="block text-xs font-bold text-brand-navy/60 uppercase tracking-widest mb-3">
                🎯 Identifiant de la Story Jira
              </label>
              <div className="flex gap-3">
                <div className="relative flex-1">
                  <Hash size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-brand-rose" />
                  <input
                    type="text"
                    id="pipeline-story-id"
                    placeholder="ex : NUXEPM-2144"
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value.toUpperCase())}
                    onKeyDown={(e) => e.key === 'Enter' && !loading && handleRun()}
                    className="w-full pl-11 pr-4 py-4 border-2 border-gray-100 rounded-2xl text-base font-mono font-bold text-brand-navy placeholder:text-gray-300 focus:border-brand-rose transition-all bg-white shadow-sm"
                  />
                </div>
                {loading ? (
                  <button
                    type="button"
                    onClick={cancel}
                    className="px-6 py-4 rounded-2xl font-bold text-white flex items-center gap-2 flex-shrink-0 transition-all hover:-translate-y-0.5"
                    style={{ background: 'linear-gradient(135deg,#ef4444,#dc2626)', boxShadow: '0 4px 16px rgba(239,68,68,0.4)' }}
                  >
                    <Square size={16} /> Arrêter
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={handleRun}
                    disabled={!inputValue.trim()}
                    className="px-8 py-4 rounded-2xl font-bold text-white flex items-center gap-2 flex-shrink-0 transition-all hover:-translate-y-0.5 disabled:opacity-40 disabled:cursor-not-allowed disabled:transform-none"
                    style={{
                      background: 'linear-gradient(135deg,#ef4444,#f43f5e,#f97316)',
                      boxShadow: inputValue.trim() ? '0 6px 24px rgba(244,63,94,0.45)' : 'none',
                    }}
                  >
                    <Play size={16} /> Lancer le Pipeline
                  </button>
                )}
              </div>
              <p className="text-xs text-brand-muted mt-2 ml-1">Appuyez sur Entrée ou cliquez sur « Lancer »</p>
            </div>

            {/* Options */}
            <div>
              <p className="text-xs font-bold text-brand-navy/60 uppercase tracking-widest mb-3">⚙️ Options</p>
              <div className="space-y-2">
                <Toggle checked={useRag}       onChange={setUseRag}       label="Contexte RAG"    desc="Enrichissement par la base de connaissances" />
                <Toggle checked={useLegacyRag} onChange={setUseLegacyRag} label="RAG Legacy"       desc="Ancien système de récupération" />
                <Toggle checked={runAgent4}    onChange={setRunAgent4}    label="Rapport Agent 4"  desc="Génération du rapport qualité final" />
              </div>
            </div>

            {/* How it works */}
            <div className="rounded-2xl p-4" style={{ background: 'linear-gradient(135deg,rgba(124,58,237,0.06),rgba(244,63,94,0.04))', border: '1px solid rgba(124,58,237,0.12)' }}>
              <p className="text-xs font-bold text-brand-violet uppercase tracking-widest mb-3 flex items-center gap-1.5">
                <Bot size={12} /> Comment ça fonctionne
              </p>
              {[
                { n: 1, t: 'Récupération', c: '#7c3aed' },
                { n: 2, t: 'Génération des tests', c: '#f43f5e' },
                { n: 3, t: 'Validation', c: '#f97316' },
                { n: 4, t: 'Rapport final', c: '#ec4899' },
              ].map(step => (
                <div key={step.n} className="flex items-center gap-2 mb-2 last:mb-0">
                  <span className="w-5 h-5 rounded-md flex items-center justify-center text-white text-[10px] font-bold flex-shrink-0"
                    style={{ background: step.c }}>
                    {step.n}
                  </span>
                  <span className="text-xs text-brand-navy font-medium">{step.t}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ── Error ───────────────────────────────────── */}
      {error && <Alert type="error" title="Erreur Pipeline" description={error.message} />}

      {/* ── Empty state ─────────────────────────────── */}
      {!data && !loading && !storyId && (
        <div className="bg-white rounded-3xl border border-gray-100 shadow-card py-20 text-center">
          <div className="w-20 h-20 mx-auto mb-5 rounded-3xl flex items-center justify-center"
            style={{ background: 'linear-gradient(135deg,rgba(244,63,94,0.08),rgba(249,115,22,0.06))' }}>
            <GitBranch size={32} className="text-brand-rose/50" />
          </div>
          <p className="text-brand-navy font-bold text-lg mb-2">Entrez un ID de Story pour commencer</p>
          <p className="text-brand-muted text-sm">Les agents IA vont analyser, générer et valider vos tests automatiquement</p>
        </div>
      )}

      {/* ── Pipeline Running / Results ───────────────── */}
      {(loading || data) && (
        <div className="space-y-4">

          {/* Progress Header */}
          <div className="bg-white rounded-3xl border border-gray-100 shadow-card p-5">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold text-brand-navy">Exécution du Pipeline</span>
                {loading && (
                  <span className="flex items-center gap-1 text-xs text-brand-orange font-semibold animate-pulse">
                    <span className="w-1.5 h-1.5 rounded-full bg-brand-orange inline-block" />
                    En cours…
                  </span>
                )}
              </div>
              <div className="flex items-center gap-3">
                <span className="text-2xl font-extrabold text-brand-navy">{progress}%</span>
                {data && (
                  <Badge
                    variant={isCompleted ? 'success' : isFailed ? 'error' : 'orange'}
                    dot size="sm"
                  >
                    {(data as any).status}
                  </Badge>
                )}
              </div>
            </div>
            {/* Progress bar */}
            <div className="h-2 rounded-full overflow-hidden" style={{ background: 'rgba(10,15,46,0.06)' }}>
              <div
                className="h-full rounded-full transition-all duration-700 relative overflow-hidden"
                style={{
                  width: `${progress}%`,
                  background: 'linear-gradient(90deg,#ef4444,#f43f5e,#f97316)',
                  boxShadow: '0 0 10px rgba(244,63,94,0.4)',
                }}
              >
                <div className="absolute inset-0"
                  style={{ background: 'linear-gradient(90deg,transparent,rgba(255,255,255,0.35),transparent)', animation: 'shimmer 1.5s linear infinite', backgroundSize: '200% auto' }} />
              </div>
            </div>
          </div>

          {/* Agent Steps */}
          {steps.length > 0 && (
            <div className="space-y-3">
              <p className="text-xs font-bold text-brand-navy/50 uppercase tracking-widest px-1">
                Résultats des Agents
              </p>
              {steps.map((step, idx) => (
                <AgentResultCard key={idx} step={step} index={idx} />
              ))}
            </div>
          )}

          {/* Loading spinner if no steps yet */}
          {loading && steps.length === 0 && (
            <div className="bg-white rounded-3xl border border-gray-100 shadow-card py-16 text-center">
              <div className="relative w-16 h-16 mx-auto mb-4">
                <div className="absolute inset-0 rounded-full border-2 border-brand-rose/15" />
                <div className="absolute inset-0 rounded-full border-2 border-t-brand-rose border-transparent animate-spin" />
                <div className="absolute inset-2 rounded-full border-2 border-t-brand-orange border-transparent animate-spin" style={{ animationDirection: 'reverse', animationDuration: '0.7s' }} />
              </div>
              <p className="text-brand-navy font-semibold">Initialisation du pipeline…</p>
              <p className="text-brand-muted text-sm mt-1">Les agents démarrent</p>
            </div>
          )}

          {/* Completed alert */}
          {isCompleted && (
            <Alert type="success" title="✅ Pipeline terminé avec succès !" description="Tous les agents ont terminé. Consultez les résultats ci-dessous." />
          )}
          {isFailed && (
            <Alert type="error" title="Pipeline échoué" description="Une erreur est survenue lors de l'exécution." />
          )}
        </div>
      )}

      {/* ── Manual Tests Table ──────────────────────── */}
      {manualTests.length > 0 && storyId && (
        <div>
          <p className="text-xs font-bold text-brand-navy/50 uppercase tracking-widest px-1 mb-3">
            Tests Manuels Générés
          </p>
          <ManualTestsTable
            tests={manualTests}
            storyId={storyId}
            onTestsChange={setManualTests}
          />
        </div>
      )}
    </div>
  )
}
