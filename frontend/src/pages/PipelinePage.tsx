import React, { useState, useCallback, useMemo, useEffect, useRef } from 'react'
import { useToast } from '../contexts/ToastContext'
import { useOrchestrator } from '../hooks'
import { ManualTestsTable } from '../components/tests/ManualTestsTable'
import { Alert } from '../components/ui/Alert'
import {
  Play, Square, GitBranch, CheckCircle2, XCircle,
  Clock, Cpu, AlertTriangle, AlertCircle, ChevronRight, Bot,
  FileText, TestTube, BarChart3, FileBarChart2,
  Sparkles, Hash, Maximize2,
  ChevronDown, ChevronUp, Edit2, Upload, Printer
} from 'lucide-react'

// ── Constants ──────────────────────────────────────────────────────────────────

const NAV       = '#0B1E3E'
const NAV_LIGHT = '#1A3A6B'
const ROSE      = '#DB2777'
const ORANGE    = '#EA580C'
const VIOLET    = '#1D4ED8'

const MAIN_GRADIENT = `linear-gradient(90deg, ${NAV}, ${NAV_LIGHT}, ${VIOLET}, ${ROSE}, ${ORANGE})`
const CARD_GRADIENT = `linear-gradient(135deg, ${NAV}, ${NAV_LIGHT}, ${VIOLET})`

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
  'Agent 1': { label: 'Agent 1 — Analyse',              desc: 'Analyse sémantique de la user story',     icon: FileText,      gradient: `linear-gradient(135deg, ${NAV}, ${VIOLET})`, accent: VIOLET },
  'Agent 2': { label: 'Agent 2 — Génération des tests', desc: 'Création des scénarios de tests manuels', icon: TestTube,      gradient: `linear-gradient(135deg, ${VIOLET}, ${ROSE})`, accent: ROSE },
  'Agent 3': { label: 'Agent 3 — Validation',           desc: 'Couverture, ambiguïtés & cas limites',    icon: CheckCircle2,  gradient: `linear-gradient(135deg, ${ORANGE}, ${ROSE})`, accent: ORANGE },
  'Agent 4': { label: 'Agent 4 — Classification',       desc: 'Classification auto/manuel',              icon: BarChart3,     gradient: CARD_GRADIENT, accent: '#7c3aed' },
  'Agent 5': { label: 'Agent 5 — Rapport',              desc: 'Rapport qualité & recommandations',       icon: FileBarChart2, gradient: CARD_GRADIENT, accent: NAV },
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
  <label className="flex items-center gap-3 cursor-pointer group py-1.5">
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className="relative w-11 h-6 rounded-full flex-shrink-0 transition-all duration-200 focus:outline-none"
      style={checked
        ? { background: CARD_GRADIENT, boxShadow: `0 0 0 3px rgba(10,22,40,0.12)` }
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

const SectionTitle: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <h3 className="text-xs font-bold uppercase tracking-widest mb-4 flex items-center gap-2" style={{ color: NAV }}>
    <span className="w-1 h-4 rounded-full inline-block" style={{ background: ROSE }} />
    {children}
  </h3>
)

// ── Agent 1 Result ────────────────────────────────────────────────────────────

