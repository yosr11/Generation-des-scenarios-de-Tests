/**
 * AgentOutputs.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Shared, design-system-aligned components for every agent output panel.
 * Imported by both PipelinePage (live run) and StoryDetailPage (history view).
 *
 * Design language: clean white cards · subtle borders · restrained palette
 * Inspired by: Linear, Stripe, Notion, Vercel
 * ─────────────────────────────────────────────────────────────────────────────
 */
import React, { useState } from 'react'
import {
  FileText, GitBranch, CheckCircle2, XCircle,
  AlertCircle, AlertTriangle, TestTube,
  ChevronDown, ChevronUp, Printer, Cpu,
} from 'lucide-react'
import { ManualTestsTable } from '../tests/ManualTestsTable'

// ── Design Tokens ─────────────────────────────────────────────────────────────
const T = {
  text:    '#0f172a',   // slate-900
  muted:   '#64748b',   // slate-500
  faint:   '#94a3b8',   // slate-400
  border:  'rgba(15,23,42,0.08)',
  borderMd:'rgba(15,23,42,0.12)',
  surface: '#ffffff',
  bg:      '#f8fafc',   // slate-50
  violet:  '#7c3aed',
  rose:    '#f43f5e',
  orange:  '#f97316',
  emerald: '#10b981',
} as const

// ── Accent Helpers ────────────────────────────────────────────────────────────
type AccentColor = 'violet' | 'rose' | 'orange' | 'emerald' | 'slate'

const accentHex: Record<AccentColor, string> = {
  violet:  T.violet,
  rose:    T.rose,
  orange:  T.orange,
  emerald: T.emerald,
  slate:   T.muted,
}

// ════════════════════════════════════════════════════════════════════════════
// SHARED PRIMITIVES
// ════════════════════════════════════════════════════════════════════════════

/** Left-bar section title with optional count badge */
export const AgentSectionTitle: React.FC<{
  children: React.ReactNode
  count?: number
  accent?: AccentColor
}> = ({ children, count, accent = 'violet' }) => (
  <div className="flex items-center gap-2.5 mb-3">
    <div
      className="w-0.5 h-4 rounded-full flex-shrink-0"
      style={{ background: accentHex[accent] }}
    />
    <p className="text-[11px] font-bold uppercase tracking-widest text-slate-500">
      {children}
    </p>
    {count !== undefined && (
      <span
        className="px-1.5 py-0.5 rounded-md text-[10px] font-bold tabular-nums"
        style={{ background: `${accentHex[accent]}14`, color: accentHex[accent] }}
      >
        {count}
      </span>
    )}
  </div>
)

/** White metric card with large value */
export const AgentKPICard: React.FC<{
  label: string
  value: React.ReactNode
  accent?: AccentColor
}> = ({ label, value, accent = 'slate' }) => (
  <div
    className="bg-white rounded-xl p-4 flex flex-col"
    style={{
      border: `1px solid ${T.border}`,
      boxShadow: '0 1px 4px rgba(15,23,42,0.05)',
    }}
  >
    <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2">
      {label}
    </span>
    <div
      className="text-2xl font-extrabold leading-none tabular-nums"
      style={{ color: accent === 'slate' ? T.text : accentHex[accent] }}
    >
      {value}
    </div>
  </div>
)

/** Small pill badge */
export const AgentTag: React.FC<{
  children: React.ReactNode
  accent?: AccentColor
  size?: 'sm' | 'md'
}> = ({ children, accent = 'slate', size = 'sm' }) => (
  <span
    className={`inline-flex items-center font-semibold rounded-full whitespace-nowrap ${
      size === 'sm' ? 'px-2 py-0.5 text-[10px]' : 'px-3 py-1 text-xs'
    }`}
    style={{
      background: `${accentHex[accent]}13`,
      color: accentHex[accent],
      border: `1px solid ${accentHex[accent]}22`,
    }}
  >
    {children}
  </span>
)

/** Larger status pill for validation states */
export const AgentStatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const s = String(status).toUpperCase()
  const accent: AccentColor =
    s === 'VALID' || s === 'APPROVED' || s === 'EXCELLENT' ? 'emerald'
    : s === 'PARTIALLY_VALID' || s === 'REQUIRES_REVIEW'  ? 'orange'
    : 'rose'
  const Icon = accent === 'emerald' ? CheckCircle2 : accent === 'orange' ? AlertCircle : XCircle
  return (
    <span
      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold"
      style={{
        background: `${accentHex[accent]}12`,
        color: accentHex[accent],
        border: `1px solid ${accentHex[accent]}28`,
      }}
    >
      <Icon size={12} />
      {status}
    </span>
  )
}

