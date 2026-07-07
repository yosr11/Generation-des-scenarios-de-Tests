import React, { useEffect, useState, useCallback } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useStory } from '../hooks'
import { apiClient, StoredStory } from '../api/client'
import { useToast } from '../contexts/ToastContext'
import {
  ArrowLeft, Trash2, FileText, CheckCircle2, XCircle,
  TestTube, FileBarChart2, ArrowRight, Workflow,
  GitBranch, ChevronDown, Printer, HelpCircle
} from 'lucide-react'
import { Badge } from '../components/ui/Badge'
import { Alert } from '../components/ui/Alert'
import { ManualTestsTable } from '../components/tests/ManualTestsTable'

// ── Colors & Styles matching PipelinePage ──────────────────────────────────
const NAV       = '#0B1E3E'
const NAV_LIGHT = '#1A3A6B'
const ROSE      = '#DB2777'
const ORANGE    = '#EA580C'
const VIOLET    = '#1D4ED8'

const CARD_GRADIENT = `linear-gradient(135deg, ${NAV}, ${NAV_LIGHT}, ${VIOLET})`
// Dégradé vif pour les cartes d'en-tête (Story ID / Type / Acteurs) : bleu → rose → rouge
const HEADER_GRADIENT = 'linear-gradient(135deg, #2563EB 0%, #7C3AED 40%, #DB2777 75%, #F43F5E 100%)'
const HEADER_SHADOW   = '0 8px 26px rgba(219,39,119,0.30)'

const AGENT_INFO: Record<string, { label: string; desc: string; icon: React.ElementType; gradient: string }> = {
  'Agent 1':   { label: 'Agent 1 — Analyse',              desc: 'Analyse sémantique de la user story',             icon: FileText,      gradient: CARD_GRADIENT },
  'Agent 1.5': { label: 'Agent 1.5 — Business Modeling',  desc: 'Goals métier & workflows end-to-end',              icon: Workflow,      gradient: CARD_GRADIENT },
  'Agent 2':   { label: 'Agent 2 — Génération des tests', desc: 'Création des scénarios de tests manuels',         icon: TestTube,      gradient: CARD_GRADIENT },
  'Agent 3':   { label: 'Agent 3 — Validation',           desc: 'Couverture, ambiguïtés & cas limites',            icon: CheckCircle2,  gradient: CARD_GRADIENT },
  'Agent 5':   { label: 'Agent 5 — Rapport',              desc: 'Rapport qualité & recommandations',               icon: FileBarChart2, gradient: CARD_GRADIENT },
}

// ── Section Title ─────────────────────────────────────────────────────────────
const SectionTitle: React.FC<{ children: React.ReactNode; count?: number }> = ({ children, count }) => (
  <div className="flex items-center gap-2.5 mb-3">
    <div className="w-1 h-5 rounded-full flex-shrink-0" style={{ background: `linear-gradient(180deg,${VIOLET},${ROSE})` }} />
    <p className="text-sm font-extrabold uppercase tracking-widest" style={{ color: NAV }}>
      {children}
    </p>
    {count !== undefined && (
      <span className="px-2 py-0.5 rounded-full text-xs font-bold ml-1"
        style={{ background: `${VIOLET}15`, color: VIOLET }}>
        {count}
      </span>
    )}
  </div>
)

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

