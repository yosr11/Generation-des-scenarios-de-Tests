import React, { useState, useCallback } from 'react'
import { Pencil, Upload, ChevronRight, X } from 'lucide-react'
import { Badge } from '../ui/Badge'
import { apiClient } from '../../api/client'
import { useToast } from '../../contexts/ToastContext'
import { useAuth, JiraProject } from '../../contexts/AuthContext'
import { ProjectPicker } from '../projects/ProjectPicker'
import { XrayTestView } from './XrayTestView'

/* ── types ── */
const ROSE      = '#f43f5e'
const NAV        = '#121b53'
const RED       = '#e70f16'
const BUTTON_GRADIENT = `linear-gradient(90deg, #4338ca, ${ROSE})`
const ICON_GRADIENT = `linear-gradient(135deg, #051268, #1a2060)`
interface ManualTestsTableProps {
  tests: any[]
  storyId?: string
  onTestsChange?: (tests: any[]) => void
  expandable?: boolean
  showProjectPicker?: boolean
  defaultExpandedIndex?: number | null
}

export interface IntegrationResult {
  status: string
  created_count: number
  created_keys: string[]
  jira_browse_base_url?: string
  errors: string[]
  test_name?: string
}

const JIRA_SUMMARY_MAX = 255

function truncateSummary(name: string): string {
  if (name.length <= JIRA_SUMMARY_MAX) return name
  return name.slice(0, JIRA_SUMMARY_MAX - 1) + '…'
}

function buildPayload(test: any, storyId?: string) {
  const groupedEtapes = Array.isArray(test.étapes) && test.étapes.length
    ? test.étapes
    : Array.isArray(test.etapes) && test.etapes.length
    ? test.etapes
    : []
  const flatSteps = groupedEtapes.length
    ? groupedEtapes.flatMap((e: any) =>
        (e.steps || []).map((s: any) => ({
          action: s.action || e.titre || '',
          expected_result: s.expected_result || '',
          data: s.data || e.data || '',
          actor: s.actor || e.actor || '',
        }))
      )
    : (test.steps || [])

  const rawName = test.test_name || test.title || 'Untitled'
  const test_name = truncateSummary(rawName)

  return {
    test_name,
    story_key: storyId || undefined,
    objective: test.objective || rawName,
    scenario_type: test.scenario_type,
    priority: test.priority || test.priorite || undefined,
    preconditions: Array.isArray(test.preconditions) ? test.preconditions : [],
    étapes: groupedEtapes.length ? groupedEtapes : undefined,
    steps: flatSteps.map((s: any) => ({
      action: s.action || '',
      expected_result: s.expected_result || s.result || '',
      data: s.data || '',
      actor: s.actor || '',
    })),
  }
}

/* ──────────────────────────────────────────────────────
   Test Edit Drawer
────────────────────────────────────────────────────── */
const CARD_GRADIENT = 'linear-gradient(135deg, #0B1E3E, #1A3A6B, #1D4ED8)'