/** Clean key-value table */
export const AgentInfoTable: React.FC<{ rows: [string, string][] }> = ({ rows }) => (
  <div className="rounded-xl overflow-hidden" style={{ border: `1px solid ${T.border}` }}>
    <table className="w-full text-sm">
      <tbody>
        {rows.map(([k, v], i) => (
          <tr key={i} className="border-t first:border-0" style={{ borderColor: T.border }}>
            <td
              className="px-4 py-2.5 text-[10px] font-bold uppercase tracking-wider w-44 text-slate-400"
              style={{ background: T.bg }}
            >
              {k}
            </td>
            <td className="px-4 py-2.5 text-sm font-medium text-slate-800">{v}</td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
)

/** Dot bullet list */
export const AgentBulletList: React.FC<{
  items: string[]
  accent?: AccentColor
}> = ({ items, accent = 'violet' }) => (
  <ul className="space-y-2">
    {items.map((item, i) => (
      <li key={i} className="flex items-start gap-2.5">
        <span
          className="w-1.5 h-1.5 rounded-full flex-shrink-0 mt-[7px]"
          style={{ background: accentHex[accent] }}
        />
        <span className="text-sm text-slate-600 leading-relaxed">{item}</span>
      </li>
    ))}
  </ul>
)

/** Centered empty state */
export const AgentEmptyState: React.FC<{
  icon: React.ElementType
  message: string
  sub?: string
}> = ({ icon: Icon, message, sub }) => (
  <div className="py-14 text-center">
    <div
      className="w-12 h-12 rounded-2xl flex items-center justify-center mx-auto mb-4"
      style={{ background: T.bg, border: `1px solid ${T.border}` }}
    >
      <Icon size={22} className="text-slate-400" />
    </div>
    <p className="text-sm font-semibold text-slate-500">{message}</p>
    {sub && <p className="text-xs text-slate-400 mt-1">{sub}</p>}
  </div>
)

/** Section card used inside Agent 5 report */
const ReportSection: React.FC<{
  title: string
  children: React.ReactNode
  accent?: AccentColor
}> = ({ title, children, accent = 'violet' }) => (
  <div
    className="bg-white rounded-xl overflow-hidden"
    style={{ border: `1px solid ${T.border}`, boxShadow: '0 1px 3px rgba(15,23,42,0.04)' }}
  >
    <div
      className="px-5 py-3 flex items-center gap-2.5"
      style={{ background: T.bg, borderBottom: `1px solid ${T.border}` }}
    >
      <div
        className="w-0.5 h-4 rounded-full flex-shrink-0"
        style={{ background: accentHex[accent] }}
      />
      <h4 className="text-[11px] font-bold uppercase tracking-widest text-slate-500">{title}</h4>
    </div>
    <div className="p-5">{children}</div>
  </div>
)

// ════════════════════════════════════════════════════════════════════════════
// AGENT 1 — Semantic Analysis
// ════════════════════════════════════════════════════════════════════════════
export const Agent1Result: React.FC<{ output: any }> = ({ output }) => {
  if (!output) return null
  const { story_id, story_title, story_type, actors, ...rest } = output

  const isEmptyScalar = (v: any) =>
    v === null || v === undefined || (typeof v === 'string' && v.trim() === '')

  const tableRows   = Object.entries(rest).filter(([, v]) => (typeof v !== 'object' || v === null) && !isEmptyScalar(v))
  const listEntries = Object.entries(rest).filter(([, v]) => Array.isArray(v) && (v as any[]).length > 0)
  const objEntries  = Object.entries(rest).filter(([, v]) => !Array.isArray(v) && typeof v === 'object' && v !== null && Object.keys(v as object).length > 0)

  return (
    <div className="space-y-6 w-full">

      {/* KPI row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {story_id && (
          <AgentKPICard label="Story ID" value={<span className="font-mono">{story_id}</span>} accent="violet" />
        )}
        {story_type && (
          <AgentKPICard label="Story Type" value={<span className="text-xl capitalize">{story_type}</span>} accent="slate" />
        )}
        {actors && (
          <div
            className="bg-white rounded-xl p-4"
            style={{ border: `1px solid ${T.border}`, boxShadow: '0 1px 4px rgba(15,23,42,0.05)' }}
          >
            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400 block mb-2">
              Acteurs
            </span>
            <div className="flex flex-wrap gap-1.5">
              {(Array.isArray(actors) ? actors : [actors]).map((a: string, i: number) => (
                <AgentTag key={i} accent="violet">{a}</AgentTag>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Story title */}
      {story_title && (
        <div
          className="rounded-xl px-5 py-4"
          style={{ background: T.bg, border: `1px solid ${T.border}` }}
        >
          <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400 block mb-1">
            Titre de la Story
          </span>
          <p className="text-sm font-semibold text-slate-800">{story_title}</p>
        </div>
      )}

      {/* Array sections */}
      {listEntries.map(([key, val]) => (
        <div key={key}>
          <AgentSectionTitle count={(val as any[]).length}>
            {key.replace(/_/g, ' ')}
          </AgentSectionTitle>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {(val as any[]).map((item: any, i: number) => {
              const isObj   = item && typeof item === 'object'
              const primary = isObj
                ? (item.description || item.label || item.title || item.name || item.text || '')
                : String(item)
              const secondary = isObj
                ? Object.entries(item).filter(
                    ([k, v]) =>
                      !['description', 'label', 'title', 'name', 'text'].includes(k) &&
                      (typeof v !== 'object' || v === null) &&
                      v !== null && v !== undefined && String(v).trim() !== ''
                  )
                : []
              return (
                <div
                  key={i}
                  className="flex items-start gap-3 p-3 rounded-lg bg-white"
                  style={{ border: `1px solid ${T.border}` }}
                >
                  <div
                    className="w-5 h-5 rounded-md flex items-center justify-center flex-shrink-0 mt-0.5 text-[9px] font-bold text-white tabular-nums"
                    style={{ background: T.violet }}
                  >
                    {i + 1}
                  </div>
                  <div className="flex-1 min-w-0">
                    <span className="text-[13px] leading-snug text-slate-800 block">
                      {primary || (isObj ? JSON.stringify(item) : '')}
                    </span>
                    {secondary.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1.5">
                        {secondary.map(([k, v]) => (
                          <span
                            key={k}
                            className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-500"
                          >
                            <span className="uppercase tracking-wider opacity-60">
                              {k.replace(/_/g, ' ')}
                            </span>
                            &nbsp;{String(v)}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      ))}

      {/* Scalar fields table */}
      {tableRows.length > 0 && (
        <AgentInfoTable
          rows={tableRows.map(([k, v]) => [k.replace(/_/g, ' '), String(v)])}
        />
      )}

      {/* Object fields (JSON) */}
      {objEntries.map(([key, val]) => (
        <div key={key}>
          <AgentSectionTitle>{key.replace(/_/g, ' ')}</AgentSectionTitle>
          <pre
            className="text-xs p-4 rounded-xl overflow-x-auto font-mono text-slate-700"
            style={{ background: T.bg, border: `1px solid ${T.border}` }}
          >
            {JSON.stringify(val, null, 2)}
          </pre>
        </div>
      ))}
    </div>
  )
}

// ════════════════════════════════════════════════════════════════════════════
// AGENT 1.5 — Business Modeling
// ════════════════════════════════════════════════════════════════════════════

const priorityAccent = (p: string): AccentColor =>
  p === 'haute' || p === 'high'   ? 'rose'
  : p === 'basse' || p === 'low'  ? 'slate'
  : 'violet'

/** Controlled accordion for a single workflow */
const WorkflowAccordion: React.FC<{ workflow: any }> = ({ workflow: w }) => {
  const [open, setOpen] = useState(false)
  return (
    <div
      className="rounded-xl overflow-hidden transition-all"
      style={{ border: `1px solid ${open ? T.rose + '40' : T.border}` }}
    >
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center gap-2.5 p-4 text-left select-none bg-white hover:bg-slate-50 transition-colors"
      >
        <AgentTag accent="rose" size="sm">{w.id}</AgentTag>
        <span className="font-semibold text-sm text-slate-800 flex-1 min-w-0 truncate">{w.label}</span>
        {w.linked_goal_id && (
          <AgentTag accent="violet" size="sm">→ {w.linked_goal_id}</AgentTag>
        )}
        {open
          ? <ChevronUp size={14} className="text-slate-400 flex-shrink-0" />
          : <ChevronDown size={14} className="text-slate-400 flex-shrink-0" />
        }
      </button>
      {open && (
        <div
          className="px-4 pb-4 space-y-4"
          style={{ borderTop: `1px solid ${T.border}`, background: T.bg }}
        >
          {w.trigger && (
            <div className="pt-3">
              <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-1">
                Déclencheur
              </p>
              <p className="text-xs text-slate-600">{w.trigger}</p>
            </div>
          )}
          {w.steps?.length > 0 && (
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2">
                Étapes ({w.steps.length})
              </p>
              <ol className="space-y-1.5">
                {w.steps.map((s: string, j: number) => (
                  <li key={j} className="flex gap-2.5 items-start text-xs text-slate-600">
                    <span
                      className="w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-bold text-white flex-shrink-0 mt-0.5 tabular-nums"
                      style={{ background: T.rose }}
                    >
                      {j + 1}
                    </span>
                    <span className="leading-relaxed">{s}</span>
                  </li>
                ))}
              </ol>
            </div>
          )}
          {w.success_criteria?.length > 0 && (
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2">
                Critères de succès
              </p>
              <ul className="space-y-1">
                {w.success_criteria.map((c: string, j: number) => (
                  <li key={j} className="flex gap-2 items-start text-xs text-slate-600">
                    <CheckCircle2
                      size={12}
                      className="flex-shrink-0 mt-0.5"
                      style={{ color: T.emerald }}
                    />
                    <span className="leading-relaxed">{c}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export const Agent15Result: React.FC<{ output: any }> = ({ output }) => {
  const bm        = output?.business_model || output || {}
  const goals     = bm.business_goals     || []
  const workflows = bm.business_workflows || []
  const notes     = bm.modeling_notes     || ''

  if (!goals.length && !workflows.length) return (
    <AgentEmptyState icon={GitBranch} message="Aucun modèle métier généré" sub={notes || undefined} />
  )

  return (
    <div className="space-y-6 w-full">

      {/* KPI row */}
      <div className="grid grid-cols-2 gap-3">
        <AgentKPICard label="Business Goals" value={goals.length} accent="violet" />
        <AgentKPICard label="Workflows"       value={workflows.length} accent="rose" />
      </div>

      {/* Business Goals */}
      {goals.length > 0 && (
        <div>
          <AgentSectionTitle count={goals.length} accent="violet">Business Goals</AgentSectionTitle>
          <div className="space-y-2">
            {goals.map((g: any, i: number) => (
              <div
                key={i}
                className="bg-white rounded-xl p-4 space-y-2"
                style={{ border: `1px solid ${T.border}` }}
              >
                <div className="flex items-center gap-2 flex-wrap">
                  <AgentTag accent="violet" size="sm">{g.id}</AgentTag>
                  <span className="font-semibold text-sm text-slate-800 flex-1">{g.label}</span>
                  {g.priority && (
                    <AgentTag accent={priorityAccent(g.priority)} size="sm">
                      {g.priority}
                    </AgentTag>
                  )}
                </div>
                {g.description && (
                  <p className="text-xs text-slate-500 leading-relaxed">{g.description}</p>
                )}
                {g.actors?.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {g.actors.map((a: string, j: number) => (
                      <AgentTag key={j} accent="slate" size="sm">{a}</AgentTag>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Business Workflows */}
      {workflows.length > 0 && (
        <div>
          <AgentSectionTitle count={workflows.length} accent="rose">Business Workflows</AgentSectionTitle>
          <div className="space-y-2">
            {workflows.map((w: any, i: number) => (
              <WorkflowAccordion key={i} workflow={w} />
            ))}
          </div>
        </div>
      )}

      {notes && (
        <p
          className="text-xs text-slate-400 italic border-t pt-3"
          style={{ borderColor: T.border }}
        >
          {notes}
        </p>
      )}
    </div>
  )
}

// ════════════════════════════════════════════════════════════════════════════
// AGENT 3 — Validation
// ════════════════════════════════════════════════════════════════════════════
export const Agent3Result: React.FC<{ output: any }> = ({ output }) => {
  if (!output) return null
  const report           = output?.report || output
  const coverage         = report?.coverage_rate ?? report?.coverage_percentage ?? 0
  const validationStatus = report?.validation_status
  const ambiguities      = report?.ambiguities || []
  const uncoveredPoints  = report?.uncovered_testable_points || []
  const duplicates       = report?.duplicate_tests || report?.duplicates || []
  const covPct           = Math.round((coverage || 0) * 100)

  const coverageAccent: AccentColor =
    covPct >= 80 ? 'emerald' : covPct >= 60 ? 'orange' : 'rose'

  const reasonList: string[] = []
  if (validationStatus === 'PARTIALLY_VALID' || validationStatus === 'INVALID') {
    if (uncoveredPoints.length)
      reasonList.push(`${uncoveredPoints.length} point${uncoveredPoints.length > 1 ? 's' : ''} non couverts`)
    if (duplicates.length)
      reasonList.push(`${duplicates.length} doublon${duplicates.length > 1 ? 's' : ''} détecté${duplicates.length > 1 ? 's' : ''}`)
    if (ambiguities.length)
      reasonList.push(`${ambiguities.length} ambiguïté${ambiguities.length > 1 ? 's' : ''} détectée${ambiguities.length > 1 ? 's' : ''}`)
    if (!reasonList.length)
      reasonList.push(
        validationStatus === 'PARTIALLY_VALID'
          ? 'Validation partielle : pas d\'issues techniques clairement identifiées.'
          : 'Validation invalide : vérifier les tests et les recommandations.'
      )
  }

  return (
    <div className="space-y-6 w-full">

      {/* KPI row */}
      <div className="grid grid-cols-3 gap-3">
        <AgentKPICard
          label="Couverture"
          value={`${covPct}%`}
          accent={coverageAccent}
        />
        <AgentKPICard
          label="Ambiguïtés"
          value={ambiguities.length}
          accent={ambiguities.length > 0 ? 'orange' : 'slate'}
        />
        <AgentKPICard
          label="Doublons"
          value={duplicates.length}
          accent={duplicates.length > 0 ? 'rose' : 'slate'}
        />
      </div>

      {/* Coverage progress bar */}
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
            Taux de couverture
          </span>
          <span className="text-sm font-bold" style={{ color: accentHex[coverageAccent] }}>
            {covPct}%
          </span>
        </div>
        <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${Math.min(covPct, 100)}%`,
              background: accentHex[coverageAccent],
            }}
          />
        </div>
      </div>

      {/* Validation status */}
      {validationStatus && (
        <div className="flex items-center gap-3">
          <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
            Statut de Validation
          </span>
          <AgentStatusBadge status={validationStatus} />
        </div>
      )}

      {/* Reason list */}
      {reasonList.length > 0 && (
        <div
          className="rounded-xl p-4"
          style={{ background: `${T.orange}08`, border: `1px solid ${T.orange}22` }}
        >
          <p className="text-[10px] font-bold uppercase tracking-widest text-orange-600 mb-2">
            Raison du statut
          </p>
          <ul className="space-y-1.5">
            {reasonList.map((r, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-orange-800">
                <AlertCircle size={13} className="flex-shrink-0 mt-0.5 text-orange-500" />
                {r}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Ambiguities */}
      {ambiguities.length > 0 && (
        <div>
          <AgentSectionTitle count={ambiguities.length} accent="orange">
            Ambiguïtés détectées
          </AgentSectionTitle>
          <div className="space-y-2">
            {ambiguities.map((a: any, i: number) => (
              <div
                key={i}
                className="flex items-start gap-3 p-3 rounded-lg"
                style={{ background: `${T.orange}07`, border: `1px solid ${T.orange}20` }}
              >
                <AlertCircle size={14} className="flex-shrink-0 mt-0.5 text-orange-400" />
                <span className="text-sm text-slate-700 leading-relaxed">
                  {typeof a === 'string' ? a : a.description || JSON.stringify(a)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Duplicates */}
      {duplicates.length > 0 && (
        <div>
          <AgentSectionTitle count={duplicates.length} accent="rose">
            Tests en doublon
          </AgentSectionTitle>
          <div className="space-y-2">
            {duplicates.map((d: any, i: number) => (
              <div
                key={i}
                className="flex items-start gap-3 p-3 rounded-lg"
                style={{ background: `${T.rose}06`, border: `1px solid ${T.rose}18` }}
              >
                <AlertTriangle size={14} className="flex-shrink-0 mt-0.5 text-rose-400" />
                <span className="text-sm text-slate-700 leading-relaxed">
                  {typeof d === 'string' ? d : d.description || JSON.stringify(d)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Uncovered points */}
      {uncoveredPoints.length > 0 && (
        <div>
          <AgentSectionTitle count={uncoveredPoints.length} accent="rose">
            Points non couverts
          </AgentSectionTitle>
          <div className="space-y-2">
            {uncoveredPoints.map((p: string, i: number) => (
              <div
                key={i}
                className="flex items-start gap-3 p-3 rounded-lg"
                style={{ background: `${T.rose}05`, border: `1px solid ${T.rose}14` }}
              >
                <XCircle size={14} className="flex-shrink-0 mt-0.5 text-rose-400" />
                <span className="text-sm text-slate-700 leading-relaxed">{p}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ════════════════════════════════════════════════════════════════════════════
// AGENT 5 — Quality Report
// ════════════════════════════════════════════════════════════════════════════
export const Agent5Result: React.FC<{ output: any; storyId?: string }> = ({ output, storyId }) => {
  if (!output) return null
  const [downloading, setDownloading] = useState(false)

  // Normalise wrapped / direct output shape
  const reportObj     = output.report || output
  const reportTitle   = reportObj.report_title      || output.report_title
  const version       = reportObj.report_version    || output.report_version
  const timestamp     = reportObj.generated_timestamp || output.generated_timestamp
  const reportStoryId = reportObj.story_id          || output.story_id || storyId

  const exec         = reportObj.executive_summary  || output.executive_summary  || {}
  const globalStatus = exec.overall_status          || exec.global_status
  const findings     = exec.key_findings            || exec.main_findings    || []
  const nextSteps    = exec.next_steps              || exec.prochaines_etapes || []

  const storySynth      = reportObj.story_summary    || output.story_summary    || {}
  const testSuite       = reportObj.test_suite       || output.test_suite       || {}
  const coverage        = reportObj.coverage_metrics || output.coverage_metrics || {}
  const validation      = reportObj.quality_assurance|| output.quality_assurance|| {}
  const recommendations = reportObj.recommendations  || output.recommendations  || []
  const pipeline        = reportObj.processing_notes || output.processing_notes || []

  // ── Handlers ──────────────────────────────────────────────────────────────
  const handleDownloadMarkdown = async () => {
    if (!reportStoryId) return
    setDownloading(true)
    try {
      const { apiClient } = await import('../../api/client')
      const md = await apiClient.agent5.getReportMarkdown(reportStoryId)
      const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' })
      const url  = URL.createObjectURL(blob)
      const a    = document.createElement('a')
      a.href = url
      a.download = `rapport-qa-${reportStoryId}.md`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (err) { console.error('Download failed:', err) }
    finally { setDownloading(false) }
  }

  const handleDownloadPdf = () => {
    const printWindow = window.open('', '_blank')
    if (!printWindow) return
    const findingsHtml  = findings.map((f: string) => `<li>${f}</li>`).join('')
    const nextStepsHtml = nextSteps.map((s: string) => `<li>${s}</li>`).join('')
    const testSuiteHtml = (testSuite.tests_summary || []).map((t: any) => `
      <tr>
        <td><span style="font-weight:700;color:#f97316;">${t.scenario_type || t.type || 'NOM'}</span></td>
        <td>${t.test_name || t.name || '—'}</td>
        <td>${t.priority || '—'}</td>
        <td>${t.step_count !== undefined ? t.step_count : t.steps_count !== undefined ? t.steps_count : 0} étapes</td>
      </tr>`).join('')
    const recsHtml = recommendations.map((rec: any) => {
      const priority  = rec.priority  || 'LOW'
      const action    = rec.action    || rec.text || 'Recommandation'
      const rationale = rec.rationale || rec.description || ''
      return `<div class="rec-card"><div class="rec-hd">[${priority.toUpperCase()}] ${action}</div><div class="rec-bd">${rationale}</div></div>`
    }).join('')
    const pipelineHtml = Array.isArray(pipeline)
      ? pipeline.map((p: string) => `<li>${p}</li>`).join('')
      : Object.entries(pipeline).map(([k, v]) => `<li><strong>${k}</strong> : ${v}</li>`).join('')

    const html = `<!DOCTYPE html><html><head><title>Rapport QA · ${reportStoryId}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800&display=swap');
  body{font-family:'Outfit',sans-serif;color:#0f172a;margin:40px;line-height:1.6}
  .hdr{font-size:11px;color:#64748b;margin-bottom:18px}
  .ttl{font-size:24px;font-weight:800;color:#7c3aed;border-bottom:2px solid #7c3aed;padding-bottom:10px;margin-bottom:28px}
  h2{font-size:14px;font-weight:800;color:#0f172a;margin-top:26px;margin-bottom:12px;border-bottom:1px solid #e2e8f0;padding-bottom:4px}
  h3{font-size:12px;font-weight:700;margin-top:14px;margin-bottom:8px;color:#475569}
  .badge{display:inline-block;padding:3px 10px;border-radius:999px;font-size:11px;font-weight:700;background:rgba(249,115,22,.12);color:#f97316;border:1px solid rgba(249,115,22,.28);margin-left:8px}
  ul{padding-left:18px;margin-bottom:14px}li{margin-bottom:5px;font-size:13px}
  table{width:100%;border-collapse:collapse;margin-bottom:20px;font-size:13px;border:1px solid #e2e8f0}
  th,td{padding:9px 12px;text-align:left;border-bottom:1px solid #e2e8f0}
  th{background:#0f172a;color:#fff;font-weight:700;font-size:10px;text-transform:uppercase;letter-spacing:.05em}
  td.prop{font-weight:600;background:#f8fafc;width:30%;color:#64748b;font-size:11px;text-transform:uppercase;letter-spacing:.05em}
  .rec-card{background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:10px 14px;margin-bottom:10px}
  .rec-hd{font-weight:800;font-size:11px;color:#f97316;margin-bottom:4px}
  .rec-bd{font-size:13px;color:#334155}
  .ftr{margin-top:40px;border-top:1px solid #e2e8f0;padding-top:12px;font-size:11px;color:#94a3b8}
  @media print{body{margin:20px}}
</style></head><body>
<div class="hdr">Agent Test — Rapport QA · ${reportStoryId}</div>
<div class="ttl">${reportTitle || `Rapport QA — ${reportStoryId}`}</div>
<h2>Résumé Exécutif</h2>
<p><strong>Statut Global :</strong><span class="badge">${globalStatus || 'APPROVED'}</span></p>
<h3>Findings Principaux</h3><ul>${findingsHtml || '<li>Aucun finding disponible</li>'}</ul>
<h3>Prochaines Étapes</h3><ul>${nextStepsHtml || '<li>Aucune étape recommandée</li>'}</ul>
<h2>Synthèse User Story</h2>
<table>
  <tr><td class="prop">ID</td><td><strong>${reportStoryId || '—'}</strong></td></tr>
  <tr><td class="prop">Titre</td><td>${storySynth.story_title || storySynth.title || '—'}</td></tr>
  <tr><td class="prop">Type</td><td>${storySynth.story_type  || storySynth.type  || '—'}</td></tr>
</table>
<p><strong>Acteurs :</strong> ${storySynth.actors?.length > 0 ? storySynth.actors.join(', ') : 'N/A'}</p>
<p><strong>Règles Métier :</strong> ${storySynth.business_rules?.length > 0 ? storySynth.business_rules.join('. ') : 'Aucune'}</p>
<h2>Suite de Tests</h2>
<ul>
  <li><strong>Total :</strong> ${testSuite.total_tests ?? 0} cas de test</li>
  <li><strong>NOM :</strong> ${testSuite.nom_count ?? 0}</li>
  <li><strong>ALT :</strong> ${testSuite.alt_count ?? 0}</li>
  <li><strong>EXC :</strong> ${testSuite.exc_count ?? 0}</li>
  <li><strong>Priorités Haute :</strong> ${testSuite.high_priority_count ?? 0}</li>
</ul>
<table><thead><tr><th>Type</th><th>Nom</th><th>Priorité</th><th>Étapes</th></tr></thead>
<tbody>${testSuiteHtml || '<tr><td colspan="4">Aucun test généré</td></tr>'}</tbody></table>
<h2>Métriques de Couverture</h2>
<ul>
  <li><strong>Taux :</strong> ${coverage.coverage_rate !== undefined ? coverage.coverage_rate + '%' : '0%'}</li>
  <li><strong>Statut :</strong> ${coverage.coverage_status || 'EXCELLENT'}</li>
  <li><strong>Points Non Couverts :</strong> ${coverage.uncovered_points?.length > 0 ? coverage.uncovered_points.join(', ') : 'Aucun'}</li>
</ul>
<h2>Validation &amp; Assurance Qualité</h2>
<p><strong>Statut Validation :</strong><span class="badge">${validation.validation_status || 'VALID'}</span></p>
<ul>
  <li><strong>Doublons détectés :</strong> ${validation.duplicate_pairs ?? 0}</li>
  <li><strong>Ambiguïtés détectées :</strong> ${validation.ambiguity_count ?? 0}</li>
  <li><strong>Score LLM :</strong> ${validation.llm_quality_score !== undefined ? validation.llm_quality_score : 'N/A'}/10</li>
</ul>
<h2>Recommandations</h2>${recsHtml || '<p>Aucune recommandation</p>'}
<h2>Notes de Traitement</h2><ul>${pipelineHtml || '<li>Aucune note</li>'}</ul>
<div class="ftr">Rapport généré le ${new Date(timestamp || new Date()).toLocaleString('fr-FR')} — Version ${version || '1.0'}</div>
<script>window.onload=function(){window.print()}</script>
</body></html>`
    printWindow.document.write(html)
    printWindow.document.close()
  }

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="w-full space-y-4 modal-print-area">

      {/* Report header — compact white card */}
      <div
        className="bg-white rounded-xl p-5"
        style={{ border: `1px solid ${T.border}`, boxShadow: '0 1px 6px rgba(15,23,42,0.05)' }}
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-1.5">
              Rapport QA Final
            </p>
            <h2 className="text-base font-bold text-slate-900 leading-snug mb-3">
              {reportTitle || `Rapport QA — ${reportStoryId}`}
            </h2>
            <div className="flex flex-wrap items-center gap-2">
              {reportStoryId && <AgentTag accent="violet">{reportStoryId}</AgentTag>}
              {version && <AgentTag accent="slate">v{version}</AgentTag>}
              {timestamp && (
                <span className="text-[10px] text-slate-400">
                  {new Date(timestamp).toLocaleString('fr-FR')}
                </span>
              )}
            </div>
          </div>
          {globalStatus && (
            <div className="flex-shrink-0 pt-1">
              <AgentStatusBadge status={globalStatus} />
            </div>
          )}
        </div>
      </div>

      {/* Executive Summary */}
      {(findings.length > 0 || nextSteps.length > 0) && (
        <ReportSection title="Résumé Exécutif" accent="violet">
          <div className="space-y-4">
            {globalStatus && (
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500">Statut Global :</span>
                <AgentStatusBadge status={globalStatus} />
              </div>
            )}
            {findings.length > 0 && (
              <div>
                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2">
                  Findings Principaux
                </p>
                <AgentBulletList items={findings} accent="violet" />
              </div>
            )}
            {nextSteps.length > 0 && (
              <div>
                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2">
                  Prochaines Étapes
                </p>
                <AgentBulletList items={nextSteps} accent="slate" />
              </div>
            )}
          </div>
        </ReportSection>
      )}

      {/* Story Synthesis */}
      {Object.keys(storySynth).length > 0 && (
        <ReportSection title="Synthèse User Story" accent="violet">
          <AgentInfoTable
            rows={Object.entries(storySynth)
              .filter(([, v]) => typeof v === 'string' || typeof v === 'number')
              .map(([k, v]) => [
                k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
                String(v),
              ])}
          />
        </ReportSection>
      )}

      {/* Test Suite */}
      {Object.keys(testSuite).length > 0 && (
        <ReportSection title="Suite de Tests Générée" accent="orange">
          <div className="space-y-4">
            {/* Mini KPI grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                { label: 'Total', value: testSuite.total_tests  ?? testSuite.total },
                { label: 'NOM',   value: testSuite.nom_count    ?? testSuite.nom   ?? testSuite.nominal },
                { label: 'ALT',   value: testSuite.alt_count    ?? testSuite.alt   ?? testSuite.alternative },
                { label: 'EXC',   value: testSuite.exc_count    ?? testSuite.exc   ?? testSuite.exception },
              ].filter(r => r.value !== undefined).map((item, i) => (
                <div
                  key={i}
                  className="rounded-lg p-3 text-center"
                  style={{ background: T.bg, border: `1px solid ${T.border}` }}
                >
                  <p className="text-xl font-extrabold text-slate-800 tabular-nums">
                    {item.value}
                  </p>
                  <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mt-0.5">
                    {item.label}
                  </p>
                </div>
              ))}
            </div>

            {/* Tests summary table */}
            {(testSuite.tests_summary || testSuite.tests || []).length > 0 && (
              <div className="rounded-xl overflow-hidden" style={{ border: `1px solid ${T.border}` }}>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="syn-table-head">
                      <th className="px-4 py-3 text-left text-xs font-bold text-white">Type</th>
                      <th className="px-4 py-3 text-left text-xs font-bold text-white">Nom</th>
                      <th className="px-4 py-3 text-left text-xs font-bold text-white">Priorité</th>
                      <th className="px-4 py-3 text-left text-xs font-bold text-white">Étapes</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(testSuite.tests_summary || testSuite.tests || []).map((t: any, i: number) => (
                      <tr
                        key={i}
                        className="border-t hover:bg-slate-50 transition-colors"
                        style={{ borderColor: T.border }}
                      >
                        <td className="px-4 py-3">
                          <AgentTag accent="orange">
                            {t.type || t.classification || t.scenario_type || '—'}
                          </AgentTag>
                        </td>
                        <td className="px-4 py-3 text-xs font-medium text-slate-800">
                          {t.name || t.nom || t.test_name || '—'}
                        </td>
                        <td className="px-4 py-3 text-xs text-slate-500">
                          {t.priority || t.priorite || '—'}
                        </td>
                        <td className="px-4 py-3 text-xs text-slate-500">
                          {t.step_count  !== undefined ? `${t.step_count} étapes`
                            : t.steps_count !== undefined ? `${t.steps_count} étapes`
                            : t.steps ? `${t.steps} étapes` : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </ReportSection>
      )}

      {/* Coverage */}
      {Object.keys(coverage).length > 0 && (
        <ReportSection title="Métriques de Couverture" accent="emerald">
          <div className="space-y-4">
            {coverage.coverage_rate !== undefined && (
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs text-slate-500">Taux de couverture</span>
                  <span className="text-sm font-bold" style={{ color: T.emerald }}>
                    {Math.round(coverage.coverage_rate)}%
                  </span>
                </div>
                <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: `${Math.min(coverage.coverage_rate, 100)}%`,
                      background: T.emerald,
                    }}
                  />
                </div>
              </div>
            )}
            <AgentInfoTable
              rows={(
                [
                  ['Statut',             coverage.coverage_status || coverage.statut],
                  ['Points testables',   coverage.total_testable_points ?? coverage.total_points],
                  ['Points couverts',    coverage.covered_points ?? coverage.points_couverts],
                  ['Points non couverts', Array.isArray(coverage.uncovered_points)
                    ? (coverage.uncovered_points.length === 0 ? 'Aucun' : `${coverage.uncovered_points.length} point(s)`)
                    : coverage.uncovered_points_count ?? undefined],
                ] as [string, any][]
              )
                .filter(([, v]) => v !== undefined && v !== '—')
                .map(([k, v]) => [k, String(v)])}
            />
            {Array.isArray(coverage.uncovered_points) && coverage.uncovered_points.length > 0 && (
              <div>
                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2">
                  Points non couverts
                </p>
                <AgentBulletList items={coverage.uncovered_points} accent="rose" />
              </div>
            )}
          </div>
        </ReportSection>
      )}

      {/* Validation QA */}
      {Object.keys(validation).length > 0 && (
        <ReportSection title="Validation &amp; Assurance Qualité" accent="violet">
          <div className="space-y-4">
            <AgentInfoTable
              rows={(
                [
                  ['Statut Validation',    validation.validation_status || validation.status || validation.statut],
                  ['Doublons détectés',    validation.duplicate_pairs   ?? validation.duplicates ?? validation.doublons],
                  ['Ambiguïtés détectées', validation.ambiguity_count   ?? validation.ambiguities ?? validation.ambiguites],
                  ['Score LLM',           validation.llm_quality_score !== undefined ? `${validation.llm_quality_score}/10` : undefined],
                ] as [string, any][]
              )
                .filter(([, v]) => v !== undefined)
                .map(([k, v]) => [k, String(v)])}
            />
            {validation.llm_quality_summary && (
              <div
                className="rounded-lg p-3.5"
                style={{ background: `${T.violet}07`, border: `1px solid ${T.violet}18` }}
              >
                <p
                  className="text-[10px] font-bold uppercase tracking-widest mb-1.5"
                  style={{ color: T.violet }}
                >
                  Synthèse qualitative IA
                </p>
                <p className="text-sm text-slate-700 leading-relaxed">
                  {validation.llm_quality_summary}
                </p>
              </div>
            )}
            {Array.isArray(validation.issues) && validation.issues.length > 0 && (
              <div>
                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2">
                  Issues détectées
                </p>
                <div className="space-y-2">
                  {validation.issues.map((issue: any, i: number) => (
                    <div
                      key={i}
                      className="p-3 rounded-lg"
                      style={{ background: `${T.rose}05`, border: `1px solid ${T.rose}16` }}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <AgentTag accent={issue.severity === 'critical' ? 'rose' : 'orange'}>
                          {issue.severity}
                        </AgentTag>
                        <span className="text-xs font-semibold text-slate-700">
                          {issue.issue_type}
                        </span>
                      </div>
                      <p className="text-xs text-slate-600 leading-relaxed">{issue.description}</p>
                      {issue.recommendation && (
                        <p className="text-xs mt-1 italic" style={{ color: T.violet }}>
                          {issue.recommendation}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </ReportSection>
      )}

      {/* Recommendations */}
      {recommendations.length > 0 && (
        <ReportSection title="Recommandations" accent="orange">
          <div className="space-y-2">
            {(Array.isArray(recommendations) ? recommendations : Object.entries(recommendations))
              .map((rec: any, i: number) => {
                const priority = typeof rec === 'object' ? (rec.priority || rec.priorite || rec[0]) : null
                const text     = typeof rec === 'string'
                  ? rec
                  : rec.text || rec.action || rec.description || rec[1] || JSON.stringify(rec)
                const pAccent: AccentColor =
                  String(priority).toUpperCase() === 'HIGH' ? 'rose' : 'orange'
                return (
                  <div
                    key={i}
                    className="flex items-start gap-3 p-3.5 rounded-lg bg-white"
                    style={{ border: `1px solid ${T.border}` }}
                  >
                    {priority && (
                      <AgentTag accent={pAccent}>{priority}</AgentTag>
                    )}
                    <p className="text-sm text-slate-700 leading-relaxed flex-1">{text}</p>
                  </div>
                )
              })}
          </div>
        </ReportSection>
      )}

      {/* Pipeline notes */}
      {(Array.isArray(pipeline) ? pipeline.length > 0 : Object.keys(pipeline).length > 0) && (
        <ReportSection title="Notes de Traitement (Pipeline)" accent="slate">
          <AgentBulletList
            items={
              Array.isArray(pipeline)
                ? pipeline
                : Object.entries(pipeline).map(
                    ([k, v]) =>
                      `${k.replace(/_/g, ' ')} : ${Array.isArray(v) ? v.join(', ') : String(v)}`
                  )
            }
            accent="slate"
          />
        </ReportSection>
      )}

      {/* Footer + download buttons */}
      <div
        className="flex items-center justify-between pt-4 border-t"
        style={{ borderColor: T.border }}
      >
        <span className="text-[10px] text-slate-400">
          {timestamp
            ? `Généré le ${new Date(timestamp).toLocaleString('fr-FR')}`
            : 'Rapport QA'}
          {version ? ` — v${version}` : ''}
        </span>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleDownloadMarkdown}
            disabled={downloading || !reportStoryId}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold transition-all hover:-translate-y-0.5 disabled:opacity-50"
            style={{
              background: T.bg,
              border: `1px solid ${T.border}`,
              color: T.text,
              boxShadow: '0 1px 3px rgba(15,23,42,0.06)',
            }}
          >
            {downloading
              ? <><Cpu size={12} className="animate-spin" /> MD…</>
              : <><FileText size={12} /> Télécharger .md</>
            }
          </button>
          <button
            type="button"
            onClick={handleDownloadPdf}
            disabled={!reportStoryId}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold text-white transition-all hover:-translate-y-0.5 disabled:opacity-40"
            style={{
              background: T.violet,
              boxShadow: `0 3px 12px ${T.violet}35`,
            }}
          >
            <Printer size={12} /> Télécharger PDF
          </button>
        </div>
      </div>
    </div>
  )
}

// ════════════════════════════════════════════════════════════════════════════
// AGENT 2 — Internal wrapper (state + ManualTestsTable)
// ════════════════════════════════════════════════════════════════════════════
const Agent2ResultWrapper: React.FC<{
  output: any
  storyId?: string
  onTestsChange?: (tests: any[]) => void
}> = ({ output, storyId, onTestsChange }) => {
  const [tests, setTests] = useState<any[]>(
    Array.isArray(output) ? output : output?.tests || output?.agent2_tests || []
  )
  const handleChange = (next: any[]) => {
    setTests(next)
    onTestsChange?.(next)
  }
  if (!tests.length) return (
    <AgentEmptyState icon={TestTube} message="Aucun test généré" />
  )
  return (
    <ManualTestsTable
      tests={tests}
      storyId={storyId}
      onTestsChange={handleChange}
      expandable
      showProjectPicker
    />
  )
}

// ════════════════════════════════════════════════════════════════════════════
// DISPATCHER — picks the right agent output component
// ════════════════════════════════════════════════════════════════════════════
export const AgentRichOutput: React.FC<{
  agentKey: string
  output: any
  storyId?: string
  onTestsChange?: (tests: any[]) => void
}> = ({ agentKey, output, storyId, onTestsChange }) => {
  if (!output) return null
  if (agentKey === 'Agent 1')   return <Agent1Result   output={output} />
  if (agentKey === 'Agent 1.5') return <Agent15Result  output={output} />
  if (agentKey === 'Agent 2')   return <Agent2ResultWrapper output={output} storyId={storyId} onTestsChange={onTestsChange} />
  if (agentKey === 'Agent 3')   return <Agent3Result   output={output} />
  if (agentKey === 'Agent 5')   return <Agent5Result   output={output} storyId={storyId} />

  // Fallback: key-value table for unknown agents
  if (typeof output === 'object') {
    const pairs = Object.entries(output).filter(([, v]) => typeof v !== 'object' || v === null)
    if (pairs.length > 0) return (
      <AgentInfoTable rows={pairs.map(([k, v]) => [k.replace(/_/g, ' '), String(v)])} />
    )
  }
  return <p className="text-sm text-slate-700">{String(output)}</p>
}
