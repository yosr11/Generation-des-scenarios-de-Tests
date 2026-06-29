import React, { useState, useCallback } from 'react'
import { Pencil, Upload, ChevronRight, X } from 'lucide-react'
import { Badge } from '../ui/Badge'
import { apiClient } from '../../api/client'
import { useToast } from '../../contexts/ToastContext'
import { useAuth, JiraProject } from '../../contexts/AuthContext'
import { ProjectPicker } from '../projects/ProjectPicker'

/* ── types ── */
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

function buildPayload(test: any) {
  const rawSteps = test.steps || []
  const flatSteps = rawSteps.length
    ? rawSteps
    : (test.étapes || []).flatMap((e: any) =>
        (e.steps || []).map((s: any) => ({
          action: s.action || e.titre || '',
          expected_result: s.expected_result || '',
          data: s.data || '',
          actor: s.actor || e.actor || '',
        }))
      )

  const rawName = test.test_name || test.title || 'Untitled'
  const test_name = truncateSummary(rawName)

  return {
    test_name,
    objective: test.objective || rawName,
    scenario_type: test.scenario_type,
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
const TestEditDrawer: React.FC<{
  test: any
  storyId: string
  onClose: () => void
  onSaved: (t: any) => void
}> = ({ test, storyId, onClose, onSaved }) => {
  const [editedTest, setEditedTest] = useState<any>(test)
  const [message, setMessage] = useState('')
  const [chatHistory, setChatHistory] = useState<{ role: string; content: string }[]>([])
  const [aiReply, setAiReply] = useState<string | null>(null)
  const [refining, setRefining] = useState(false)
  const [saving, setSaving] = useState(false)
  const toast = useToast()

  const steps =
    editedTest?.steps ||
    editedTest?.étapes?.flatMap((e: any) => e.steps || []) ||
    []

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
        await apiClient.testEditing.saveEdited(storyId, [editedTest])
        onSaved(editedTest)
        toast.success('Test sauvegardé !')
      } catch (err: any) {
        toast.error(err?.message || 'Échec de la sauvegarde')
      } finally {
        setSaving(false)
      }
    },
    [editedTest, storyId, onSaved, toast]
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
          <section className="rounded-xl border border-brand-violet/15 bg-brand-violet/[0.03] p-4">
            <p className="syn-label text-brand-violet mb-2">Affiner avec l'IA</p>
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
                className="syn-btn-xray !text-xs !py-2 !px-4"
              >
                {refining ? (
                  <>
                    <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Affinement…
                  </>
                ) : (
                  'Affiner'
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
            <p className="syn-label mb-2">Objectif</p>
            <textarea
              className="w-full text-sm text-brand-navy leading-relaxed rounded-lg px-3 py-2.5 border border-brand-navy/[0.08] bg-brand-offwhite/30 focus:border-brand-violet focus:outline-none focus:ring-2 focus:ring-brand-violet/10 resize-none"
              value={editedTest?.objective || ''}
              placeholder="Objectif du test…"
              onChange={(e) => setEditedTest({ ...editedTest, objective: e.target.value })}
              onClick={(e) => e.stopPropagation()}
              rows={2}
            />
          </section>

          {/* Étapes */}
          {steps.length > 0 && (
            <section>
              <div className="flex items-center justify-between mb-2">
                <p className="syn-label">Étapes</p>
                <span className="text-xs text-brand-muted">{steps.length}</span>
              </div>
              <ol className="space-y-3">
                {steps.map((step: any, i: number) => (
                  <li
                    key={i}
                    className="pl-3 border-l-2 border-brand-violet/20 space-y-2"
                  >
                    <span className="text-xs font-bold text-brand-violet">{i + 1}.</span>
                    <input
                      className="w-full text-sm text-brand-navy rounded-lg px-2.5 py-2 border border-brand-navy/[0.08] bg-white focus:border-brand-violet focus:outline-none focus:ring-2 focus:ring-brand-violet/10"
                      value={step.action || step.titre || ''}
                      onChange={(e) => {
                        const newSteps = [...steps]
                        if (newSteps[i].action !== undefined) newSteps[i].action = e.target.value
                        else newSteps[i].titre = e.target.value
                        const newTest = { ...editedTest }
                        if (newTest.steps) newTest.steps = newSteps
                        setEditedTest(newTest)
                      }}
                      onClick={(e) => e.stopPropagation()}
                      placeholder="Action…"
                    />
                    <input
                      className="w-full text-xs text-brand-navy rounded-lg px-2.5 py-2 border border-brand-navy/[0.06] bg-brand-offwhite/20 focus:border-brand-violet focus:outline-none focus:ring-2 focus:ring-brand-violet/10"
                      value={step.expected_result || ''}
                      onChange={(e) => {
                        const newSteps = [...steps]
                        newSteps[i].expected_result = e.target.value
                        const newTest = { ...editedTest }
                        if (newTest.steps) newTest.steps = newSteps
                        setEditedTest(newTest)
                      }}
                      onClick={(e) => e.stopPropagation()}
                      placeholder="Résultat attendu…"
                    />
                  </li>
                ))}
              </ol>
            </section>
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
            className="flex-1 syn-btn-xray !py-2.5 justify-center disabled:opacity-50"
          >
            {saving ? (
              <>
                <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Sauvegarde…
              </>
            ) : (
              'Sauvegarder'
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
  React.useEffect(() => {
    setExpandedIndex(null)
  }, [tests])

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
        const payload = buildPayload(test)
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
                  <span className={`flex-shrink-0 text-brand-muted transition-transform ${isExpanded ? 'rotate-90 text-brand-violet' : ''}`}>
                    <ChevronRight size={16} />
                  </span>
                  <span className="flex-shrink-0 w-6 text-xs font-bold text-brand-violet tabular-nums">
                    {idx + 1}.
                  </span>
                  <span className={`flex-1 text-sm font-medium leading-snug min-w-0 ${
                    isExpanded ? 'text-brand-violet' : 'text-brand-navy'
                  }`}>
                    {title}
                  </span>
                  <span className="flex-shrink-0 text-xs text-brand-muted">
                    {allSteps.length} étape{allSteps.length !== 1 ? 's' : ''}
                  </span>
                </button>

                {isExpanded && (
                  <div className="px-4 pb-5 pt-1 pl-[3.25rem] space-y-4">

                    {test.objective && (
                      <div>
                        <p className="syn-label mb-1.5">Objectif</p>
                        <p className="text-sm text-brand-navy leading-relaxed">{test.objective}</p>
                      </div>
                    )}

                    {test.description && (
                      <div>
                        <p className="syn-label mb-1.5">Description</p>
                        <p className="text-sm text-brand-navy leading-relaxed whitespace-pre-wrap">
                          {test.description}
                        </p>
                      </div>
                    )}

                    {allSteps.length > 0 && (
                      <div>
                        <p className="syn-label mb-2">Étapes</p>
                        <div className="space-y-3">
                          {allSteps.map((step: any, si: number) => (
                            <div
                              key={si}
                              className="text-sm border-l-2 border-brand-violet/25 pl-3 py-0.5"
                            >
                              <p className="font-semibold text-brand-navy mb-1">
                                {si + 1}. {step.titre || step.action}
                              </p>
                              {step.data && (
                                <p className="text-xs text-brand-muted mb-1">
                                  <span className="font-medium">Données :</span> {step.data}
                                </p>
                              )}
                              {step.expected_result && (
                                <p className="text-xs text-brand-navy leading-relaxed">
                                  <span className="font-medium text-brand-muted">Résultat attendu :</span>{' '}
                                  {step.expected_result}
                                </p>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

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
                        title={!projectKey ? 'Sélectionnez un projet Jira' : 'Exporter vers Xray'}
                        onClick={(e) => handleIntegrate(e, test, idx)}
                        className="syn-btn-xray"
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