const Agent1Result: React.FC<{ output: any }> = ({ output }) => {
  if (!output) return null
  const { story_id, story_title, story_type, actors, ...rest } = output

  const tableRows   = Object.entries(rest).filter(([, v]) => typeof v !== 'object' || v === null)
  const listEntries = Object.entries(rest).filter(([, v]) => Array.isArray(v))
  const objEntries  = Object.entries(rest).filter(([, v]) => !Array.isArray(v) && typeof v === 'object' && v !== null)

  return (
    <div className="space-y-8 w-full">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {story_id && (
          <div className="rounded-2xl p-5 flex flex-col gap-1.5"
            style={{ background: CARD_GRADIENT, boxShadow: '0 4px 20px rgba(10,22,40,0.25)' }}>
            <span className="text-[10px] font-bold uppercase tracking-widest text-white/50">Story ID</span>
            <span className="text-2xl font-extrabold text-white font-mono">{story_id}</span>
          </div>
        )}
        {story_type && (
          <div className="rounded-2xl p-5 flex flex-col gap-1.5"
            style={{ background: CARD_GRADIENT, boxShadow: '0 4px 20px rgba(10,22,40,0.25)' }}>
            <span className="text-[10px] font-bold uppercase tracking-widest text-white/50">Story Type</span>
            <span className="text-xl font-bold text-white capitalize">{story_type}</span>
          </div>
        )}
        {actors && (
          <div className="rounded-2xl p-5 flex flex-col gap-2"
            style={{ background: CARD_GRADIENT, boxShadow: '0 4px 20px rgba(10,22,40,0.25)' }}>
            <span className="text-[10px] font-bold uppercase tracking-widest text-white/50">Acteurs</span>
            <div className="flex flex-wrap gap-1.5">
              {(Array.isArray(actors) ? actors : [actors]).map((a: string, i: number) => (
                <span key={i} className="px-2.5 py-0.5 rounded-full text-xs font-semibold text-white"
                  style={{ background: 'rgba(255,255,255,0.15)', border: '1px solid rgba(255,255,255,0.25)' }}>
                  {a}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {story_title && (
        <div className="rounded-2xl p-5 border" style={{ borderColor: 'rgba(10,22,40,0.12)', background: 'rgba(10,22,40,0.03)' }}>
          <span className="text-[10px] font-bold uppercase tracking-widest block mb-2" style={{ color: `${NAV}80` }}>
            Titre de la Story
          </span>
          <p className="text-base font-semibold" style={{ color: NAV }}>{story_title}</p>
        </div>
      )}

      {listEntries.map(([key, val]) => (
        <div key={key}>
          <SectionTitle>{key.replace(/_/g, ' ')}</SectionTitle>
          <div className="space-y-2">
            {(val as any[]).map((item: any, i: number) => (
              <div key={i} className="flex items-start gap-3 p-3 rounded-xl"
                style={{ background: 'rgba(10,22,40,0.03)', border: '1px solid rgba(10,22,40,0.07)' }}>
                <div className="w-6 h-6 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5"
                  style={{ background: CARD_GRADIENT }}>
                  <span className="text-[10px] font-bold text-white">{i + 1}</span>
                </div>
                <span className="text-sm leading-relaxed" style={{ color: NAV }}>
                  {typeof item === 'string' ? item : item?.description || JSON.stringify(item)}
                </span>
              </div>
            ))}
          </div>
        </div>
      ))}

      {tableRows.length > 0 && (
        <div className="rounded-2xl overflow-hidden border" style={{ borderColor: 'rgba(10,22,40,0.12)' }}>
          <table className="w-full text-sm">
            <tbody className="divide-y" style={{ borderColor: 'rgba(10,22,40,0.08)' }}>
              {tableRows.map(([k, v]) => (
                <tr key={k}>
                  <td className="px-4 py-3 font-semibold text-xs uppercase tracking-wider w-1/3"
                    style={{ background: 'rgba(10,22,40,0.04)', color: `${NAV}80` }}>
                    {k.replace(/_/g, ' ')}
                  </td>
                  <td className="px-4 py-3 font-medium" style={{ color: NAV }}>{String(v)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {objEntries.map(([key, val]) => (
        <div key={key}>
          <SectionTitle>{key.replace(/_/g, ' ')}</SectionTitle>
          <pre className="text-xs p-4 rounded-xl overflow-x-auto font-mono"
            style={{ background: 'rgba(10,22,40,0.04)', border: '1px solid rgba(10,22,40,0.1)', color: NAV }}>
            {JSON.stringify(val, null, 2)}
          </pre>
        </div>
      ))}
    </div>
  )
}

// ── Edit Modal ────────────────────────────────────────────────────────────────

const TestEditModal: React.FC<{
  test: any
  onSave: (updated: any) => void
  onClose: () => void
}> = ({ test, onSave, onClose }) => {
  const [title, setTitle]         = useState(test.test_name || test.title || '')
  const [objective, setObjective] = useState(test.objective || test.objectif || '')
  const [aiPrompt, setAiPrompt]   = useState('')
  const [aiLoading, setAiLoading] = useState(false)
  const [aiReply, setAiReply]     = useState<string | null>(null)
  const [chatHistory, setChatHistory] = useState<{role: string; content: string}[]>([])

  const allSteps = test.steps || test.étapes?.flatMap((e: any) => e.steps || []) || []
  const [steps, setSteps] = useState<any[]>(allSteps)

  const handleStepChange = (idx: number, field: string, value: string) => {
    setSteps(prev => prev.map((s, i) => i === idx ? { ...s, [field]: value } : s))
  }

  const handleAiRefine = useCallback(async () => {
    if (!aiPrompt.trim()) return
    setAiLoading(true)
    setAiReply(null)
    const userMsg = aiPrompt.trim()
    try {
      const { apiClient } = await import('../api/client')
      const result = await apiClient.testEditing.refineChat({
        test: { ...test, steps },
        message: userMsg,
        chat_history: chatHistory,
      })
      const newHistory = [
        ...chatHistory,
        { role: 'user', content: userMsg },
        { role: 'assistant', content: result.assistant_message || result.message || 'Test mis à jour.' },
      ]
      setChatHistory(newHistory)
      if (result.test?.steps) setSteps(result.test.steps)
      setAiReply(result.assistant_message || result.message || 'Test mis à jour par l\'IA.')
      setAiPrompt('')
    } catch (err: any) {
      setAiReply(`Erreur : ${err?.message || 'Impossible de contacter le service IA.'}`)
    } finally {
      setAiLoading(false)
    }
  }, [aiPrompt, test, steps, chatHistory])

  const handleSave = () => {
    onSave({ ...test, test_name: title, objective, steps })
    onClose()
  }

  return (
    <div
      className="fixed inset-0 z-[9999] flex items-start justify-center p-4 md:p-8 overflow-y-auto"
      style={{ background: 'rgba(10,22,40,0.6)', backdropFilter: 'blur(4px)' }}
    >
      <div
        className="relative bg-white rounded-3xl w-full max-w-2xl shadow-2xl my-4 flex flex-col modal-print-area"
        style={{ maxHeight: '90vh' }}
      >
        {/* Header */}
        <div className="flex items-center gap-3 px-6 py-4 sticky top-0 bg-white z-10 border-b rounded-t-3xl"
          style={{ borderColor: 'rgba(10,22,40,0.08)' }}>
          <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
            style={{ background: CARD_GRADIENT }}>
            <Edit2 size={16} className="text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-[10px] font-bold uppercase tracking-widest mb-0.5" style={{ color: `${NAV}50` }}>
              Éditer le test
            </p>
            <input
              value={title}
              onChange={e => setTitle(e.target.value)}
              className="w-full font-bold text-sm focus:outline-none bg-transparent"
              style={{ color: NAV }}
            />
          </div>
          <button onClick={onClose}
            className="p-2 rounded-xl transition-colors hover:bg-slate-100"
            style={{ color: `${NAV}50` }}>
            <XCircle size={20} />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-5 overflow-y-auto flex-1">
          {/* AI refine */}
          <div className="rounded-2xl p-4 space-y-3"
            style={{
              background: `linear-gradient(135deg, rgba(11,30,62,0.03), rgba(29,78,216,0.06))`,
              border: `1.5px solid rgba(29,78,216,0.22)`,
            }}>
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-lg flex items-center justify-center"
                style={{ background: `linear-gradient(135deg, ${VIOLET}, #2563EB)` }}>
                <Sparkles size={12} className="text-white" />
              </div>
              <p className="text-xs font-bold uppercase tracking-widest" style={{ color: VIOLET }}>
                Affiner avec l'IA
              </p>
              <span className="w-2 h-2 rounded-full ml-auto"
                style={{ background: VIOLET, animation: 'pulse 1.8s ease-in-out infinite', opacity: .7 }} />
            </div>

            {/* Chat history */}
            {chatHistory.length > 0 && (
              <div className="space-y-2 max-h-40 overflow-y-auto rounded-xl p-2"
                style={{ background: 'rgba(29,78,216,0.03)', border: '1px solid rgba(29,78,216,0.1)' }}>
                {chatHistory.map((msg, i) => (
                  <div key={i} className={`flex gap-2 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className="max-w-[80%] px-3 py-1.5 rounded-xl text-xs leading-relaxed"
                      style={msg.role === 'user'
                        ? { background: VIOLET, color: 'white' }
                        : { background: 'rgba(11,30,62,0.06)', color: NAV }
                      }>
                      {msg.content}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* AI reply */}
            {aiReply && (
              <div className="rounded-xl px-3 py-2 text-xs leading-relaxed"
                style={{ background: `${VIOLET}10`, border: `1px solid ${VIOLET}25`, color: NAV }}>
                <span className="font-bold" style={{ color: VIOLET }}>IA : </span>{aiReply}
              </div>
            )}

            <textarea
              value={aiPrompt}
              onChange={e => setAiPrompt(e.target.value)}
              rows={2}
              placeholder="ex : Ajouter une étape pour vérifier le message d'erreur..."
              className="w-full text-sm rounded-xl px-3 py-2.5 focus:outline-none resize-none transition-all"
              style={{ color: NAV, background: 'rgba(29,78,216,0.04)', border: '1.5px solid rgba(29,78,216,0.18)' }}
              onKeyDown={e => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) handleAiRefine() }}
            />
            <div className="flex justify-end">
              <button
                type="button"
                onClick={handleAiRefine}
                disabled={aiLoading || !aiPrompt.trim()}
                className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold text-white transition-all hover:-translate-y-0.5 disabled:opacity-40 disabled:cursor-not-allowed"
                style={{ background: `linear-gradient(135deg, ${VIOLET}, #2563EB)`, boxShadow: `0 3px 12px rgba(29,78,216,0.35)` }}>
                {aiLoading
                  ? <><Cpu size={12} className="animate-spin" /> Affinage…</>
                  : <><Sparkles size={12} /> Affiner</>
                }
              </button>
            </div>
          </div>

          {/* Objectif */}
          <div className="space-y-2">
            <p className="text-[10px] font-bold uppercase tracking-widest" style={{ color: `${NAV}55` }}>Objectif</p>
            <textarea
              value={objective}
              onChange={e => setObjective(e.target.value)}
              rows={2}
              className="w-full text-sm rounded-xl px-3 py-2.5 focus:outline-none resize-none transition-all"
              style={{ color: NAV, border: `1.5px solid rgba(10,22,40,0.12)`, background: `rgba(10,22,40,0.02)` }}
            />
          </div>

          {/* Steps */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-[10px] font-bold uppercase tracking-widest" style={{ color: `${NAV}55` }}>Étapes</p>
              <span className="px-2 py-0.5 rounded-lg text-xs font-bold"
                style={{ background: 'rgba(10,22,40,0.07)', color: NAV }}>
                {steps.length}
              </span>
            </div>

            {steps.map((step, si) => (
              <div key={si} className="flex items-start gap-3">
                <div className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 mt-1"
                  style={{ background: CARD_GRADIENT }}>
                  <span className="text-[10px] font-extrabold text-white">{si + 1}</span>
                </div>
                <div className="flex-1 space-y-1.5">
                  <input
                    value={step.titre || step.action || ''}
                    onChange={e => handleStepChange(si, 'titre', e.target.value)}
                    className="w-full text-sm rounded-xl px-3 py-2 focus:outline-none transition-all"
                    placeholder="Action..."
                    style={{ color: NAV, border: `1.5px solid rgba(10,22,40,0.1)`, background: `rgba(10,22,40,0.02)` }}
                  />
                  <input
                    value={step.expected_result || ''}
                    onChange={e => handleStepChange(si, 'expected_result', e.target.value)}
                    className="w-full text-xs rounded-xl px-3 py-2 focus:outline-none transition-all"
                    placeholder="Résultat attendu..."
                    style={{ color: `${NAV}90`, border: `1.5px dashed rgba(10,22,40,0.1)`, background: `rgba(10,22,40,0.015)` }}
                  />
                </div>
              </div>
            ))}

            <button
              type="button"
              onClick={() => setSteps(prev => [...prev, { titre: '', expected_result: '' }])}
              className="w-full py-2 rounded-xl text-xs font-semibold transition-all hover:bg-slate-50"
              style={{ color: `${NAV}50`, border: `1.5px dashed rgba(10,22,40,0.12)` }}>
              + Ajouter une étape
            </button>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t flex items-center gap-3 justify-end rounded-b-3xl bg-white"
          style={{ borderColor: 'rgba(10,22,40,0.08)' }}>
          <button type="button" onClick={onClose}
            className="px-5 py-2.5 rounded-xl text-sm font-bold transition-colors hover:bg-slate-50"
            style={{ color: `${NAV}60`, border: `1.5px solid rgba(10,22,40,0.12)` }}>
            Annuler
          </button>
          <button type="button" onClick={handleSave}
            className="flex items-center gap-2 px-6 py-2.5 rounded-xl text-sm font-bold text-white transition-all hover:-translate-y-0.5"
            style={{ background: CARD_GRADIENT, boxShadow: `0 4px 16px rgba(10,22,40,0.3)` }}>
            <span>💾</span> Sauvegarder
          </button>
        </div>
      </div>
    </div>
  )
}

// ── TestAccordion ─────────────────────────────────────────────────────────────

const TestAccordion: React.FC<{
  test: any
  idx: number
  storyId?: string
  onEdit?: (test: any) => void
  onXray?: (test: any) => void
}> = ({ test, idx, onEdit, onXray }) => {
  const [open, setOpen] = useState(false)

  // FIX #8 — memoised so it's not recomputed on every render
  const allSteps = useMemo(
    () => test.steps || test.étapes?.flatMap((e: any) => e.steps || []) || [],
    [test]
  )
  const testTitle = test.test_name || test.title || `Test ${idx + 1}`

  return (
    <div className="rounded-2xl overflow-hidden border transition-all duration-200"
      style={{
        borderColor: open ? `${NAV}30` : 'rgba(10,22,40,0.1)',
        boxShadow: open ? `0 4px 20px rgba(10,22,40,0.08)` : 'none',
      }}>

      {/* Accordion header */}
      <div
        className="flex items-center gap-4 p-4 cursor-pointer select-none transition-colors"
        style={{ background: open ? CARD_GRADIENT : 'white' }}
        onClick={() => setOpen(v => !v)}
      >
        <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
          style={{ background: open ? 'rgba(255,255,255,0.15)' : CARD_GRADIENT }}>
          <span className="text-sm font-extrabold text-white">{idx + 1}</span>
        </div>

        <div className="flex-1 min-w-0">
          <p className="font-bold text-sm truncate" style={{ color: open ? 'white' : NAV }}>{testTitle}</p>
          {!open && (
            <p className="text-xs mt-0.5" style={{ color: `${NAV}60` }}>
              {allSteps.length} étape{allSteps.length > 1 ? 's' : ''} · Cliquer pour voir les détails
            </p>
          )}
        </div>

        <div className="flex items-center gap-2 flex-shrink-0" onClick={e => e.stopPropagation()}>
          <button
            type="button"
            onClick={() => onEdit?.(test)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all hover:-translate-y-0.5"
            style={open
              ? { background: 'rgba(255,255,255,0.15)', color: 'white', border: '1px solid rgba(255,255,255,0.3)' }
              : { background: 'rgba(10,22,40,0.06)', color: NAV, border: `1px solid rgba(10,22,40,0.12)` }
            }>
            <Edit2 size={12} /> Éditer
          </button>
          <button
            type="button"
            onClick={() => onXray?.(test)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all hover:-translate-y-0.5"
            style={{ background: `linear-gradient(135deg,${ROSE},${ORANGE})`, color: 'white', boxShadow: `0 2px 8px ${ROSE}40` }}>
            <Upload size={12} /> Xray
          </button>
        </div>

        <div style={{ color: open ? 'rgba(255,255,255,0.6)' : `${NAV}40` }}>
          {open ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
      </div>

      {/* Accordion body */}
      {open && (
        <div className="p-6 space-y-6 bg-white">
          {allSteps.length > 0 && (
            <div>
              <p className="text-xs font-bold uppercase tracking-widest mb-3" style={{ color: `${NAV}60` }}>Description</p>
              <div className="space-y-2 pl-2">
                {allSteps.map((step: any, si: number) => (
                  <div key={si} className="flex items-center gap-2 text-sm" style={{ color: NAV }}>
                    <span className="text-xs font-bold px-2 py-0.5 rounded-lg"
                      style={{ background: 'rgba(10,22,40,0.08)', color: NAV }}>
                      {step.actor || 'Collaborateur'}
                    </span>
                    <span>{step.titre || step.action}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="rounded-2xl overflow-hidden border" style={{ borderColor: 'rgba(10,22,40,0.1)' }}>
            <table className="w-full text-sm text-left">
              <thead style={{ background: CARD_GRADIENT }}>
                <tr>
                  <th className="w-12 px-4 py-3 font-bold text-white text-center text-xs">#</th>
                  <th className="px-4 py-3 font-bold text-white text-xs">Action</th>
                  <th className="px-4 py-3 font-bold text-white text-xs">Données</th>
                  <th className="px-4 py-3 font-bold text-white text-xs">Résultat Attendu</th>
                </tr>
              </thead>
              <tbody>
                {allSteps.map((step: any, si: number) => (
                  <tr key={si} className="border-t align-top hover:bg-slate-50/60 transition-colors"
                    style={{ borderColor: 'rgba(10,22,40,0.06)' }}>
                    <td className="px-4 py-4 text-center font-extrabold text-xs"
                      style={{ background: 'rgba(10,22,40,0.03)', color: NAV }}>
                      {si + 1}
                    </td>
                    <td className="px-4 py-4">
                      <p className="font-semibold text-xs mb-1 px-2 py-0.5 rounded-lg inline-block"
                        style={{ background: 'rgba(10,22,40,0.07)', color: NAV }}>
                        {step.actor || 'Collaborateur'}
                      </p>
                      <p className="text-sm leading-relaxed mt-1" style={{ color: NAV }}>
                        {step.titre || step.action}
                      </p>
                    </td>
                    <td className="px-4 py-4 text-xs font-mono leading-relaxed whitespace-pre-wrap"
                      style={{ background: 'rgba(10,22,40,0.015)', color: `${NAV}90` }}>
                      {step.data || '—'}
                    </td>
                    <td className="px-4 py-4">
                      {step.expected_result ? (
                        <ul className="space-y-1.5 list-disc list-inside ml-1">
                          {step.expected_result.split('\n').map((line: string, i: number) => {
                            const cl = line.replace(/^-\s*/, '').trim()
                            return cl ? <li key={i} className="text-xs leading-relaxed" style={{ color: NAV }}>{cl}</li> : null
                          })}
                        </ul>
                      ) : <span className="text-xs" style={{ color: `${NAV}40` }}>—</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Agent 2 Result ────────────────────────────────────────────────────────────

const Agent2Result: React.FC<{ output: any; storyId?: string; onTestsChange?: (tests: any[]) => void }> = ({ output, storyId, onTestsChange }) => {
  const [tests, setTests] = useState<any[]>(
    Array.isArray(output) ? output : output?.tests || output?.agent2_tests || []
  )

  const handleChange = (next: any[]) => {
    setTests(next)
    onTestsChange?.(next)
  }

  if (!tests.length) return (
    <div className="py-12 text-center">
      <TestTube size={32} className="mx-auto mb-3 opacity-30" style={{ color: NAV }} />
      <p className="text-sm font-medium" style={{ color: `${NAV}60` }}>Aucun test généré</p>
    </div>
  )

  return (
    <ManualTestsTable
      tests={tests}
      storyId={storyId}
      onTestsChange={handleChange}
      expandable
      defaultExpandedIndex={0}
      showProjectPicker
    />
  )
}

// ── Agent 3 Result ────────────────────────────────────────────────────────────

const Agent3Result: React.FC<{ output: any }> = ({ output }) => {
  if (!output) return null
  const report          = output?.report || output
  const coverage        = report?.coverage_rate ?? report?.coverage_percentage
  const validationStatus = report?.validation_status
  const ambiguities     = report?.ambiguities || []
  const uncoveredPoints = report?.uncovered_testable_points || []
  const duplicates      = report?.duplicate_tests || report?.duplicates || []
  const covPct          = Math.round((coverage || 0) * 100)

  const reasonList: string[] = []
  if (validationStatus === 'PARTIALLY_VALID' || validationStatus === 'INVALID') {
    if (uncoveredPoints.length) reasonList.push(`${uncoveredPoints.length} point${uncoveredPoints.length > 1 ? 's' : ''} non couverts`)
    if (duplicates.length)      reasonList.push(`${duplicates.length} doublon${duplicates.length > 1 ? 's' : ''} détecté${duplicates.length > 1 ? 's' : ''}`)
    if (ambiguities.length)     reasonList.push(`${ambiguities.length} ambiguïté${ambiguities.length > 1 ? 's' : ''} détectée${ambiguities.length > 1 ? 's' : ''}`)
    if (!reasonList.length)     reasonList.push(validationStatus === 'PARTIALLY_VALID'
      ? 'Validation partielle : pas d\'issues techniques clairement identifiées.'
      : 'Validation invalide : vérifier les tests et les recommandations.')
  }

  return (
    <div className="space-y-6 w-full">
      <div className="grid grid-cols-3 gap-4">
        <div className="rounded-2xl p-5 text-center"
          style={{ background: `linear-gradient(135deg,${ORANGE},${ROSE})`, boxShadow: `0 4px 20px ${ORANGE}35` }}>
          <p className="text-3xl font-extrabold text-white">{covPct}%</p>
          <p className="text-xs font-bold text-white/70 uppercase tracking-widest mt-1">Couverture</p>
        </div>
        <div className="rounded-2xl p-5 text-center border"
          style={{ borderColor: `${ROSE}25`, background: `${ROSE}08` }}>
          <p className="text-3xl font-extrabold" style={{ color: ROSE }}>{ambiguities.length}</p>
          <p className="text-xs font-bold uppercase tracking-widest mt-1" style={{ color: `${ROSE}80` }}>Ambiguïtés</p>
        </div>
        <div className="rounded-2xl p-5 text-center border"
          style={{ borderColor: `${ORANGE}25`, background: `${ORANGE}08` }}>
          <p className="text-3xl font-extrabold" style={{ color: ORANGE }}>{duplicates.length}</p>
          <p className="text-xs font-bold uppercase tracking-widest mt-1" style={{ color: `${ORANGE}80` }}>Doublons</p>
        </div>
      </div>

      {validationStatus && (
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <span className="text-xs font-bold uppercase tracking-widest" style={{ color: `${NAV}50` }}>Statut Validation</span>
            <span className="px-3 py-1 rounded-full text-xs font-bold"
              style={{
                background: validationStatus === 'valid' ? `${ORANGE}18` : `${ROSE}18`,
                color: validationStatus === 'valid' ? ORANGE : ROSE,
                border: `1px solid ${validationStatus === 'valid' ? ORANGE : ROSE}40`,
              }}>
              {validationStatus}
            </span>
          </div>
          {reasonList.length > 0 && (
            <div className="rounded-3xl border border-orange-200 bg-orange-50 p-4">
              <p className="text-sm font-semibold text-orange-900">Raison du statut</p>
              <ul className="mt-2 space-y-2 text-sm text-orange-800">
                {reasonList.map((reason, i) => (
                  <li key={i} className="leading-relaxed">• {reason}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {ambiguities.length > 0 && (
        <div>
          <SectionTitle>Ambiguïtés détectées</SectionTitle>
          <div className="space-y-2">
            {ambiguities.map((a: any, i: number) => (
              <div key={i} className="flex items-start gap-3 p-3 rounded-xl"
                style={{ background: `${ORANGE}08`, border: `1px solid ${ORANGE}20` }}>
                <AlertCircle size={14} className="flex-shrink-0 mt-0.5" style={{ color: ORANGE }} />
                <span className="text-sm leading-relaxed" style={{ color: NAV }}>
                  {typeof a === 'string' ? a : a.description || JSON.stringify(a)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {duplicates.length > 0 && (
        <div>
          <SectionTitle>Tests en doublon</SectionTitle>
          <div className="space-y-2">
            {duplicates.map((d: any, i: number) => (
              <div key={i} className="flex items-start gap-3 p-3 rounded-xl"
                style={{ background: `${ROSE}08`, border: `1px solid ${ROSE}20` }}>
                <AlertTriangle size={14} className="flex-shrink-0 mt-0.5" style={{ color: ROSE }} />
                <span className="text-sm leading-relaxed" style={{ color: NAV }}>
                  {typeof d === 'string' ? d : d.description || JSON.stringify(d)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {uncoveredPoints.length > 0 && (
        <div>
          <SectionTitle>Points non couverts</SectionTitle>
          <div className="space-y-2">
            {uncoveredPoints.map((p: string, i: number) => (
              <div key={i} className="flex items-start gap-3 p-3 rounded-xl"
                style={{ background: `${ROSE}06`, border: `1px solid ${ROSE}15` }}>
                <XCircle size={14} className="flex-shrink-0 mt-0.5" style={{ color: ROSE }} />
                <span className="text-sm leading-relaxed" style={{ color: NAV }}>{p}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Agent 5 Result ────────────────────────────────────────────────────────────

const ReportSection: React.FC<{ icon: string; title: string; children: React.ReactNode }> = ({ icon, title, children }) => (
  <div className="space-y-4">
    <div className="flex items-center gap-3 pb-3 border-b-2" style={{ borderColor: `${NAV}12` }}>
      <span className="text-lg">{icon}</span>
      <h3 className="text-lg font-extrabold" style={{ color: NAV }}>{title}</h3>
    </div>
    {children}
  </div>
)

const InfoTable: React.FC<{ rows: [string, string][] }> = ({ rows }) => (
  <div className="rounded-xl overflow-hidden border" style={{ borderColor: 'rgba(10,22,40,0.1)' }}>
    <table className="w-full text-sm">
      <tbody>
        {rows.map(([label, value], i) => (
          <tr key={i} className="border-t first:border-0" style={{ borderColor: 'rgba(10,22,40,0.07)' }}>
            <td className="px-4 py-3 font-semibold text-xs uppercase tracking-wider w-40"
              style={{ background: 'rgba(10,22,40,0.03)', color: `${NAV}70` }}>
              {label}
            </td>
            <td className="px-4 py-3 font-medium text-sm" style={{ color: NAV }}>{value}</td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
)

const BulletList: React.FC<{ items: string[]; color?: string }> = ({ items, color = NAV }) => (
  <ul className="space-y-2">
    {items.map((item, i) => (
      <li key={i} className="flex items-start gap-2.5">
        <span className="w-1.5 h-1.5 rounded-full flex-shrink-0 mt-2" style={{ background: color }} />
        <span className="text-sm leading-relaxed" style={{ color: NAV }}>{item}</span>
      </li>
    ))}
  </ul>
)

const Agent5Result: React.FC<{ output: any; storyId?: string }> = ({ output, storyId }) => {
  if (!output) return null
  const [downloading, setDownloading] = useState(false)

  // The output IS the Agent5Report object (unwrapped)
  const reportObj     = output.report || output  // handle both wrapped and direct
  const reportTitle   = reportObj.report_title   || output.report_title
  const version       = reportObj.report_version || output.report_version
  const timestamp     = reportObj.generated_timestamp || output.generated_timestamp
  const reportStoryId = reportObj.story_id || output.story_id || storyId

  const exec         = reportObj.executive_summary || output.executive_summary || {}
  const globalStatus = exec.overall_status || exec.global_status
  const findings     = exec.key_findings    || exec.main_findings    || []
  const nextSteps    = exec.next_steps      || exec.prochaines_etapes || []

  const storySynth      = reportObj.story_summary    || output.story_summary    || {}
  const testSuite       = reportObj.test_suite       || output.test_suite       || {}
  const coverage        = reportObj.coverage_metrics || output.coverage_metrics || {}
  const validation      = reportObj.quality_assurance|| output.quality_assurance|| {}
  const recommendations = reportObj.recommendations  || output.recommendations  || []
  const pipeline        = reportObj.processing_notes || output.processing_notes || []

  const normalizedStatus = String(globalStatus || '').toUpperCase()
  const statusColor = (normalizedStatus === 'APPROVED') ? ORANGE : (normalizedStatus === 'REQUIRES_REVIEW' ? ROSE : ROSE)

  const handleDownloadPdf = () => {
    // Helper to generate the exact styled PDF report matching user's screenshots
    const printWindow = window.open('', '_blank')
    if (!printWindow) return

    const findingsHtml = findings.map((f: string) => `<li>${f}</li>`).join('')
    const nextStepsHtml = nextSteps.map((s: string) => `<li>${s}</li>`).join('')
    
    const testSuiteHtml = (testSuite.tests_summary || []).map((t: any) => `
      <tr>
        <td><span style="font-weight:700;color:#EA580C;">${t.scenario_type || t.type || 'NOM'}</span></td>
        <td>${t.test_name || t.name || '—'}</td>
        <td>${t.priority || '—'}</td>
        <td>${t.step_count !== undefined ? t.step_count : (t.steps_count !== undefined ? t.steps_count : 0)} étapes</td>
      </tr>
    `).join('')

    const recsHtml = recommendations.map((rec: any) => {
      const priority = rec.priority || 'LOW'
      const action = rec.action || rec.text || 'Recommandation'
      const rationale = rec.rationale || rec.description || ''
      return `
        <div class="recommendation-card">
          <div class="rec-header">[${priority.toUpperCase()}] ${action}</div>
          <div class="rec-body">${rationale}</div>
        </div>
      `
    }).join('')

    const pipelineHtml = pipeline.map((p: string) => `<li>${p}</li>`).join('')

    const html = `
      <!DOCTYPE html>
      <html>
      <head>
        <title>Agent Test — Rapport QA · ${reportStoryId}</title>
        <style>
          @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&display=swap');
          body {
            font-family: 'Outfit', 'Segoe UI', system-ui, -apple-system, sans-serif;
            color: #0B1E3E;
            margin: 40px;
            line-height: 1.6;
          }
          .header {
            font-size: 11px;
            color: #64748b;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
          }
          .title {
            font-size: 26px;
            font-weight: 800;
            color: #1D4ED8;
            border-bottom: 2px solid #1D4ED8;
            padding-bottom: 10px;
            margin-bottom: 30px;
          }
          h2 {
            font-size: 16px;
            font-weight: 800;
            color: #0B1E3E;
            margin-top: 30px;
            margin-bottom: 15px;
            border-bottom: 1px solid #e2e8f0;
            padding-bottom: 5px;
          }
          h3 {
            font-size: 13px;
            font-weight: 700;
            margin-top: 20px;
            margin-bottom: 10px;
            color: #1A3A6B;
          }
          .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 9999px;
            font-size: 12px;
            font-weight: 700;
            background: rgba(234,88,12,0.1);
            color: #EA580C;
            border: 1px solid rgba(234,88,12,0.3);
            margin-left: 10px;
          }
          ul {
            padding-left: 20px;
            margin-bottom: 20px;
          }
          li {
            margin-bottom: 6px;
            font-size: 13px;
          }
          table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 25px;
            font-size: 13px;
            border: 1px solid #e2e8f0;
          }
          th, td {
            padding: 10px 12px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
          }
          th {
            background-color: #0B1E3E;
            color: white;
            font-weight: 700;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
          }
          td.prop-name {
            font-weight: 700;
            background-color: #f8fafc;
            width: 30%;
            color: #64748b;
          }
          .recommendation-card {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 12px;
          }
          .rec-header {
            font-weight: 800;
            font-size: 11px;
            color: #EA580C;
            margin-bottom: 4px;
          }
          .rec-body {
            font-size: 13px;
          }
          .footer {
            margin-top: 50px;
            border-top: 1px solid #e2e8f0;
            padding-top: 15px;
            font-size: 11px;
            color: #64748b;
            display: flex;
            justify-content: space-between;
          }
          @media print {
            body {
              margin: 20px;
            }
          }
        </style>
      </head>
      <body>
        <div class="header">
          <span>Agent Test — Rapport QA · ${reportStoryId}</span>
        </div>
        
        <div class="title">${reportTitle || `Rapport QA Complet — ${reportStoryId}`}</div>
        
        <h2>■ Résumé Exécutif</h2>
        <p><strong>Statut Global :</strong> <span class="status-badge">${globalStatus || 'APPROVED'}</span></p>
        
        <h3>Findings Principaux</h3>
        <ul>${findingsHtml || '<li>Aucun finding disponible</li>'}</ul>
        
        <h3>Prochaines Étapes</h3>
        <ul>${nextStepsHtml || '<li>Aucune étape recommandée</li>'}</ul>
        
        <h2>■ Synthèse User Story</h2>
        <table>
          <tr>
            <td class="prop-name">ID</td>
            <td><strong>${reportStoryId || '—'}</strong></td>
          </tr>
          <tr>
            <td class="prop-name">Titre</td>
            <td>${storySynth.story_title || storySynth.title || '—'}</td>
          </tr>
          <tr>
            <td class="prop-name">Type</td>
            <td>${storySynth.story_type || storySynth.type || '—'}</td>
          </tr>
        </table>
        <p><strong>Acteurs :</strong> ${storySynth.actors && storySynth.actors.length > 0 ? storySynth.actors.join(', ') : 'N/A'}</p>
        <p><strong>Règles Métier :</strong> ${storySynth.business_rules && storySynth.business_rules.length > 0 ? storySynth.business_rules.join('. ') : 'Aucune'}</p>
        <p><strong>Périmètre Technique :</strong> ${storySynth.technical_scope && storySynth.technical_scope.length > 0 ? storySynth.technical_scope.join(', ') : 'N/A'}</p>
        
        <h2>■ Suite de Tests Générée</h2>
        <ul>
          <li><strong>Total :</strong> ${testSuite.total_tests ?? 0} cas de test</li>
          <li><strong>NOM (Nominal) :</strong> ${testSuite.nom_count ?? 0}</li>
          <li><strong>ALT (Alternatif) :</strong> ${testSuite.alt_count ?? 0}</li>
          <li><strong>EXC (Exception) :</strong> ${testSuite.exc_count ?? 0}</li>
          <li><strong>Priorités :</strong> Haute: ${testSuite.high_priority_count ?? 0}</li>
        </ul>
        
        <h3>Tests (résumé)</h3>
        <table>
          <thead>
            <tr>
              <th>Type</th>
              <th>Nom</th>
              <th>Priorité</th>
              <th>Étapes</th>
            </tr>
          </thead>
          <tbody>
            ${testSuiteHtml || '<tr><td colspan="4">Aucun test généré</td></tr>'}
          </tbody>
        </table>
        
        <h2>■ Métriques de Couverture</h2>
        <ul>
          <li><strong>Taux :</strong> ${coverage.coverage_rate !== undefined ? coverage.coverage_rate + '%' : '0%'}</li>
          <li><strong>Statut :</strong> ${coverage.coverage_status || 'EXCELLENT'}</li>
          <li><strong>Points Non Couverts :</strong> ${coverage.uncovered_points && coverage.uncovered_points.length > 0 ? coverage.uncovered_points.join(', ') : 'Aucun'}</li>
        </ul>
        
        <h2>■ Validation & Assurance Qualité</h2>
        <p><strong>Statut Validation :</strong> <span class="status-badge">${validation.validation_status || 'VALID'}</span></p>
        <ul>
          <li><strong>Doublons détectés :</strong> ${validation.duplicate_pairs ?? 0}</li>
          <li><strong>Ambiguïtés détectées :</strong> ${validation.ambiguity_count ?? 0}</li>
        </ul>
        
        <h3>Issues Détectées</h3>
        <p>${(validation.issues || []).length === 0 ? 'Aucune issue détectée ■' : (validation.issues || []).map((i: any) => `• [${i.severity}] ${i.description}`).join('<br>')}</p>
        
        <h3>Qualité LLM</h3>
        <ul>
          <li><strong>Score :</strong> ${validation.llm_quality_score !== undefined ? validation.llm_quality_score : 'N/A'}/10</li>
          <li><strong>Feedback :</strong> ${validation.llm_quality_summary || 'Pas de feedback'}</li>
        </ul>
        
        <h2>■ Recommandations</h2>
        ${recsHtml || '<p>Aucune recommandation</p>'}
        
        <h2>■■ Notes de Traitement (Pipeline)</h2>
        <ul>${pipelineHtml || '<li>Aucune note de traitement</li>'}</ul>
        
        <div class="footer">
          <span>Rapport généré le ${new Date(timestamp || new Date()).toLocaleString('fr-FR')} — Version ${version || '1.0'}</span>
        </div>
        
        <script>
          window.onload = function() {
            window.print();
          }
        </script>
      </body>
      </html>
    `
    printWindow.document.write(html)
    printWindow.document.close()
  }

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
    <div className="w-full space-y-8 modal-print-area">
      {/* Report header card */}
      <div className="rounded-2xl p-6" style={{ background: CARD_GRADIENT, boxShadow: '0 8px 32px rgba(10,22,40,0.3)' }}>
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <p className="text-xs font-bold uppercase tracking-widest text-white/50 mb-2">Rapport QA Final</p>
            <h2 className="text-2xl font-extrabold text-white leading-tight mb-3">
              {reportTitle || `Rapport QA — ${reportStoryId}`}
            </h2>
            <div className="flex flex-wrap gap-3">
              {reportStoryId && (
                <span className="px-3 py-1 rounded-full text-xs font-bold text-white"
                  style={{ background: 'rgba(255,255,255,0.15)', border: '1px solid rgba(255,255,255,0.25)' }}>
                  {reportStoryId}
                </span>
              )}
              {version && (
                <span className="px-3 py-1 rounded-full text-xs font-bold text-white/70"
                  style={{ background: 'rgba(255,255,255,0.08)' }}>
                  v{version}
                </span>
              )}
              {timestamp && (
                <span className="px-3 py-1 rounded-full text-xs text-white/50"
                  style={{ background: 'rgba(255,255,255,0.06)' }}>
                  {new Date(timestamp).toLocaleString('fr-FR')}
                </span>
              )}
            </div>
          </div>
          {globalStatus && (
            <div className="flex-shrink-0 text-center">
              <div className="w-24 h-24 rounded-2xl flex flex-col items-center justify-center"
                style={{ background: `${statusColor}25`, border: `2px solid ${statusColor}60` }}>
                <CheckCircle2 size={28} style={{ color: statusColor }} />
                <p className="text-xs font-extrabold mt-1" style={{ color: statusColor }}>{globalStatus}</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {(findings.length > 0 || nextSteps.length > 0) && (
        <ReportSection icon="■" title="Résumé Exécutif">
          {globalStatus && (
            <div className="flex items-center gap-2 mb-4">
              <span className="text-sm font-semibold" style={{ color: `${NAV}70` }}>Statut Global :</span>
              <span className="font-extrabold" style={{ color: statusColor }}>{globalStatus}</span>
            </div>
          )}
          {findings.length > 0 && (
            <div className="mb-4">
              <p className="text-sm font-bold mb-2" style={{ color: NAV }}>Findings Principaux</p>
              <BulletList items={findings} color={ORANGE} />
            </div>
          )}
          {nextSteps.length > 0 && (
            <div>
              <p className="text-sm font-bold mb-2" style={{ color: NAV }}>Prochaines Étapes</p>
              <BulletList items={nextSteps} color={NAV_LIGHT} />
            </div>
          )}
        </ReportSection>
      )}

      {Object.keys(storySynth).length > 0 && (
        <ReportSection icon="■" title="Synthèse User Story">
          <InfoTable rows={
            Object.entries(storySynth)
              .filter(([, v]) => typeof v === 'string' || typeof v === 'number')
              .map(([k, v]) => [k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()), String(v)])
          } />
        </ReportSection>
      )}

      {Object.keys(testSuite).length > 0 && (
        <ReportSection icon="■" title="Suite de Tests Générée">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4">
            {[
              { label: 'Total',             value: testSuite.total_tests ?? testSuite.total },
              { label: 'NOM (Nominal)',     value: testSuite.nom_count   ?? testSuite.nom ?? testSuite.nominal },
              { label: 'ALT (Alternatif)', value: testSuite.alt_count   ?? testSuite.alt ?? testSuite.alternative },
              { label: 'EXC (Exception)',  value: testSuite.exc_count   ?? testSuite.exc ?? testSuite.exception },
              { label: 'Priorité Haute',   value: testSuite.high_priority_count ?? testSuite.high_priority ?? testSuite.priorite_haute },
            ].filter(r => r.value !== undefined).map((item, i) => (
              <div key={i} className="rounded-xl p-3 text-center"
                style={{ background: 'rgba(10,22,40,0.04)', border: '1px solid rgba(10,22,40,0.1)' }}>
                <p className="text-xl font-extrabold" style={{ color: NAV }}>{item.value ?? '—'}</p>
                <p className="text-[10px] font-bold uppercase tracking-wider mt-0.5" style={{ color: `${NAV}55` }}>{item.label}</p>
              </div>
            ))}
          </div>

          {(testSuite.tests_summary || testSuite.tests || []).length > 0 && (
            <div className="rounded-xl overflow-hidden border" style={{ borderColor: 'rgba(10,22,40,0.1)' }}>
              <table className="w-full text-sm">
                <thead style={{ background: CARD_GRADIENT }}>
                  <tr>
                    <th className="px-4 py-3 text-xs font-bold text-white text-left">Type</th>
                    <th className="px-4 py-3 text-xs font-bold text-white text-left">Nom</th>
                    <th className="px-4 py-3 text-xs font-bold text-white text-left">Priorité</th>
                    <th className="px-4 py-3 text-xs font-bold text-white text-left">Étapes</th>
                  </tr>
                </thead>
                <tbody>
                  {(testSuite.tests_summary || testSuite.tests || []).map((t: any, i: number) => (
                    <tr key={i} className="border-t" style={{ borderColor: 'rgba(10,22,40,0.06)' }}>
                      <td className="px-4 py-3">
                        <span className="px-2 py-0.5 rounded-lg text-xs font-bold"
                          style={{ background: `${ORANGE}15`, color: ORANGE }}>
                          {t.type || t.classification || t.scenario_type || '—'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs font-medium" style={{ color: NAV }}>{t.name || t.nom || t.test_name || '—'}</td>
                      <td className="px-4 py-3 text-xs font-semibold" style={{ color: `${NAV}70` }}>{t.priority || t.priorite || '—'}</td>
                      <td className="px-4 py-3 text-xs" style={{ color: `${NAV}60` }}>
                        {t.step_count !== undefined ? `${t.step_count} étapes` : (t.steps_count !== undefined ? `${t.steps_count} étapes` : t.steps ? `${t.steps} étapes` : '—')}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </ReportSection>
      )}

      {Object.keys(coverage).length > 0 && (
        <ReportSection icon="■" title="Métriques de Couverture">
          <div className="space-y-4">
            {coverage.coverage_rate !== undefined && (
              <div className="flex items-center gap-4">
                <div className="flex-1 bg-gray-100 rounded-full h-3 overflow-hidden">
                  <div className="h-full rounded-full transition-all"
                    style={{ width: `${Math.min(coverage.coverage_rate, 100)}%`, background: `linear-gradient(90deg, ${VIOLET}, ${ORANGE})` }} />
                </div>
                <span className="text-lg font-extrabold flex-shrink-0" style={{ color: NAV }}>
                  {Math.round(coverage.coverage_rate)}%
                </span>
              </div>
            )}
            {[
              ['Statut Couverture',   coverage.coverage_status || coverage.statut],
              ['Points testables',   coverage.total_testable_points ?? coverage.total_points],
              ['Points couverts',    coverage.covered_points ?? coverage.points_couverts],
              ['Points non couverts', Array.isArray(coverage.uncovered_points)
                ? (coverage.uncovered_points.length === 0 ? 'Aucun' : `${coverage.uncovered_points.length} point(s)`)
                : coverage.uncovered_points_count ?? '—'],
            ].filter(([, v]) => v !== undefined && v !== '—').map(([label, value], i) => (
              <div key={i} className="flex items-center gap-4">
                <span className="text-sm font-semibold w-44 flex-shrink-0" style={{ color: `${NAV}70` }}>{label} :</span>
                <span className="text-sm font-bold" style={{ color: NAV }}>{String(value)}</span>
              </div>
            ))}
            {Array.isArray(coverage.uncovered_points) && coverage.uncovered_points.length > 0 && (
              <div>
                <p className="text-xs font-bold uppercase tracking-widest mb-2" style={{ color: `${NAV}60` }}>Points non couverts :</p>
                <BulletList items={coverage.uncovered_points} color={ROSE} />
              </div>
            )}
          </div>
        </ReportSection>
      )}

      {Object.keys(validation).length > 0 && (
        <ReportSection icon="■" title="Validation & Assurance Qualité">
          <div className="space-y-3">
            {[
              ['Statut Validation',   validation.validation_status || validation.status || validation.statut],
              ['Doublons détectés',   validation.duplicate_pairs   ?? validation.duplicates ?? validation.doublons],
              ['Ambiguïtés détectées', validation.ambiguity_count   ?? validation.ambiguities ?? validation.ambiguites],
              ['Score LLM',          validation.llm_quality_score !== undefined ? `${validation.llm_quality_score}/10` : undefined],
            ].filter(([, v]) => v !== undefined).map(([label, value], i) => (
              <div key={i} className="flex items-center gap-4">
                <span className="text-sm font-semibold w-44 flex-shrink-0" style={{ color: `${NAV}70` }}>{label} :</span>
                <span className="text-sm font-bold" style={{ color: NAV }}>{String(value)}</span>
              </div>
            ))}
            {validation.llm_quality_summary && (
              <div className="rounded-xl p-3 mt-2"
                style={{ background: `${VIOLET}08`, border: `1px solid ${VIOLET}20` }}>
                <p className="text-xs font-bold uppercase tracking-widest mb-1" style={{ color: VIOLET }}>Synthèse qualitative IA</p>
                <p className="text-sm leading-relaxed" style={{ color: NAV }}>{validation.llm_quality_summary}</p>
              </div>
            )}
            {Array.isArray(validation.issues) && validation.issues.length > 0 && (
              <div>
                <p className="text-xs font-bold uppercase tracking-widest mb-2" style={{ color: `${NAV}60` }}>Issues détectées :</p>
                <div className="space-y-2">
                  {validation.issues.map((issue: any, i: number) => (
                    <div key={i} className="p-3 rounded-xl"
                      style={{ background: `${ROSE}06`, border: `1px solid ${ROSE}20` }}>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-[10px] font-extrabold uppercase px-2 py-0.5 rounded-lg"
                          style={{ background: issue.severity === 'critical' ? `${ROSE}20` : `${ORANGE}20`,
                            color: issue.severity === 'critical' ? ROSE : ORANGE }}>
                          {issue.severity}
                        </span>
                        <span className="text-xs font-semibold" style={{ color: NAV }}>{issue.issue_type}</span>
                      </div>
                      <p className="text-xs leading-relaxed" style={{ color: `${NAV}80` }}>{issue.description}</p>
                      {issue.recommendation && (
                        <p className="text-xs mt-1 italic" style={{ color: VIOLET }}>{issue.recommendation}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </ReportSection>
      )}

      {recommendations.length > 0 && (
        <ReportSection icon="■" title="Recommandations">
          <div className="space-y-3">
            {(Array.isArray(recommendations) ? recommendations : Object.entries(recommendations)).map((rec: any, i: number) => {
              const priority = typeof rec === 'object' ? (rec.priority || rec.priorite || rec[0]) : null
              const text     = typeof rec === 'string' ? rec : rec.text || rec.description || rec[1] || JSON.stringify(rec)
              return (
                <div key={i} className="flex items-start gap-3 p-4 rounded-xl"
                  style={{ background: 'rgba(10,22,40,0.03)', border: '1px solid rgba(10,22,40,0.08)' }}>
                  {priority && (
                    <span className="px-2 py-0.5 rounded-lg text-[10px] font-extrabold uppercase flex-shrink-0 mt-0.5"
                      style={{
                        background: String(priority) === 'HIGH' ? `${ROSE}20` : `${ORANGE}20`,
                        color:      String(priority) === 'HIGH' ? ROSE : ORANGE,
                      }}>
                      {priority}
                    </span>
                  )}
                  <p className="text-sm leading-relaxed" style={{ color: NAV }}>{text}</p>
                </div>
              )
            })}
          </div>
        </ReportSection>
      )}

      {Object.keys(pipeline).length > 0 && (
        <ReportSection icon="■■" title="Notes de Traitement (Pipeline)">
          <BulletList
            items={Object.entries(pipeline).map(([k, v]) =>
              `${k.replace(/_/g, ' ')} : ${Array.isArray(v) ? v.join(', ') : String(v)}`
            )}
          />
        </ReportSection>
      )}

      <div className="flex items-center justify-between pt-4 border-t text-xs"
        style={{ borderColor: 'rgba(11,30,62,0.1)', color: `${NAV}50` }}>
        <span>
          Rapport généré le {timestamp ? new Date(timestamp).toLocaleString('fr-FR') : '—'} — Version {version || '—'}
        </span>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleDownloadMarkdown}
            disabled={downloading || !reportStoryId}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-bold text-white transition-all hover:-translate-y-0.5 disabled:opacity-50"
            style={{ background: CARD_GRADIENT, boxShadow: `0 4px 16px ${NAV}35` }}>
            {downloading ? <><Cpu size={14} className="animate-spin" /> MD…</> : <><FileText size={14} /> Télécharger .md</>}
          </button>
          <button
            type="button"
            onClick={handleDownloadPdf}
            disabled={!reportStoryId}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-bold text-white transition-all hover:-translate-y-0.5"
            style={{ background: `linear-gradient(135deg, ${ROSE}, ${ORANGE})`, boxShadow: `0 4px 16px ${ROSE}35` }}>
            <Printer size={14} /> Télécharger PDF
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Agent dispatcher ──────────────────────────────────────────────────────────

const AgentRichOutput: React.FC<{ agentKey: string; output: any; storyId?: string; onTestsChange?: (tests: any[]) => void }> = ({ agentKey, output, storyId, onTestsChange }) => {
  if (!output) return null
  if (agentKey === 'Agent 1') return <Agent1Result output={output} />
  if (agentKey === 'Agent 2') return <Agent2Result output={output} storyId={storyId} onTestsChange={onTestsChange} />
  if (agentKey === 'Agent 3') return <Agent3Result output={output} />
  if (agentKey === 'Agent 5') return <Agent5Result output={output} storyId={storyId} />
  if (typeof output === 'object') {
    const pairs = Object.entries(output).filter(([, v]) => typeof v !== 'object' || v === null)
    return (
      <div className="rounded-2xl overflow-hidden border" style={{ borderColor: 'rgba(10,22,40,0.1)' }}>
        <table className="w-full text-sm">
          <tbody>
            {pairs.map(([k, v]) => (
              <tr key={k} className="border-t first:border-0" style={{ borderColor: 'rgba(10,22,40,0.07)' }}>
                <td className="px-4 py-3 font-semibold text-xs uppercase tracking-wider w-40"
                  style={{ background: 'rgba(10,22,40,0.03)', color: `${NAV}70` }}>
                  {k.replace(/_/g, ' ')}
                </td>
                <td className="px-4 py-3 font-medium text-sm" style={{ color: NAV }}>{String(v)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  }
  return <p className="text-sm" style={{ color: NAV }}>{String(output)}</p>
}

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
  const [modelAgent2,   setModelAgent2]   = useState<ModelOption>('llama4')
  const [modelAgent3,   setModelAgent3]   = useState<ModelOption>('qwen3')
  const [modelAgent4,   setModelAgent4]   = useState<ModelOption>('qwen3')
  const [modelAgent5,   setModelAgent5]   = useState<ModelOption>('qwen3')
  const [manualTests,   setManualTests]   = useState<any[]>([])
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null)

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
      model_agent2: modelAgent2,
      model_agent3_quality: modelAgent3,
      model_agent4: modelAgent4,
      model_agent5: modelAgent5,
    }
    setLaunchToken(t => t + 1) // always increments → effect always fires
  }, [inputValue, useRag, useLegacyRag, runAgent4, forceRefresh, modelAgent1, modelAgent2, modelAgent3, modelAgent4, modelAgent5])

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
      warnings.push({
        title: 'Story non fonctionnelle',
        description: pipelineResult.errors?.[0]
          ? pipelineResult.errors[0]
          : `Cette story a été classée « ${pipelineResult.story_type} » et n'est pas traitée par le pipeline fonctionnel.`,
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
                    style={{ background: `linear-gradient(135deg,${ROSE},#dc2626)`, boxShadow: `0 4px 16px ${ROSE}45` }}>
                    <Square size={16} /> Arrêter
                  </button>
                ) : (
                  <button type="button" onClick={handleRun}
                    disabled={!inputValue.trim()}
                    className="px-8 py-4 rounded-2xl font-bold text-white flex items-center gap-2 flex-shrink-0 transition-all hover:-translate-y-0.5 disabled:opacity-40 disabled:cursor-not-allowed disabled:transform-none syn-btn-xray !text-sm !py-4 !px-8">
                    <Play size={16} /> Lancer le Pipeline
                  </button>
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

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 mt-2">
            <ModelSelector label="Modèle Agent 1" value={modelAgent1} onChange={setModelAgent1} />
            <ModelSelector label="Modèle Agent 2" value={modelAgent2} onChange={setModelAgent2} />
            <ModelSelector label="Modèle Agent 3" value={modelAgent3} onChange={setModelAgent3} />
            <ModelSelector label="Modèle Agent 5" value={modelAgent5} onChange={setModelAgent5} />
            <ModelSelector label="Modèle Agent 4" value={modelAgent4} onChange={setModelAgent4} disabled={!runAgent4} />
          </div>
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
              <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                {[
                  { label: 'Agent 1',    value: modelAgent1 },
                  { label: 'Agent 2',    value: modelAgent2 },
                  { label: 'Agent 3',    value: modelAgent3 },
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