// ── Agent 1 Result (rendu complet dynamique, identique à la vue live) ─────────
const Agent1Result: React.FC<{ output: any }> = ({ output }) => {
  if (!output) return null
  const { story_id, story_title, story_type, actors, ...rest } = output

  const isEmptyScalar = (v: any) =>
    v === null || v === undefined || (typeof v === 'string' && v.trim() === '')

  // On n'affiche que les données réellement présentes : plus de titres de
  // section orphelins (ex. « BUSINESS RULES » sans contenu) ni de valeurs vides.
  const tableRows   = Object.entries(rest).filter(
    ([, v]) => (typeof v !== 'object' || v === null) && !isEmptyScalar(v)
  )
  const listEntries = Object.entries(rest).filter(
    ([, v]) => Array.isArray(v) && v.length > 0
  )
  const objEntries  = Object.entries(rest).filter(
    ([, v]) => !Array.isArray(v) && typeof v === 'object' && v !== null && Object.keys(v).length > 0
  )

  return (
    <div className="space-y-8 w-full">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {story_id && (
          <div className="rounded-2xl p-5 flex flex-col gap-1.5"
            style={{ background: HEADER_GRADIENT, boxShadow: HEADER_SHADOW }}>
            <span className="text-[10px] font-bold uppercase tracking-widest text-white/60">Story ID</span>
            <span className="text-2xl font-extrabold text-white font-mono">{story_id}</span>
          </div>
        )}
        {story_type && (
          <div className="rounded-2xl p-5 flex flex-col gap-1.5"
            style={{ background: HEADER_GRADIENT, boxShadow: HEADER_SHADOW }}>
            <span className="text-[10px] font-bold uppercase tracking-widest text-white/60">Story Type</span>
            <span className="text-xl font-bold text-white capitalize">{story_type}</span>
          </div>
        )}
        {actors && (
          <div className="rounded-2xl p-5 flex flex-col gap-2"
            style={{ background: HEADER_GRADIENT, boxShadow: HEADER_SHADOW }}>
            <span className="text-[10px] font-bold uppercase tracking-widest text-white/60">Acteurs</span>
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
          <SectionTitle count={(val as any[]).length}>{key.replace(/_/g, ' ')}</SectionTitle>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {(val as any[]).map((item: any, i: number) => {
              const isObj = item && typeof item === 'object'
              const primary = isObj
                ? (item.description || item.label || item.title || item.name || item.text || '')
                : String(item)
              const secondary = isObj
                ? Object.entries(item)
                    .filter(([k, v]) =>
                      !['description', 'label', 'title', 'name', 'text'].includes(k) &&
                      (typeof v !== 'object' || v === null) &&
                      v !== null && v !== undefined && String(v).trim() !== ''
                    )
                : []
              return (
                <div key={i} className="flex items-start gap-3 p-3 rounded-xl"
                  style={{ background: 'rgba(10,22,40,0.03)', border: '1px solid rgba(10,22,40,0.07)' }}>
                  <div className="w-6 h-6 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5"
                    style={{ background: CARD_GRADIENT }}>
                    <span className="text-[10px] font-bold text-white">{i + 1}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <span className="text-sm leading-relaxed block" style={{ color: NAV }}>
                      {primary || (isObj ? JSON.stringify(item) : '')}
                    </span>
                    {secondary.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 mt-1.5">
                        {secondary.map(([k, v]) => (
                          <span key={k} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold"
                            style={{ background: 'rgba(10,22,40,0.06)', color: `${NAV}90` }}>
                            <span className="uppercase tracking-wider opacity-60">{k.replace(/_/g, ' ')}</span>
                            {String(v)}
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

// ── Agent 2 Result (format Xray, identique à la vue live) ─────────────────────
const Agent2Result: React.FC<{ output: any; storyId?: string }> = ({ output, storyId }) => {
  const tests = Array.isArray(output) ? output : output?.tests || output?.agent2_tests || []
  if (!tests.length) return (
    <div className="py-12 text-center">
      <TestTube size={32} className="mx-auto mb-3 opacity-30" style={{ color: NAV }} />
      <p className="text-sm font-medium text-slate-400">Aucun test généré</p>
    </div>
  )
  return (
    <ManualTestsTable
      tests={tests}
      storyId={storyId}
      expandable
      showProjectPicker
    />
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

// ── Agent 5 Result — sub-components ──────────────────────────────────────────
const BulletList: React.FC<{ items: string[]; color?: string }> = ({ items, color = NAV }) => (
  <ul className="space-y-1.5 list-disc list-inside pl-1 text-xs" style={{ color }}>
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

// ── Agent 5 Result ────────────────────────────────────────────────────────────
const Agent5Result: React.FC<{ output: any; storyId?: string }> = ({ output, storyId }) => {
  const [downloading, setDownloading] = useState(false)

  const report          = output?.report || output || {}
  const reportTitle     = report.report_title    || report.title    || ''
  const reportStoryId   = report.story_id        || storyId        || ''
  const version         = report.version         || ''
  const timestamp       = report.timestamp       || ''
  const globalStatus    = report.global_status   || report.status  || ''
  const findings        = report.key_findings    || report.findings || []
  const nextSteps       = report.next_steps      || []
  const storySynth      = report.story_synthesis || report.story_synth || {}
  const testSuite       = report.test_suite      || report.tests   || {}
  const coverage        = report.coverage        || report.coverage_metrics || {}
  const validation      = report.validation      || report.quality  || {}
  const recommendations = report.recommendations || []
  const pipeline        = report.pipeline_notes  || report.pipeline || {}

  const handleDownloadMarkdown = async () => {
    setDownloading(true)
    try {
      // placeholder — ajoute ta logique ici si besoin
    } finally {
      setDownloading(false)
    }
  }

  const handleDownloadPdf = () => {
    const printWindow = window.open('', '_blank')
    if (!printWindow) return

    const findingsHtml   = findings.map((f: string) => `<li>${f}</li>`).join('')
    const nextStepsHtml  = nextSteps.map((s: string) => `<li>${s}</li>`).join('')

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
      const action   = rec.action   || rec.text || 'Recommandation'
      const rationale = rec.rationale || rec.description || ''
      return `
        <div class="recommendation-card">
          <div class="rec-header">[${priority.toUpperCase()}] ${action}</div>
          <div class="rec-body">${rationale}</div>
        </div>
      `
    }).join('')

    const pipelineHtml = Array.isArray(pipeline)
      ? pipeline.map((p: string) => `<li>${p}</li>`).join('')
      : Object.entries(pipeline).map(([k, v]) => `<li><strong>${k}</strong> : ${v}</li>`).join('')

    const html = `
      <!DOCTYPE html>
      <html>
      <head>
        <title>Agent Test — Rapport QA · ${reportStoryId}</title>
        <style>
          @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&display=swap');
          body { font-family: 'Outfit', 'Segoe UI', system-ui, -apple-system, sans-serif; color: #0B1E3E; margin: 40px; line-height: 1.6; }
          .header { font-size: 11px; color: #64748b; margin-bottom: 20px; display: flex; justify-content: space-between; }
          .title { font-size: 26px; font-weight: 800; color: #1D4ED8; border-bottom: 2px solid #1D4ED8; padding-bottom: 10px; margin-bottom: 30px; }
          h2 { font-size: 16px; font-weight: 800; color: #0B1E3E; margin-top: 30px; margin-bottom: 15px; border-bottom: 1px solid #e2e8f0; padding-bottom: 5px; }
          h3 { font-size: 13px; font-weight: 700; margin-top: 20px; margin-bottom: 10px; color: #1A3A6B; }
          .status-badge { display: inline-block; padding: 4px 12px; border-radius: 9999px; font-size: 12px; font-weight: 700; background: rgba(234,88,12,0.1); color: #EA580C; border: 1px solid rgba(234,88,12,0.3); margin-left: 10px; }
          ul { padding-left: 20px; margin-bottom: 20px; }
          li { margin-bottom: 6px; font-size: 13px; }
          table { width: 100%; border-collapse: collapse; margin-bottom: 25px; font-size: 13px; border: 1px solid #e2e8f0; }
          th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #e2e8f0; }
          th { background-color: #0B1E3E; color: white; font-weight: 700; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; }
          td.prop-name { font-weight: 700; background-color: #f8fafc; width: 30%; color: #64748b; }
          .recommendation-card { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; margin-bottom: 12px; }
          .rec-header { font-weight: 800; font-size: 11px; color: #EA580C; margin-bottom: 4px; }
          .rec-body { font-size: 13px; }
          .footer { margin-top: 50px; border-top: 1px solid #e2e8f0; padding-top: 15px; font-size: 11px; color: #64748b; display: flex; justify-content: space-between; }
          @media print { body { margin: 20px; } }
        </style>
      </head>
      <body>
        <div class="header"><span>Agent Test — Rapport QA · ${reportStoryId}</span></div>
        <div class="title">${reportTitle || `Rapport QA Complet — ${reportStoryId}`}</div>

        <h2>■ Résumé Exécutif</h2>
        <p><strong>Statut Global :</strong> <span class="status-badge">${globalStatus || 'APPROVED'}</span></p>
        <h3>Findings Principaux</h3>
        <ul>${findingsHtml || '<li>Aucun finding disponible</li>'}</ul>
        <h3>Prochaines Étapes</h3>
        <ul>${nextStepsHtml || '<li>Aucune étape recommandée</li>'}</ul>

        <h2>■ Synthèse User Story</h2>
        <table>
          <tr><td class="prop-name">ID</td><td><strong>${reportStoryId || '—'}</strong></td></tr>
          <tr><td class="prop-name">Titre</td><td>${storySynth.story_title || storySynth.title || '—'}</td></tr>
          <tr><td class="prop-name">Type</td><td>${storySynth.story_type  || storySynth.type  || '—'}</td></tr>
        </table>
        <p><strong>Acteurs :</strong> ${storySynth.actors?.length > 0 ? storySynth.actors.join(', ') : 'N/A'}</p>
        <p><strong>Règles Métier :</strong> ${storySynth.business_rules?.length > 0 ? storySynth.business_rules.join('. ') : 'Aucune'}</p>
        <p><strong>Périmètre Technique :</strong> ${storySynth.technical_scope?.length > 0 ? storySynth.technical_scope.join(', ') : 'N/A'}</p>

        <h2>■ Suite de Tests Générée</h2>
        <ul>
          <li><strong>Total :</strong> ${testSuite.total_tests ?? 0} cas de test</li>
          <li><strong>NOM (Nominal) :</strong> ${testSuite.nom_count ?? 0}</li>
          <li><strong>ALT (Alternatif) :</strong> ${testSuite.alt_count ?? 0}</li>
          <li><strong>EXC (Exception) :</strong> ${testSuite.exc_count ?? 0}</li>
          <li><strong>Priorités Haute :</strong> ${testSuite.high_priority_count ?? 0}</li>
        </ul>
        <h3>Tests (résumé)</h3>
        <table>
          <thead><tr><th>Type</th><th>Nom</th><th>Priorité</th><th>Étapes</th></tr></thead>
          <tbody>${testSuiteHtml || '<tr><td colspan="4">Aucun test généré</td></tr>'}</tbody>
        </table>

        <h2>■ Métriques de Couverture</h2>
        <ul>
          <li><strong>Taux :</strong> ${coverage.coverage_rate !== undefined ? coverage.coverage_rate + '%' : '0%'}</li>
          <li><strong>Statut :</strong> ${coverage.coverage_status || 'EXCELLENT'}</li>
          <li><strong>Points Non Couverts :</strong> ${coverage.uncovered_points?.length > 0 ? coverage.uncovered_points.join(', ') : 'Aucun'}</li>
        </ul>

        <h2>■ Validation & Assurance Qualité</h2>
        <p><strong>Statut Validation :</strong> <span class="status-badge">${validation.validation_status || 'VALID'}</span></p>
        <ul>
          <li><strong>Doublons détectés :</strong> ${validation.duplicate_pairs ?? 0}</li>
          <li><strong>Ambiguïtés détectées :</strong> ${validation.ambiguity_count ?? 0}</li>
        </ul>
        <h3>Issues Détectées</h3>
        <p>${(validation.issues || []).length === 0
          ? 'Aucune issue détectée ■'
          : (validation.issues || []).map((i: any) => `• [${i.severity}] ${i.description}`).join('<br>')
        }</p>
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
        <script>window.onload = function() { window.print(); }</script>
      </body>
      </html>
    `
    printWindow.document.write(html)
    printWindow.document.close()
  }

  return (
    <div className="w-full space-y-8 text-slate-900">
      {/* Header card */}
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
              {version   && <span className="px-3 py-1 rounded-full text-xs font-bold text-white/70 bg-white/10">v{version}</span>}
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
        <ReportSection icon="■" title="Suite de Tests Générée">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4">
            {[
              { label: 'Total', value: testSuite.total_tests ?? testSuite.total },
              { label: 'NOM',   value: testSuite.nom_count   ?? testSuite.nom   },
              { label: 'ALT',   value: testSuite.alt_count   ?? testSuite.alt   },
              { label: 'EXC',   value: testSuite.exc_count   ?? testSuite.exc   },
            ].filter(r => r.value !== undefined).map((item, i) => (
              <div key={i} className="rounded-xl p-3 bg-slate-50 border text-center">
                <p className="text-xl font-extrabold" style={{ color: NAV }}>{item.value}</p>
                <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mt-0.5">{item.label}</p>
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
                        {t.step_count !== undefined
                          ? `${t.step_count} étapes`
                          : t.steps_count !== undefined
                          ? `${t.steps_count} étapes`
                          : t.steps
                          ? `${t.steps} étapes`
                          : '—'}
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
            {[
              ['Statut Couverture',    coverage.coverage_status || coverage.statut],
              ['Points testables',     coverage.total_testable_points ?? coverage.total_points],
              ['Points couverts',      coverage.covered_points ?? coverage.points_couverts],
              ['Points non couverts',  Array.isArray(coverage.uncovered_points)
                ? (coverage.uncovered_points.length === 0 ? 'Aucun' : `${coverage.uncovered_points.length} point(s)`)
                : coverage.uncovered_points_count ?? '—'],
            ].filter(([, v]) => v !== undefined && v !== '—').map(([label, value], i) => (
              <div key={i} className="flex items-center gap-4">
                <span className="text-sm font-semibold w-44 flex-shrink-0" style={{ color: `${NAV}70` }}>{label} :</span>
                <span className="text-sm font-bold" style={{ color: NAV }}>{String(value)}</span>
              </div>
            ))}
          </div>
        </ReportSection>
      )}

      {Object.keys(validation).length > 0 && (
        <ReportSection icon="■" title="Validation & Assurance Qualité">
          <div className="space-y-3">
            {[
              ['Statut Validation',    validation.validation_status || validation.status || validation.statut],
              ['Doublons détectés',    validation.duplicate_pairs   ?? validation.duplicates ?? validation.doublons],
              ['Ambiguïtés détectées', validation.ambiguity_count   ?? validation.ambiguities ?? validation.ambiguites],
              ['Score LLM',           validation.llm_quality_score !== undefined ? `${validation.llm_quality_score}/10` : undefined],
            ].filter(([, v]) => v !== undefined).map(([label, value], i) => (
              <div key={i} className="flex items-center gap-4">
                <span className="text-sm font-semibold w-44 flex-shrink-0" style={{ color: `${NAV}70` }}>{label} :</span>
                <span className="text-sm font-bold" style={{ color: NAV }}>{String(value)}</span>
              </div>
            ))}
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

      <div className="flex items-center justify-between pt-4 border-t text-xs text-slate-400">
        <span>Rapport d'historique</span>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleDownloadMarkdown}
            disabled={downloading}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-bold text-white transition-all hover:-translate-y-0.5 disabled:opacity-50"
            style={{ background: CARD_GRADIENT }}>
            {downloading ? 'Génération...' : 'Télécharger .md'}
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

// ── Agent 1.5 Result — Business Modeling ──────────────────────────────────────
const Agent15Result: React.FC<{ output: any }> = ({ output }) => {
  const bm        = output?.business_model || output || {}
  const goals     = bm.business_goals     || []
  const workflows = bm.business_workflows || []
  const notes     = bm.modeling_notes     || ''

  if (!goals.length && !workflows.length) return (
    <div className="py-12 text-center space-y-2">
      <GitBranch size={32} className="mx-auto opacity-20" style={{ color: NAV }} />
      <p className="text-sm font-medium" style={{ color: `${NAV}60` }}>Aucun modèle métier généré</p>
      {notes && <p className="text-xs mt-1" style={{ color: `${NAV}40` }}>{notes}</p>}
    </div>
  )

  const BM_BLUE   = '#1e40af'
  const BM_INDIGO = '#4338ca'
  const BM_SLATE  = '#475569'

  return (
    <div className="space-y-6 w-full">
      {/* Stats KPI row */}
      <div className="grid grid-cols-2 gap-4">
        <div className="rounded-2xl p-5 text-center" style={{
          background: 'linear-gradient(135deg,#1e40af,#2563eb)',
          boxShadow: '0 4px 16px rgba(37,99,235,0.25)'
        }}>
          <p className="text-3xl font-extrabold text-white">{goals.length}</p>
          <p className="text-xs font-bold uppercase tracking-widest mt-1 text-white/70">Business Goals</p>
        </div>
        <div className="rounded-2xl p-5 text-center" style={{
          background: 'linear-gradient(135deg,#0f172a,#1e293b)',
          boxShadow: '0 4px 16px rgba(15,23,42,0.25)'
        }}>
          <p className="text-3xl font-extrabold text-white">{workflows.length}</p>
          <p className="text-xs font-bold uppercase tracking-widest mt-1 text-white/70">Workflows</p>
        </div>
      </div>

      {/* Business Goals */}
      {goals.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <div className="w-1 h-5 rounded-full" style={{ background: `linear-gradient(180deg,${BM_BLUE},${BM_INDIGO})` }} />
            <p className="text-sm font-extrabold uppercase tracking-widest" style={{ color: NAV }}>Business Goals</p>
          </div>
          {goals.map((g: any, i: number) => (
            <div key={i} className="rounded-2xl p-4 border space-y-2" style={{
              borderColor: 'rgba(30,64,175,0.15)',
              background: 'rgba(30,64,175,0.03)',
            }}>
              <div className="flex items-center gap-3 flex-wrap">
                <span className="px-2.5 py-0.5 rounded-lg text-[10px] font-extrabold uppercase text-white"
                  style={{ background: BM_BLUE }}>{g.id}</span>
                <span className="font-bold text-sm flex-1" style={{ color: NAV }}>{g.label}</span>
                {g.priority && (
                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase"
                    style={{
                      background: g.priority === 'haute' ? 'rgba(220,38,38,0.1)' : g.priority === 'basse' ? 'rgba(100,116,139,0.1)' : 'rgba(37,99,235,0.1)',
                      color:      g.priority === 'haute' ? '#dc2626'             : g.priority === 'basse' ? BM_SLATE                : BM_BLUE,
                      border:     `1px solid ${g.priority === 'haute' ? 'rgba(220,38,38,0.2)' : g.priority === 'basse' ? 'rgba(100,116,139,0.2)' : 'rgba(37,99,235,0.2)'}`,
                    }}>{g.priority}</span>
                )}
              </div>
              {g.description && <p className="text-xs leading-relaxed" style={{ color: `${NAV}70` }}>{g.description}</p>}
              {g.actors?.length > 0 && (
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {g.actors.map((a: string, j: number) => (
                    <span key={j} className="px-2.5 py-0.5 rounded-lg text-xs font-semibold"
                      style={{ background: 'rgba(30,64,175,0.08)', color: BM_BLUE, border: '1px solid rgba(30,64,175,0.15)' }}>{a}</span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Business Workflows */}
      {workflows.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <div className="w-1 h-5 rounded-full" style={{ background: `linear-gradient(180deg,#0f172a,#1e293b)` }} />
            <p className="text-sm font-extrabold uppercase tracking-widest" style={{ color: NAV }}>Business Workflows</p>
          </div>
          {workflows.map((w: any, i: number) => (
            <details key={i} className="rounded-2xl border overflow-hidden group" style={{ borderColor: 'rgba(15,23,42,0.12)' }}>
              <summary className="flex items-center gap-3 p-4 cursor-pointer list-none select-none hover:bg-slate-50 transition">
                <span className="px-2.5 py-0.5 rounded-lg text-[10px] font-extrabold uppercase text-white"
                  style={{ background: 'linear-gradient(135deg,#0f172a,#1e293b)' }}>{w.id}</span>
                <span className="font-bold text-sm flex-1" style={{ color: NAV }}>{w.label}</span>
                {w.linked_goal_id && (
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full"
                    style={{ background: 'rgba(30,64,175,0.1)', color: BM_BLUE, border: '1px solid rgba(30,64,175,0.2)' }}>→ {w.linked_goal_id}</span>
                )}
                <ChevronDown size={14} className="text-slate-400 group-open:rotate-180 transition-transform" />
              </summary>
              <div className="px-4 pb-4 space-y-4 border-t bg-slate-50/80" style={{ borderColor: 'rgba(15,23,42,0.06)' }}>
                {w.trigger && (
                  <div className="pt-3">
                    <p className="text-[10px] font-bold uppercase tracking-widest mb-1" style={{ color: `${NAV}50` }}>Déclencheur</p>
                    <p className="text-xs" style={{ color: `${NAV}80` }}>{w.trigger}</p>
                  </div>
                )}
                {w.steps?.length > 0 && (
                  <div>
                    <p className="text-[10px] font-bold uppercase tracking-widest mb-2" style={{ color: `${NAV}50` }}>Étapes ({w.steps.length})</p>
                    <ol className="space-y-1.5">
                      {w.steps.map((s: string, j: number) => (
                        <li key={j} className="flex gap-2 items-start text-xs" style={{ color: `${NAV}80` }}>
                          <span className="w-5 h-5 flex-shrink-0 rounded-full flex items-center justify-center font-bold text-[10px] text-white"
                            style={{ background: BM_BLUE }}>{j + 1}</span>
                          <span>{s}</span>
                        </li>
                      ))}
                    </ol>
                  </div>
                )}
                {w.success_criteria?.length > 0 && (
                  <div>
                    <p className="text-[10px] font-bold uppercase tracking-widest mb-2" style={{ color: `${NAV}50` }}>Critères de succès</p>
                    <ul className="space-y-1">
                      {w.success_criteria.map((c: string, j: number) => (
                        <li key={j} className="flex gap-2 items-start text-xs">
                          <span style={{ color: '#059669' }}>✓</span>
                          <span style={{ color: `${NAV}70` }}>{c}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </details>
          ))}
        </div>
      )}

      {notes && <p className="text-xs italic border-t pt-3 mt-2" style={{ color: `${NAV}40` }}>{notes}</p>}
    </div>
  )
}

// ── Agent Rich Output Dispatcher ──────────────────────────────────────────────
const AgentRichOutput: React.FC<{ agentKey: string; output: any; storyId?: string }> = ({ agentKey, output, storyId }) => {
  if (!output) return null
  if (agentKey === 'Agent 1')   return <Agent1Result output={output} />
  if (agentKey === 'Agent 1.5') return <Agent15Result output={output} />
  if (agentKey === 'Agent 2')   return <Agent2Result output={output} storyId={storyId} />
  if (agentKey === 'Agent 3')   return <Agent3Result output={output} />
  if (agentKey === 'Agent 5')   return <Agent5Result output={output} storyId={storyId} />
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
          <SectionTitle>Données JSON — Historique</SectionTitle>

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