const TestEditDrawer: React.FC<{
  test: any
  storyId: string
  allTests: any[]
  editingIndex: number
  onClose: () => void
  onSaved: (t: any) => void
}> = ({ test, storyId, allTests, editingIndex, onClose, onSaved }) => {
  const [editedTest, setEditedTest] = useState<any>(test)
  const [message, setMessage] = useState('')
  const [chatHistory, setChatHistory] = useState<{ role: string; content: string }[]>([])
  const [aiReply, setAiReply] = useState<string | null>(null)
  const [refining, setRefining] = useState(false)
  const [openedGroup, setOpenedGroup] = useState<number | null>(null)
  const [saving, setSaving] = useState(false)
  const toast = useToast()

  const updateGroupTitre = (groupIndex: number, value: string) => {
    setEditedTest((prev: any) => {
      const next = { ...prev }
      if (Array.isArray(next.étapes)) {
        next.étapes = next.étapes.map((g: any, idx: number) =>
          idx === groupIndex ? { ...g, titre: value } : g
        )
      }
      return next
    })
  }

  const updateGroupActor = (groupIndex: number, value: string) => {
    setEditedTest((prev: any) => {
      const next = { ...prev }
      if (Array.isArray(next.étapes)) {
        next.étapes = next.étapes.map((g: any, idx: number) =>
          idx === groupIndex ? { ...g, actor: value } : g
        )
      }
      return next
    })
  }

  const updateGroupField = (groupIndex: number, field: string, value: string) => {
    setEditedTest((prev: any) => {
      const next = { ...prev }
      if (Array.isArray(next.étapes)) {
        next.étapes = next.étapes.map((g: any, idx: number) =>
          idx === groupIndex ? { ...g, [field]: value } : g
        )
      }
      return next
    })
  }

  const getGroupDataValue = (group: any) => {
    if (group.data) return group.data
    if (!Array.isArray(group.steps)) return ''
    const values = group.steps
      .map((s: any) => (s.data || '').trim())
      .filter(Boolean)
    return Array.from(new Set(values)).join('\n')
  }

  const updateSubStepField = (groupIndex: number, stepIndex: number, field: string, value: string) => {
    setEditedTest((prev: any) => {
      const next = { ...prev }
      if (Array.isArray(next.étapes)) {
        next.étapes = next.étapes.map((g: any, gIdx: number) => {
          if (gIdx !== groupIndex) return g
          const newSteps = (g.steps || []).map((s: any, sIdx: number) =>
            sIdx === stepIndex ? { ...s, [field]: value } : s
          )
          return { ...g, steps: newSteps }
        })
        next.steps = next.étapes.flatMap((g: any) => g.steps || [])
      }
      return next
    })
  }

  const updatePrecondition = (preIndex: number, value: string) => {
    setEditedTest((prev: any) => {
      const next = { ...prev }
      const preconditions = Array.isArray(next.preconditions) ? [...next.preconditions] : []
      preconditions[preIndex] = value
      next.preconditions = preconditions
      return next
    })
  }

  const addPrecondition = () => {
    setEditedTest((prev: any) => {
      const next = { ...prev }
      next.preconditions = Array.isArray(next.preconditions)
        ? [...next.preconditions, '']
        : ['']
      return next
    })
  }

  const removePrecondition = (preIndex: number) => {
    setEditedTest((prev: any) => {
      const next = { ...prev }
      if (!Array.isArray(next.preconditions)) return next
      next.preconditions = next.preconditions.filter((_: any, idx: number) => idx !== preIndex)
      return next
    })
  }

  const updateFlatStepField = (stepIndex: number, field: string, value: string) => {
    setEditedTest((prev: any) => {
      const next = { ...prev }
      next.steps = (next.steps || []).map((s: any, idx: number) =>
        idx === stepIndex ? { ...s, [field]: value } : s
      )
      return next
    })
  }

  const handleRefine = useCallback(
    async (e: React.MouseEvent) => {
      e.preventDefault()
      e.stopPropagation()
      if (!message.trim()) return
      setRefining(true)
      setAiReply(null)
      try {
        const resp = await apiClient.testEditing.refineChat({
          test: editedTest,
          message: message.trim(),
          chat_history: chatHistory,
          story_id: storyId,
        })
        setEditedTest(resp.test)
        setAiReply(resp.assistant_message)
        setChatHistory((prev) => [
          ...prev,
          { role: 'user', content: message.trim() },
          { role: 'assistant', content: resp.assistant_message },
        ])
        setMessage('')
        toast.success('Test affiné !')
      } catch (err: any) {
        toast.error(err?.message || 'Échec du raffinement')
      } finally {
        setRefining(false)
      }
    },
    [message, editedTest, chatHistory, storyId, toast]
  )

  const handleSave = useCallback(
    async (e: React.MouseEvent) => {
      e.preventDefault()
      e.stopPropagation()
      setSaving(true)
      try {
        // On persiste la LISTE COMPLÈTE des tests (avec l'édition fusionnée),
        // pas seulement le test édité — sinon le snapshot backend écrase tous
        // les autres tests et l'historique n'en affiche plus qu'un seul.
        const fullList = allTests.map((t, i) => (i === editingIndex ? editedTest : t))
        await apiClient.testEditing.saveEdited(storyId, fullList)
        onSaved(editedTest)
        toast.success('Test sauvegardé !')
      } catch (err: any) {
        toast.error(err?.message || 'Échec de la sauvegarde')
      } finally {
        setSaving(false)
      }
    },
    [editedTest, storyId, allTests, editingIndex, onSaved, toast]
  )

  return (
    <div
      className="fixed inset-0 z-[9999]"
      onClick={(e) => { e.preventDefault(); e.stopPropagation() }}
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-brand-navy/50 backdrop-blur-sm"
        onClick={(e) => { e.preventDefault(); e.stopPropagation(); onClose() }}
      />

      {/* Drawer */}
      <aside
        className="absolute top-0 right-0 h-full w-full max-w-lg bg-white flex flex-col shadow-float"
        style={{ zIndex: 1 }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="syn-strip" />

        {/* Header */}
        <div className="px-5 py-4 flex items-center gap-3 border-b border-brand-navy/[0.06] bg-brand-offwhite/50">
          <div className="flex-1 min-w-0">
            <p className="syn-label mb-1">Éditer le test</p>
            <input
              className="font-bold text-brand-navy text-sm w-full bg-transparent border-0 border-b border-brand-navy/10 pb-1 focus:border-brand-violet focus:outline-none placeholder:text-brand-muted"
              value={editedTest?.test_name || editedTest?.title || ''}
              placeholder="Nom du test"
              onChange={(e) =>
                setEditedTest({ ...editedTest, test_name: e.target.value, title: e.target.value })
              }
              onClick={(e) => e.stopPropagation()}
            />
          </div>
          <button
            type="button"
            onClick={(e) => { e.preventDefault(); e.stopPropagation(); onClose() }}
            className="p-2 rounded-lg text-brand-muted hover:text-brand-navy hover:bg-brand-navy/5 transition-all flex-shrink-0"
          >
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-5 space-y-5 bg-white">

          {/* Affiner avec l'IA — en haut */}
          <section className="rounded-xl border border-brand-red/15 bg-brand-red/[0.03] p-4">
            <p className="syn-label text-brand-red mb-2">Affiner avec l'IA</p>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onClick={(e) => e.stopPropagation()}
              rows={2}
              placeholder="Ex. : Ajouter une étape pour vérifier le message d'erreur…"
              className="w-full px-3 py-2.5 rounded-lg text-sm resize-none text-brand-navy placeholder:text-brand-muted/60 bg-white border border-brand-navy/[0.08] focus:border-brand-violet focus:outline-none focus:ring-2 focus:ring-brand-violet/10"
            />
            <div className="flex justify-end mt-2">
              <button
  type="button"
  onClick={handleRefine}
  disabled={refining || !message.trim()}
  className="syn-btn-xray !text-xs !py-2 !px-4 !text-white !font-bold"
  style={{
    background: BUTTON_GRADIENT,
    border: "none",
    boxShadow: "0 4px 18px rgba(219,39,119,0.38)",
  }}
>
  {refining ? (
    <>
      <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
      Affinement…
    </>
  ) : (
    "Affiner"
  )}
</button>
            </div>
            {aiReply && (
              <div className="mt-3 pt-3 border-t border-brand-violet/10">
                <p className="syn-label mb-1.5">Réponse IA</p>
                <p className="text-sm text-brand-navy leading-relaxed">{aiReply}</p>
              </div>
            )}
          </section>

          {/* Objectif */}
          <section>
            <div className="flex items-center gap-2">
            <div className="w-1 h-4 rounded-full" style={{ background: 'linear-gradient(135deg, #0B1E3E, #1E3A8A)' }} />
            <p className="text-sm font-extrabold uppercase tracking-widest text-brand-navy font-sans">Objectif</p>
            </div>
            <textarea
              className="w-full text-sm text-brand-navy leading-relaxed rounded-lg px-3 py-2.5 border border-brand-navy/[0.08] bg-brand-offwhite/30 focus:border-brand-violet focus:outline-none focus:ring-2 focus:ring-brand-violet/10 resize-none"
              value={editedTest?.objective || ''}
              placeholder="Objectif du test…"
              onChange={(e) => setEditedTest({ ...editedTest, objective: e.target.value })}
              onClick={(e) => e.stopPropagation()}
              rows={2}
            />
          </section>

          {/* Préconditions */}
          <section className="space-y-3">
            <div className="flex items-center gap-2">
              <div className="w-1 h-4 rounded-full" style={{ background: 'linear-gradient(135deg, #0B1E3E, #1E3A8A)' }} />
              <p className="text-sm font-extrabold uppercase tracking-widest text-brand-navy font-sans">Préconditions</p>
            </div>
            {Array.isArray(editedTest?.preconditions) && editedTest.preconditions.length > 0 ? (
              <div className="space-y-3">
                {editedTest.preconditions.map((pre: string, pi: number) => (
                  <div key={pi} className="grid gap-2 items-center sm:grid-cols-[auto_1fr_auto]">
                    <span
                      className="w-5 h-5 rounded-md flex items-center justify-center text-[10px] font-extrabold text-white"
                      style={{ background: 'linear-gradient(135deg, #0B1E3E, #1E3A8A)' }}
                    >
                      {pi + 1}
                    </span>
                    <input
                      className="w-full text-sm text-brand-navy rounded-xl px-3 py-2 border border-brand-navy/[0.08] bg-white focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/10 transition-all font-sans"
                      value={pre}
                      onChange={(e) => updatePrecondition(pi, e.target.value)}
                      onClick={(e) => e.stopPropagation()}
                      placeholder="Précondition…"
                    />
                    <button
                      type="button"
                      onClick={(e) => { e.preventDefault(); e.stopPropagation(); removePrecondition(pi) }}
                      className="rounded-xl border border-brand-navy/10 px-3 text-sm text-brand-rose hover:bg-brand-rose/10 transition"
                    >
                      Supprimer
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-brand-muted">Aucune précondition définie.</p>
            )}
            <button
              type="button"
              onClick={(e) => { e.preventDefault(); e.stopPropagation(); addPrecondition() }}
              className="inline-flex items-center gap-2 rounded-xl bg-brand-offwhite px-3 py-2 text-sm font-semibold text-brand-navy hover:bg-brand-navy/5 transition"
            >
              + Ajouter une précondition
            </button>
          </section>

          {/* Étapes groupées (Xray / normal format) */}
          {Array.isArray(editedTest?.étapes) && editedTest.étapes.length > 0 ? (
            <section className="space-y-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="w-1 h-4 rounded-full" style={{ background: 'linear-gradient(135deg, #0B1E3E, #1E3A8A)' }} />
                  <p className="text-sm font-extrabold uppercase tracking-widest text-brand-navy font-sans">Étapes </p>
                </div>
                <span className="px-2 py-0.5 rounded-full text-xs font-bold font-sans"
                  style={{ background: 'rgba(22, 46, 123, 0.1)', color: '#0b182e' }}>
                  {editedTest.étapes.length}
                </span>
              </div>

              <div className="space-y-4">
                {editedTest.étapes.map((group: any, gi: number) => {

                  const opened = openedGroup === gi
                  const preCount = Array.isArray(editedTest?.preconditions) ? editedTest.preconditions.length : 0
                  const stepNumber = gi + 1 + preCount

                  return (

                  <div
                    key={gi}
                    className="rounded-2xl border overflow-hidden"
                    style={{ borderColor: 'rgba(5, 19, 65, 0.2)', background: 'rgba(12, 24, 63, 0.01)' }}
                  >
                    {/* Group Header */}
                    <button
    type="button"
    onClick={() =>
        setOpenedGroup(opened ? null : gi)
    }
    className="w-full px-4 py-3 flex items-center justify-between"
    style={{
        background:'rgba(19, 37, 98, 0.06)',
        borderBottom:'1px solid rgba(27, 43, 94, 0.12)'
    }}
>

    <div className="flex items-center gap-2">

        <span
            className="w-5 h-5 rounded-md flex items-center justify-center text-[10px] font-extrabold text-white"
            style={{
                background:'linear-gradient(135deg, #0B1E3E, #1E3A8A)'
            }}
        >
            {stepNumber}
        </span>

        <span className="text-xs font-extrabold text-brand-navy uppercase tracking-wider">
            {group.titre || `Étape ${stepNumber}`}
        </span>

    </div>

    <ChevronRight
        size={18}
        className={`transition-transform ${
            opened ? 'rotate-90' : ''
        }`}
    />

</button>
                  {opened && (
                    <div className="p-4 space-y-4">
                      {/* Group Title (main action) */}
                      <div>
                        <p className="text-[10px] font-extrabold uppercase tracking-widest mb-1.5 font-sans" style={{ color: '#ad1406'  }}>
                          Titre de l'étape (Action principale)
                        </p>
                        <input
                          className="w-full text-sm font-semibold text-brand-navy rounded-xl px-3 py-2.5 border border-brand-navy/[0.12] bg-white focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/10 transition-all font-sans"
                          value={group.titre || ''}
                          onChange={(e) => updateGroupTitre(gi, e.target.value)}
                          onClick={(e) => e.stopPropagation()}
                          placeholder="ex : Se connecter en tant que Collaborateur…"
                        />
                      </div>
                       
                      {/* Group Actor */}
                      <div>
                        <p className="text-[10px] font-extrabold uppercase tracking-widest mb-1.5 font-sans" style={{ color: '#102b75'}}>
                          Acteur
                        </p>
                        <input
                          className="w-full text-xs text-brand-navy rounded-xl px-3 py-2 border border-brand-navy/[0.1] bg-white focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-500/10 transition-all font-sans"
                          value={group.actor || ''}
                          onChange={(e) => updateGroupActor(gi, e.target.value)}
                          onClick={(e) => e.stopPropagation()}
                          placeholder="ex : Collaborateur, Manager…"
                        />
                      </div>

                      {/* Group Data */}
                      <div>
                        <p className="text-[10px] font-extrabold uppercase tracking-widest mb-1.5 font-sans" style={{ color: '#102b75' }}>
                          Données de l'étape
                        </p>
                        <input
                          className="w-full text-xs text-brand-navy rounded-xl px-3 py-2 border border-brand-navy/[0.1] bg-white focus:border-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-500/10 transition-all font-sans"
                          value={getGroupDataValue(group)}
                          onChange={(e) => updateGroupField(gi, 'data', e.target.value)}
                          onClick={(e) => e.stopPropagation()}
                          placeholder="Donnée unique pour cette étape…"
                        />
                      </div>

                      {/* Sub-steps of this group */}
                      {Array.isArray(group.steps) && group.steps.length > 0 && (
                        <div className="space-y-3 pt-2 border-t border-dashed border-brand-navy/10">
                          <p className="text-[10px] font-extrabold uppercase tracking-widest text-brand-navy/50 font-sans"style={{ color: '#a70909'  }}>
                            Actions & Résultats détaillés
                          </p>
                          {group.steps.map((subStep: any, si: number) => (
                            <div key={si} className="p-4 rounded-xl bg-white border border-brand-violet/[10] space-y-3">
                              {/* SubStep Action */}
                              <div>
                                <p className="text-[10px] font-extrabold uppercase tracking-widest mb-1.5 font-sans"style={{ color: '#102b75' }}>
                                  Action détaillée
                                </p>
                                <input
                                  className="w-full text-xs text-brand-navy rounded-lg px-2.5 py-2 border border-brand-navy/[0.08] bg-slate-50/50 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 font-sans"
                                  value={subStep.action || ''}
                                  onChange={(e) => updateSubStepField(gi, si, 'action', e.target.value)}
                                  onClick={(e) => e.stopPropagation()}
                                  placeholder="Action détaillée…"
                                />
                              </div>

                              {/* SubStep Expected Result */}
                              <div>
                                <p className="text-[10px] font-extrabold uppercase tracking-widest mb-1.5 font-sans"style={{ color: '#102b75' }}>
                                  Résultat attendu
                                </p>
                                <textarea
                                  className="w-full text-xs text-brand-navy rounded-lg px-2.5 py-2 border border-brand-navy/[0.08] bg-slate-50/50 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500 font-sans resize-y leading-relaxed"
                                  value={subStep.expected_result || ''}
                                  onChange={(e) => updateSubStepField(gi, si, 'expected_result', e.target.value)}
                                  onClick={(e) => e.stopPropagation()}
                                  placeholder="Résultat attendu (une assertion par ligne)…"
                                  rows={2}
                                />
                              </div>

                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                
                  </div>
                  )
                })
              }

              </div>

            </section>
          ) : (
            /* Flat steps fallback */
            Array.isArray(editedTest?.steps) && editedTest.steps.length > 0 && (
              <section className="space-y-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className="w-1 h-4 rounded-full" style={{ background: 'linear-gradient(180deg,#1e40af,#3b82f6)' }} />
                    <p className="text-sm font-extrabold uppercase tracking-widest text-brand-navy font-sans">Étapes (Format Plat)</p>
                  </div>
                  <span className="px-2 py-0.5 rounded-full text-xs font-bold font-sans"
                    style={{ background: 'rgba(30,64,175,0.1)', color: '#1e40af' }}>
                    {editedTest.steps.length}
                  </span>
                </div>

                <div className="space-y-4">
                  {editedTest.steps.map((step: any, si: number) => {
                    const preCount = Array.isArray(editedTest?.preconditions) ? editedTest.preconditions.length : 0
                    const stepNumber = si + 1 + preCount
                    return (
                    <div
                      key={si}
                      className="rounded-2xl border overflow-hidden"
                      style={{ borderColor: 'rgba(10,22,40,0.12)', background: 'rgba(10,22,40,0.01)' }}
                    >
                      <div className="px-4 py-2.5 flex items-center gap-2"
                        style={{ background: 'rgba(10,22,40,0.04)', borderBottom: '1px solid rgba(10,22,40,0.08)' }}>
                        <span className="w-5 h-5 rounded-md flex items-center justify-center text-[10px] font-extrabold text-white flex-shrink-0"
                          style={{ background: CARD_GRADIENT }}>{stepNumber}</span>
                        <span className="text-xs font-extrabold text-brand-navy uppercase tracking-wider font-sans">Étape {stepNumber}</span>
                      </div>

                      <div className="p-4 space-y-3">
                        {/* Action */}
                        <div>
                          <p className="text-[10px] font-extrabold uppercase tracking-widest mb-1.5 font-sans" style={{ color: '#1e40af' }}>
                            Action
                          </p>
                          <input
                            className="w-full text-sm text-brand-navy rounded-xl px-3 py-2.5 border border-brand-navy/[0.12] bg-white focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/10 transition-all font-sans"
                            value={step.action || step.titre || ''}
                            onChange={(e) => updateFlatStepField(si, 'action', e.target.value)}
                            onClick={(e) => e.stopPropagation()}
                            placeholder="Action à réaliser…"
                          />
                        </div>

                        {/* Expected Result */}
                        <div>
                          <p className="text-[10px] font-extrabold uppercase tracking-widest mb-1.5 font-sans" style={{ color: '#059669' }}>
                            Résultat attendu
                          </p>
                          <textarea
                            className="w-full text-xs text-brand-navy rounded-xl px-3 py-2 border border-brand-navy/[0.1] bg-white focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/10 transition-all font-sans resize-y leading-relaxed"
                            value={step.expected_result || ''}
                            onChange={(e) => updateFlatStepField(si, 'expected_result', e.target.value)}
                            onClick={(e) => e.stopPropagation()}
                            placeholder="Résultat attendu (une assertion par ligne)…"
                            rows={3}
                          />
                        </div>

                        {/* Data */}
                        <div>
                          <p className="text-[10px] font-extrabold uppercase tracking-widest mb-1.5 font-sans" style={{ color: '#7c3aed' }}>
                            Données de test
                          </p>
                          <input
                            className="w-full text-xs text-brand-navy rounded-xl px-3 py-2 border border-brand-navy/[0.1] bg-white focus:border-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-500/10 transition-all font-sans"
                            value={step.data || ''}
                            onChange={(e) => updateFlatStepField(si, 'data', e.target.value)}
                            onClick={(e) => e.stopPropagation()}
                            placeholder="Données ou valeurs (optionnel)…"
                          />
                        </div>
                      </div>
                    </div>
                    )
                  })}
                </div>
              </section>
            )
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-4 border-t border-brand-navy/[0.06] bg-brand-offwhite/40 flex gap-3">
          <button
            type="button"
            onClick={(e) => { e.preventDefault(); e.stopPropagation(); onClose() }}
            className="flex-1 syn-btn-ghost !py-2.5 justify-center"
          >
            Annuler
          </button>
          <button
  type="button"
  onClick={handleSave}
  disabled={saving}
  className="flex-1 syn-btn-xray !py-2.5 justify-center disabled:opacity-50 !text-white !font-bold"
  style={{
    background: BUTTON_GRADIENT,
    border: "none",
    boxShadow: "0 4px 18px rgba(219,39,119,0.38)",
  }}
>
  {saving ? (
    <>
      <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
      Sauvegarde…
    </>
  ) : (
    "Sauvegarder"
  )}
</button>
        </div>

      </aside>
    </div>
  )
}

/* ──────────────────────────────────────────────────────
   Integration Result Modal
────────────────────────────────────────────────────── */
const IntegrationModal: React.FC<{
  result: IntegrationResult
  onClose: () => void
}> = ({ result, onClose }) => {
  const isSuccess = result.status === 'success' && result.errors.length === 0
  const isPartial = result.created_keys.length > 0 && result.errors.length > 0
  const successMessage =
    result.created_keys.length === 1
      ? `Le test a été intégré avec succès dans Jira sous l'ID ${result.created_keys[0]}.`
      : 'Les tests ont été intégrés avec succès dans Jira.'
  const grad = isSuccess
    ? 'linear-gradient(135deg,#10b981,#059669)'
    : isPartial
    ? 'linear-gradient(135deg,#f97316,#f59e0b)'
    : 'linear-gradient(135deg,#ef4444,#f43f5e)'

  return (
    <div
      className="fixed inset-0 z-[9999]"
      onClick={(e) => { e.preventDefault(); e.stopPropagation() }}
    >
      <div
        className="absolute inset-0 bg-brand-navy/50 backdrop-blur-sm"
        onClick={(e) => { e.preventDefault(); e.stopPropagation(); onClose() }}
      />

      <div
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-md bg-white rounded-3xl overflow-hidden"
        style={{ boxShadow: '0 25px 60px rgba(10,15,46,0.3)', zIndex: 1 }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-6 py-5 flex items-center gap-3" style={{ background: grad }}>
          <div className="w-10 h-10 rounded-xl bg-white/20 flex items-center justify-center text-xl flex-shrink-0">
            {isSuccess ? '✅' : isPartial ? '⚠️' : '❌'}
          </div>
          <div className="flex-1">
            <h3 className="font-bold text-white">Résultat Xray</h3>
            {result.test_name && (
              <p className="text-xs text-white/70 mt-0.5 truncate">{result.test_name}</p>
            )}
          </div>
          <button
            type="button"
            onClick={(e) => { e.preventDefault(); e.stopPropagation(); onClose() }}
            className="p-2 rounded-xl text-white/60 hover:text-white hover:bg-white/10 transition-all"
          >
            <X size={16} />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <div className="flex items-center gap-3 p-3 rounded-xl bg-gray-50">
            <span className="text-sm text-brand-muted">Statut :</span>
            <Badge variant={isSuccess ? 'success' : isPartial ? 'warning' : 'error'} dot>
              {result.status}
            </Badge>
            {result.created_count > 0 && (
              <span className="ml-auto text-sm font-bold text-brand-navy">
                {result.created_count} créé(s)
              </span>
            )}
          </div>

          {isSuccess && result.created_keys.length > 0 && (
            <div
              className="px-4 py-3 rounded-xl text-sm"
              style={{
                background: 'rgba(16,185,129,0.06)',
                border: '1px solid rgba(16,185,129,0.2)',
                color: '#065f46',
              }}
            >
              {successMessage}
            </div>
          )}

          {result.created_keys.length > 0 && (
            <div>
              <p className="text-xs font-bold text-brand-navy uppercase tracking-widest mb-2">
                Tests Jira créés
              </p>
              <ul className="space-y-2">
                {result.created_keys.map((k) => (
                  <li
                    key={k}
                    className="px-4 py-2.5 rounded-xl text-sm font-mono font-semibold flex items-center justify-between gap-3"
                    style={{
                      background: 'rgba(16,185,129,0.06)',
                      border: '1px solid rgba(16,185,129,0.2)',
                      color: '#065f46',
                    }}
                  >
                    <span>🔗 {k}</span>
                    {result.jira_browse_base_url && (<a
                      
                        href={result.jira_browse_base_url + '/' + k}
                        target="_blank"
                        rel="noreferrer"
                        className="text-xs font-semibold underline underline-offset-2"
                      >
                        Consulter dans Jira
                      </a>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {result.errors.length > 0 && (
            <div>
              <p className="text-xs font-bold text-brand-rose uppercase tracking-widest mb-2">
                Erreurs
              </p>
              <ul className="space-y-2">
                {result.errors.map((err, i) => (
                  <li
                    key={i}
                    className="px-4 py-2.5 rounded-xl text-sm"
                    style={{
                      background: 'rgba(244,63,94,0.06)',
                      border: '1px solid rgba(244,63,94,0.2)',
                      color: '#be123c',
                    }}
                  >
                    {err}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <div className="px-5 pb-5">
          <button
            type="button"
            onClick={(e) => { e.preventDefault(); e.stopPropagation(); onClose() }}
            className="w-full py-3.5 rounded-xl text-sm font-bold text-white transition-all hover:-translate-y-0.5"
            style={{ background: grad, boxShadow: '0 4px 16px rgba(10,15,46,0.15)' }}
          >
            Fermer
          </button>
        </div>
      </div>
    </div>
  )
}
/* ──────────────────────────────────────────────────────
   Main Table
────────────────────────────────────────────────────── */
export const ManualTestsTable: React.FC<ManualTestsTableProps> = ({
  tests,
  storyId,
  onTestsChange,
  expandable = true,
  showProjectPicker = true,
  defaultExpandedIndex = null,
}) => {
  const [localTests, setLocalTests] = useState(tests)
  const [editingTest, setEditingTest] = useState<any | null>(null)
  const [editingIndex, setEditingIndex] = useState<number | null>(null)
  const [integratingIndex, setIntegratingIndex] = useState<number | null>(null)
  const [integrationResult, setIntegrationResult] = useState<IntegrationResult | null>(null)
  const [expandedIndex, setExpandedIndex] = useState<number | null>(defaultExpandedIndex)
  const [xrayProjectKey, setXrayProjectKey] = useState<string | undefined>(undefined)
  const toast = useToast()
  const { selectedProject } = useAuth()

  React.useEffect(() => { setLocalTests(tests) }, [tests])
  const lastStoryIdRef = React.useRef(storyId)
  React.useEffect(() => {
    if (lastStoryIdRef.current !== storyId) {
      setExpandedIndex(null)
      lastStoryIdRef.current = storyId
    }
  }, [storyId])

  const projectKey = xrayProjectKey || selectedProject?.key || ''

  const handleProjectChange = useCallback((project: JiraProject) => {
    setXrayProjectKey(project.key)
  }, [])

  const handleIntegrate = useCallback(
    async (e: React.MouseEvent, test: any, index: number) => {
      e.preventDefault()
      e.stopPropagation()
      if (!projectKey) {
        toast.error('Sélectionnez un projet Jira pour l\'intégration Xray')
        return
      }
      setIntegratingIndex(index)
      try {
        const payload = buildPayload(test, storyId)
        const resp = await apiClient.integration.integrateTest({
          project_key: projectKey,
          test: payload,
        })
        setIntegrationResult({ ...resp, test_name: payload.test_name })
        if (resp.created_keys.length > 0) {
          toast.success(`Test intégré avec succès. ID Jira: ${resp.created_keys.join(', ')}`)
        } else if (resp.errors?.length) {
          toast.error('Intégration avec des erreurs')
        }
      } catch (err: any) {
        toast.error(err?.message || "Échec de l'intégration")
        setIntegrationResult({
          status: 'error',
          created_count: 0,
          created_keys: [],
          errors: [err?.message || 'Erreur'],
          test_name: test.test_name,
        })
      } finally {
        setIntegratingIndex(null)
      }
    },
    [projectKey, toast]
  )

  const handleEditClick = useCallback((e: React.MouseEvent, test: any, idx: number) => {
    e.preventDefault()
    e.stopPropagation()
    setEditingTest(test)
    setEditingIndex(idx)
  }, [])

  const handleSaved = useCallback(
    (updatedTest: any) => {
      if (editingIndex === null) return
      const next = [...localTests]
      next[editingIndex] = updatedTest
      setLocalTests(next)
      onTestsChange?.(next)
      setEditingTest(null)
      setEditingIndex(null)
    },
    [editingIndex, localTests, onTestsChange]
  )

  const toggleExpanded = useCallback((idx: number) => {
    if (!expandable) return
    setExpandedIndex((current) => (current === idx ? null : idx))
  }, [expandable])

  if (!localTests.length) return null

  return (
    <div className="animate-fade-in">
      <div className="syn-surface overflow-hidden">
        <div className="syn-strip" />

        {/* En-tête minimal */}
        <div className="px-4 py-3 flex items-center justify-between border-b border-brand-navy/[0.06]">
          <p className="text-sm font-semibold text-brand-navy">
            {localTests.length} test{localTests.length > 1 ? 's' : ''} généré{localTests.length > 1 ? 's' : ''}
          </p>
          <p className="text-xs text-brand-muted hidden sm:block">Cliquez pour voir le détail</p>
        </div>

        {showProjectPicker && (
          <div className="px-4 py-3 border-b border-brand-navy/[0.06] bg-brand-offwhite/40">
            <ProjectPicker
              value={projectKey || undefined}
              onChange={handleProjectChange}
            />
          </div>
        )}

        {/* Liste simple */}
        <ul>
          {localTests.map((test, idx) => {
            const allSteps =
              test.steps ||
              test.étapes?.flatMap((e: any) => e.steps || []) ||
              []
            const isExpanded = expandable && expandedIndex === idx
            const title = test.test_name || test.title || `Test ${idx + 1}`

            return (
              <li
                key={idx}
                className={`border-b border-brand-navy/[0.05] last:border-0 ${
                  isExpanded ? 'bg-brand-offwhite/30' : ''
                }`}
              >
                <button
                  type="button"
                  onClick={() => toggleExpanded(idx)}
                  className="w-full px-4 py-3.5 flex items-center gap-3 text-left hover:bg-brand-offwhite/50 transition-colors"
                >
                  <span
  className="flex-shrink-0 text-brand-muted transition-transform"
  style={isExpanded ? { transform: 'rotate(90deg)', color: NAV } : undefined}
>
  <ChevronRight size={16} />
</span>
                  <span className="flex-shrink-0 w-6 text-xs font-bold tabular-nums" style={{ color: RED }}>
  {idx + 1}.
</span>
<span className="flex-1 text-sm font-medium leading-snug min-w-0" style={{ color: NAV }}>
  {title}
</span>
                  <span className="flex-shrink-0 text-xs text-brand-muted">
                    {allSteps.length} étape{allSteps.length !== 1 ? 's' : ''}
                  </span>
                </button>

                {isExpanded && (
                  <div className="px-4 pb-5 pt-1 pl-[3.25rem] space-y-4">

                    <XrayTestView test={test} />

                    <div className="flex items-center gap-2 pt-2">
                      <button
                        type="button"
                        onClick={(e) => handleEditClick(e, test, idx)}
                        className="syn-btn-ghost"
                      >
                        <Pencil size={13} /> Éditer
                      </button>
                      <button
  type="button"
  disabled={integratingIndex === idx || !projectKey}
  title={!projectKey ? "Sélectionnez un projet Jira" : "Exporter vers Xray"}
  onClick={(e) => handleIntegrate(e, test, idx)}
  className="syn-btn-xray !text-xs !py-2 !px-4 !text-white !font-bold"
  style={{
    background: BUTTON_GRADIENT,
    border: "none",
    boxShadow: "0 4px 18px rgba(219,39,119,0.38)",
  }}
>
  {integratingIndex === idx ? (
    <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
  ) : (
    <Upload size={13} />
  )}
  Xray
</button>

                    </div>
                  </div>
                )}
              </li>
            )
          })}
        </ul>
      </div>

      {/* Modals */}
      {editingTest !== null && editingIndex !== null && (
        <TestEditDrawer
          test={editingTest}
          storyId={storyId ?? ''}
          allTests={localTests}
          editingIndex={editingIndex}
          onClose={() => { setEditingTest(null); setEditingIndex(null) }}
          onSaved={handleSaved}
        />
      )}

      {integrationResult !== null && (
        <IntegrationModal
          result={integrationResult}
          onClose={() => setIntegrationResult(null)}
        />
      )}

    </div>
  )
}