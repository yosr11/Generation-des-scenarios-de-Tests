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
  Sparkles, Hash, ToggleLeft, ToggleRight,
  Target, Shield, AlertCircle, TrendingUp, List, ChevronDown
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
  'Agent 1': { label: 'Agent 1 : Analyse',              desc: 'Analyse sémantique de la user story',     icon: FileText,      color: '#3b82f6' },
  'Agent 2': { label: 'Agent 2 : Génération des tests', desc: 'Création des scénarios de tests manuels', icon: TestTube,      color: '#06b6d4' },
  'Agent 3': { label: 'Agent 3 : Validation',           desc: 'Couverture, ambiguïtés & cas limites',    icon: CheckCircle2,  color: '#10b981' },
  'Agent 4': { label: 'Agent 4 : Classification',       desc: 'Classification auto/manuel',              icon: BarChart3,     color: '#6366f1' },
  'Agent 5': { label: 'Agent 5 : Rapport',              desc: 'Rapport qualité & recommandations',       icon: FileBarChart2, color: '#8b5cf6' },
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
      style={checked ? { background: 'linear-gradient(135deg,#2563eb,#4f46e5)' } : {}}
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
   Rich result renderers per agent
────────────────────────────────────────────────────── */

const Agent1Result: React.FC<{ output: any }> = ({ output }) => {
  if (!output) return null
  
  const entries = Object.entries(output)
  
  return (
    <div className="space-y-6 text-sm bg-white p-6 rounded-2xl border border-gray-100 shadow-sm">
      {entries.map(([key, val]) => {
        const label = key.replace(/_/g, ' ').toUpperCase()
        
        if (typeof val === 'string' || typeof val === 'number') {
          return (
            <div key={key} className="flex items-center gap-3">
              <p className="text-[10px] font-bold text-brand-navy/50 tracking-widest w-24 flex-shrink-0">{label}</p>
              <span className="px-3 py-1 rounded-lg font-bold text-xs" style={{ background: 'rgba(124,58,237,0.1)', color: '#7c3aed' }}>
                {String(val)}
              </span>
            </div>
          )
        }
        
        if (Array.isArray(val) && val.length > 0) {
          // Simple string array like actors
          if (key === 'actors' || key === 'acteurs') {
            return (
              <div key={key}>
                <p className="text-[10px] font-bold text-brand-navy/50 tracking-widest mb-2">{label}</p>
                <div className="flex flex-wrap gap-2">
                  {val.map((a: any, i: number) => (
                    <span key={i} className="px-3 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-100">
                      {String(a)}
                    </span>
                  ))}
                </div>
              </div>
            )
          }
          
          // Regular list (testable points, rules, etc.)
          return (
            <div key={key}>
              <p className="text-[10px] font-bold text-brand-navy/50 tracking-widest mb-2">{label}</p>
              <ul className="space-y-2">
                {val.map((item: any, i: number) => (
                  <li key={i} className="flex items-start gap-2.5 text-brand-navy/80">
                    <Target size={14} className="mt-0.5 flex-shrink-0 text-brand-violet" />
                    <span className="text-sm leading-relaxed">
                      {typeof item === 'string' ? item : item?.description || JSON.stringify(item)}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )
        }
        
        if (typeof val === 'object' && val !== null) {
          return (
             <div key={key}>
               <p className="text-[10px] font-bold text-brand-navy/50 tracking-widest mb-2">{label}</p>
               <pre className="text-xs bg-gray-50 p-3 rounded-xl border border-gray-200 overflow-x-auto text-gray-700 font-mono">
                 {JSON.stringify(val, null, 2)}
               </pre>
             </div>
          )
        }
        
        return null
      })}
    </div>
  )
}

const Agent2Result: React.FC<{ output: any }> = ({ output }) => {
  const tests = Array.isArray(output) ? output : output?.tests || []
  if (!tests.length) return <p className="text-sm text-gray-500 italic p-4 text-center">Aucun test généré</p>

  return (
    <div className="space-y-8 print:space-y-8">
      {tests.map((test: any, idx: number) => {
        const allSteps = test.steps || test.étapes?.flatMap((e: any) => e.steps || []) || []

        return (
          <div key={idx} className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden print:border-gray-300 print:shadow-none print:break-inside-avoid">
            {/* Test Header */}
            <div className="bg-gray-50 px-6 py-4 border-b border-gray-200">
              <h4 className="font-bold text-brand-navy text-lg">{test.test_name || test.title || `Test ${idx + 1}`}</h4>
            </div>

            <div className="p-6 space-y-6">
              {/* Description */}
              <div>
                <h5 className="font-bold text-brand-navy flex items-center gap-1.5 mb-3">
                  <ChevronDown size={18} className="text-gray-400" /> Description
                </h5>
                <div className="pl-6 space-y-3">
                  {allSteps.map((step: any, si: number) => (
                    <p key={si} className="text-sm text-gray-800 leading-relaxed">
                      <span className="text-blue-500 font-medium">[{step.actor || 'Collaborateur'}]</span> {step.titre || step.action}
                    </p>
                  ))}
                </div>
              </div>

              {/* Steps Table */}
              <div className="border border-gray-200 rounded-xl overflow-hidden shadow-sm print:border-gray-300 print:shadow-none">
                <table className="w-full text-sm text-left">
                  <thead className="bg-[#f4f5f7] border-b border-gray-200">
                    <tr>
                      <th className="w-12 px-4 py-3 font-semibold text-brand-navy border-r border-gray-200 text-center">#</th>
                      <th className="w-1/3 px-4 py-3 font-semibold text-brand-navy border-r border-gray-200">Action</th>
                      <th className="w-1/3 px-4 py-3 font-semibold text-brand-navy border-r border-gray-200">Data</th>
                      <th className="w-1/3 px-4 py-3 font-semibold text-brand-navy">Expected Result</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {allSteps.map((step: any, si: number) => (
                      <tr key={si} className="align-top bg-white hover:bg-gray-50/50 transition-colors print:bg-white">
                        <td className="px-4 py-4 border-r border-gray-200 text-center font-bold text-brand-navy bg-[#f4f5f7]">
                          {si + 1}
                        </td>
                        <td className="px-4 py-4 border-r border-gray-200">
                          <p className="text-sm text-gray-900 mb-3 leading-relaxed">
                            <span className="text-blue-500 font-medium">[{step.actor || 'Collaborateur'}]</span> {step.titre || step.action}
                          </p>
                          {step.titre && step.action && step.titre !== step.action && (
                            <div>
                              <p className="text-xs font-bold uppercase tracking-wider text-brand-navy underline underline-offset-2 mb-2">Action(s):</p>
                              <ul className="list-disc list-inside text-sm text-gray-700 space-y-1.5 ml-1">
                                {step.action.split('\n').map((line: string, i: number) => {
                                  const cleanLine = line.replace(/^-\s*/, '').trim()
                                  return cleanLine ? <li key={i}>{cleanLine}</li> : null
                                })}
                              </ul>
                            </div>
                          )}
                        </td>
                        <td className="px-4 py-4 border-r border-gray-200 whitespace-pre-wrap text-sm text-gray-700 font-mono leading-relaxed bg-[#fbfbfc]">
                          {step.data || ''}
                        </td>
                        <td className="px-4 py-4 whitespace-pre-wrap text-sm text-gray-700 leading-relaxed">
                          {step.expected_result ? (
                            <ul className="list-disc list-inside space-y-1.5 ml-1">
                              {step.expected_result.split('\n').map((line: string, i: number) => {
                                const cleanLine = line.replace(/^-\s*/, '').trim()
                                return cleanLine ? <li key={i}>{cleanLine}</li> : null
                              })}
                            </ul>
                          ) : ''}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

const Agent3Result: React.FC<{ output: any }> = ({ output }) => {
  if (!output) return null
  const report = output?.report || output
  const coverage = report?.coverage_rate ?? report?.coverage_percentage
  const validationStatus = report?.validation_status
  const ambiguities = report?.ambiguities || []
  const uncoveredPoints = report?.uncovered_testable_points || []
  const duplicates = report?.duplicate_tests || report?.duplicates || []

  return (
    <div className="space-y-3">
      {/* KPIs row */}
      <div className="grid grid-cols-3 gap-2">
        {coverage !== undefined && (
          <div className="rounded-xl p-3 text-center" style={{ background: 'rgba(16,185,129,0.06)', border: '1px solid rgba(16,185,129,0.15)' }}>
            <p className="text-2xl font-extrabold" style={{ color: '#10b981' }}>{Math.round((coverage || 0) * 100)}%</p>
            <p className="text-[10px] font-bold text-brand-navy/50 uppercase tracking-widest mt-0.5">Couverture</p>
          </div>
        )}
        {ambiguities.length >= 0 && (
          <div className="rounded-xl p-3 text-center" style={{ background: 'rgba(249,115,22,0.06)', border: '1px solid rgba(249,115,22,0.15)' }}>
            <p className="text-2xl font-extrabold" style={{ color: '#f97316' }}>{ambiguities.length}</p>
            <p className="text-[10px] font-bold text-brand-navy/50 uppercase tracking-widest mt-0.5">Ambiguïtés</p>
          </div>
        )}
        {duplicates.length >= 0 && (
          <div className="rounded-xl p-3 text-center" style={{ background: 'rgba(99,102,241,0.06)', border: '1px solid rgba(99,102,241,0.15)' }}>
            <p className="text-2xl font-extrabold" style={{ color: '#6366f1' }}>{duplicates.length}</p>
            <p className="text-[10px] font-bold text-brand-navy/50 uppercase tracking-widest mt-0.5">Doublons</p>
          </div>
        )}
      </div>

      {validationStatus && (
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-brand-navy/50 uppercase tracking-widest">Statut</span>
          <span className="px-2.5 py-0.5 rounded-full text-xs font-bold"
            style={{
              background: validationStatus === 'valid' ? 'rgba(16,185,129,0.1)' : 'rgba(249,115,22,0.1)',
              color: validationStatus === 'valid' ? '#10b981' : '#f97316',
            }}>
            {validationStatus}
          </span>
        </div>
      )}

      {ambiguities.length > 0 && (
        <div>
          <p className="text-xs font-bold text-brand-navy/50 uppercase tracking-widest mb-1.5">Ambiguïtés détectées</p>
          <ul className="space-y-1">
            {ambiguities.slice(0, 4).map((a: any, i: number) => (
              <li key={i} className="flex items-start gap-2 text-xs text-brand-navy/80">
                <AlertCircle size={11} className="mt-0.5 flex-shrink-0 text-amber-500" />
                <span className="leading-relaxed">{typeof a === 'string' ? a : a.description || JSON.stringify(a)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {duplicates.length > 0 && (
        <div>
          <p className="text-xs font-bold text-brand-navy/50 uppercase tracking-widest mb-1.5">Tests en doublon</p>
          <ul className="space-y-1">
            {duplicates.slice(0, 4).map((d: any, i: number) => (
              <li key={i} className="flex items-start gap-2 text-xs text-brand-navy/80">
                <AlertTriangle size={11} className="mt-0.5 flex-shrink-0 text-brand-violet" />
                <span className="leading-relaxed">{typeof d === 'string' ? d : d.description || JSON.stringify(d)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {uncoveredPoints.length > 0 && (
        <div>
          <p className="text-xs font-bold text-brand-navy/50 uppercase tracking-widest mb-1.5">Points non couverts</p>
          <ul className="space-y-1">
            {uncoveredPoints.slice(0, 3).map((p: string, i: number) => (
              <li key={i} className="flex items-start gap-2 text-xs text-brand-navy/80">
                <XCircle size={11} className="mt-0.5 flex-shrink-0 text-brand-rose" />
                <span className="leading-relaxed">{p}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

const Agent5Result: React.FC<{ output: any }> = ({ output }) => {
  if (!output) return null

  // Recursive renderer for generating a clean document-like text flow
  const renderDocumentSection = (val: any): React.ReactNode => {
    if (typeof val === 'string') {
      return <p className="text-sm text-gray-800 leading-relaxed whitespace-pre-wrap mb-4">{val}</p>
    }
    if (typeof val === 'number' || typeof val === 'boolean') {
      return <p className="text-sm text-gray-800 mb-4">{String(val)}</p>
    }
    if (Array.isArray(val)) {
      return (
        <ul className="list-disc list-inside space-y-2 mb-6 ml-2">
          {val.map((item, idx) => (
            <li key={idx} className="text-sm text-gray-800">
              {typeof item === 'string' ? item : JSON.stringify(item)}
            </li>
          ))}
        </ul>
      )
    }
    if (typeof val === 'object' && val !== null) {
      return (
        <div className="space-y-4 mb-6">
          {Object.entries(val).map(([k, v]) => {
            const heading = k.replace(/_/g, ' ').toUpperCase()
            return (
              <div key={k} className="mt-2">
                <h5 className="text-xs font-bold text-brand-navy/60 tracking-widest mb-2 border-b border-gray-100 pb-1">{heading}</h5>
                {renderDocumentSection(v)}
              </div>
            )
          })}
        </div>
      )
    }
    return null
  }

  return (
    <div className="space-y-6 bg-white p-2 sm:p-6 border border-gray-100 rounded-2xl shadow-sm print:shadow-none print:border-none print:p-0">
      <div className="border-b border-gray-200 pb-4 mb-6 print:pb-2 print:mb-4">
        <h2 className="text-2xl font-bold text-brand-navy">Rapport Final</h2>
        <p className="text-sm text-gray-500 mt-1">Généré automatiquement à partir de l'analyse et de la validation</p>
      </div>

      <div className="prose prose-sm max-w-none">
        {renderDocumentSection(output)}
      </div>

      {/* Bouton Télécharger PDF - hidden in print */}
      <div className="pt-6 border-t border-gray-100 flex justify-end print:hidden">
        <button
          type="button"
          onClick={() => window.print()}
          className="px-6 py-2.5 rounded-xl text-sm font-bold text-white flex items-center gap-2 transition-all hover:-translate-y-0.5 shadow-md"
          style={{ background: 'linear-gradient(135deg,#2563eb,#4f46e5)' }}>
          📥 Télécharger PDF
        </button>
      </div>
    </div>
  )
}

const AgentRichOutput: React.FC<{ agentKey: string; output: any }> = ({ agentKey, output }) => {
  if (!output) return null
  if (agentKey === 'Agent 1') return <Agent1Result output={output} />
  if (agentKey === 'Agent 2') return <Agent2Result output={output} />
  if (agentKey === 'Agent 3') return <Agent3Result output={output} />
  if (agentKey === 'Agent 5') return <Agent5Result output={output} />
  // Agent 4 fallback
  if (typeof output === 'object') {
    const pairs = Object.entries(output).filter(([, v]) => typeof v !== 'object' || v === null)
    return (
      <div className="space-y-1">
        {pairs.slice(0, 6).map(([k, v]) => (
          <div key={k} className="flex items-center gap-2 text-xs">
            <span className="font-semibold text-brand-navy/60 capitalize">{k.replace(/_/g, ' ')}:</span>
            <span className="text-brand-navy">{String(v)}</span>
          </div>
        ))}
      </div>
    )
  }
  return <p className="text-xs text-brand-navy">{String(output)}</p>
}

const AgentResultModal: React.FC<{
  step: any
  onClose: () => void
}> = ({ step, onClose }) => {
  const info = AGENT_INFO[step.agent] || { label: step.agent, icon: Bot, color: '#3b82f6' }
  const Icon = info.icon

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 print:p-0">
      <div className="absolute inset-0 bg-brand-navy/50 backdrop-blur-sm print:hidden" onClick={onClose} />
      <div className="relative bg-white rounded-3xl w-full max-w-2xl max-h-[90vh] overflow-y-auto flex flex-col shadow-2xl print:shadow-none print:max-h-none print:w-full print:rounded-none">
        
        {/* Header */}
        <div className="px-6 py-4 flex items-center gap-4 sticky top-0 bg-white z-10 border-b border-gray-100 print:relative">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center text-white flex-shrink-0" style={{ background: info.color }}>
            <Icon size={20} />
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-bold text-brand-navy">{info.label}</h3>
            <p className="text-sm text-brand-muted">{step.description || 'Détails du résultat'}</p>
          </div>
          <button onClick={onClose} className="p-2 text-brand-muted hover:text-brand-navy rounded-xl hover:bg-gray-100 transition-colors print:hidden">
            <XCircle size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          <AgentRichOutput agentKey={step.agent} output={step.output} />
        </div>
      </div>
    </div>
  )
}

const AgentResultCard: React.FC<{ step: any; index: number }> = ({ step, index }) => {
  const [isOpen, setIsOpen] = useState(false)
  const info = AGENT_INFO[step.agent] || { label: step.agent, icon: Bot, color: '#3b82f6' }
  const statusStyle = STEP_STYLE[step.status] || STEP_STYLE.pending
  const Icon = info.icon

  return (
    <>
      <div
        onClick={() => step.status === 'completed' && setIsOpen(true)}
        className={`bg-white rounded-2xl border transition-all ${step.status === 'completed' ? 'hover:shadow-md cursor-pointer hover:-translate-y-0.5' : 'opacity-80'}`}
        style={{ borderColor: statusStyle.border }}
      >
        <div className="p-4 flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0" style={{ background: statusStyle.bg, color: info.color }}>
            {statusStyle.spin ? <statusStyle.icon size={18} className="animate-spin" /> : <Icon size={18} />}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold text-brand-navy">{info.label}</span>
              <Badge variant={step.status === 'completed' ? 'success' : step.status === 'failed' ? 'error' : step.status === 'running' ? 'orange' : 'gray'} size="sm">
                {step.status}
              </Badge>
            </div>
            <p className="text-xs text-brand-muted truncate mt-0.5">{step.description || info.desc}</p>
          </div>
          <div className="text-brand-muted print:hidden">
            <ChevronRight size={16} />
          </div>
        </div>
      </div>
      {isOpen && <AgentResultModal step={step} onClose={() => setIsOpen(false)} />}
    </>
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
  const [forceRefresh, setForceRefresh] = useState(false)
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
        const resp = await run({
          use_rag: useRag,
          use_legacy_rag: useLegacyRag,
          run_agent4: runAgent4,
          force_refresh: forceRefresh,
        })
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
          style={{ background: 'linear-gradient(135deg,#2563eb,#4f46e5)' }}>
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
        <div className="h-1.5" style={{ background: 'linear-gradient(90deg,#3b82f6,#06b6d4,#10b981,#6366f1,#8b5cf6)' }} />

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
                      background: 'linear-gradient(135deg,#2563eb,#4f46e5)',
                      boxShadow: inputValue.trim() ? '0 6px 24px rgba(37,99,235,0.45)' : 'none',
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
                <Toggle checked={forceRefresh} onChange={setForceRefresh} label="Renforcer l'enrichissement" desc="Force le rechargement des données et l'enrichissement complet" />
                <Toggle checked={runAgent4}    onChange={setRunAgent4}    label="Rapport Agent 4"  desc="Génération du rapport qualité final" />
              </div>
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
                  background: 'linear-gradient(90deg,#2563eb,#4f46e5)',
                  boxShadow: '0 0 10px rgba(37,99,235,0.4)',
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
