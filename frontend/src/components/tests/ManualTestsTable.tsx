import React, { useState, useCallback } from 'react'
import { Pencil, Upload, TestTube, ChevronDown, ChevronRight, X, Target, ListChecks } from 'lucide-react'
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
        className="absolute top-0 right-0 h-full w-full max-w-lg bg-white flex flex-col"
        style={{ boxShadow: '-8px 0 40px rgba(10,15,46,0.25)', zIndex: 1 }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          className="px-6 py-4 flex items-center gap-3 border-b border-gray-100"
          style={{ background: 'linear-gradient(135deg,#0a0f2e,#1a1f4e)' }}
        >
          <div className="flex-1 min-w-0">
            <p className="text-[10px] text-white/40 uppercase tracking-widest">Éditer le test</p>
            <input
              className="font-bold text-white text-sm bg-white/10 rounded px-2 py-1 mt-0.5 w-full border border-transparent focus:border-white/30 focus:outline-none placeholder:text-white/30"
              value={editedTest?.test_name || editedTest?.title || ''}
              placeholder="Test manuel"
              onChange={(e) =>
                setEditedTest({ ...editedTest, test_name: e.target.value, title: e.target.value })
              }
              onClick={(e) => e.stopPropagation()}
            />
          </div>
          <button
            type="button"
            onClick={(e) => { e.preventDefault(); e.stopPropagation(); onClose() }}
            className="p-2 rounded-xl text-white/40 hover:text-white hover:bg-white/10 transition-all flex-shrink-0"
          >
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4 bg-gray-50/60">

          {/* Objective */}
          <div className="bg-white rounded-2xl p-4 border border-gray-100 shadow-sm">
            <p className="text-[10px] font-bold text-brand-muted uppercase tracking-widest mb-2">
              Objectif
            </p>
            <textarea
              className="w-full text-sm text-brand-navy leading-relaxed border border-gray-200 rounded p-2 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 resize-none"
              value={editedTest?.objective || ''}
              placeholder="Objectif du test..."
              onChange={(e) => setEditedTest({ ...editedTest, objective: e.target.value })}
              onClick={(e) => e.stopPropagation()}
              rows={2}
            />
          </div>

          {/* Steps */}
          {steps.length > 0 && (
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
                <p className="text-xs font-bold text-brand-navy uppercase tracking-widest">Étapes</p>
                <span className="text-xs font-bold text-brand-muted bg-gray-100 px-2 py-0.5 rounded-full">
                  {steps.length}
                </span>
              </div>
              <ol className="divide-y divide-gray-50">
                {steps.map((step: any, i: number) => (
                  <li key={i} className="px-4 py-3 flex items-start gap-3">
                    <span
                      className="w-6 h-6 rounded-lg flex items-center justify-center text-white text-[11px] font-bold flex-shrink-0 mt-0.5"
                      style={{ background: 'linear-gradient(135deg,#2563eb,#4f46e5)' }}
                    >
                      {i + 1}
                    </span>
                    <div className="flex-1 min-w-0 space-y-2">
                      <input
                        className="w-full text-sm font-medium text-brand-navy border border-gray-200 rounded p-1.5 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
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
                        placeholder="Action..."
                      />
                      <input
                        className="w-full text-xs text-brand-muted border border-gray-200 rounded p-1.5 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                        value={step.expected_result || ''}
                        onChange={(e) => {
                          const newSteps = [...steps]
                          newSteps[i].expected_result = e.target.value
                          const newTest = { ...editedTest }
                          if (newTest.steps) newTest.steps = newSteps
                          setEditedTest(newTest)
                        }}
                        onClick={(e) => e.stopPropagation()}
                        placeholder="Résultat attendu..."
                      />
                    </div>
                  </li>
                ))}
              </ol>
            </div>
          )}

          {/* AI Reply */}
          {aiReply && (
            <div
              className="rounded-2xl p-4 animate-fade-in"
              style={{
                background: 'rgba(16,185,129,0.06)',
                border: '1px solid rgba(16,185,129,0.2)',
              }}
            >
              <p className="text-[10px] font-bold text-emerald-600 uppercase tracking-widest mb-2">
                ✨ Réponse IA
              </p>
              <p className="text-sm text-emerald-900 leading-relaxed">{aiReply}</p>
            </div>
          )}

          {/* Refine */}
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
            <p className="text-xs font-bold text-brand-navy uppercase tracking-widest mb-3">
              🤖 Affiner avec l'IA
            </p>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onClick={(e) => e.stopPropagation()}
              rows={3}
              placeholder="ex : Ajouter une étape pour vérifier le message d'erreur..."
              className="w-full px-4 py-3 border-2 border-gray-100 rounded-xl text-sm resize-none text-brand-navy placeholder:text-gray-300 focus:border-brand-violet transition-all"
            />
            <div className="flex justify-end mt-3">
              <button
                type="button"
                onClick={handleRefine}
                disabled={refining || !message.trim()}
                className="px-5 py-2.5 rounded-xl text-sm font-bold text-white flex items-center gap-2 transition-all hover:-translate-y-0.5 disabled:opacity-40 disabled:cursor-not-allowed"
                style={{ background: 'linear-gradient(135deg,#6366f1,#8b5cf6)' }}
              >
                {refining ? (
                  <>
                    <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Affinement…
                  </>
                ) : (
                  <>✨ Affiner</>
                )}
              </button>
            </div>
          </div>

        </div>{/* fin body */}

        {/* Footer */}
        <div className="px-5 py-4 border-t border-gray-100 bg-white flex gap-3">
          <button
            type="button"
            onClick={(e) => { e.preventDefault(); e.stopPropagation(); onClose() }}
            className="flex-1 py-3 rounded-xl text-sm font-semibold text-brand-navy border-2 border-gray-100 hover:border-gray-200 transition-all"
          >
            Annuler
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="flex-1 py-3 rounded-xl text-sm font-bold text-white flex items-center justify-center gap-2 transition-all hover:-translate-y-0.5 disabled:opacity-50"
            style={{
              background: 'linear-gradient(135deg,#2563eb,#4f46e5)',
              boxShadow: '0 4px 16px rgba(37,99,235,0.35)',
            }}
          >
            {saving ? (
              <>
                <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Sauvegarde…
              </>
            ) : (
              <>💾 Sauvegarder</>
            )}
          </button>
        </div>

      </aside>{/* fin drawer */}
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
  defaultExpandedIndex = 0,
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
    if (defaultExpandedIndex !== null && defaultExpandedIndex !== undefined) {
      setExpandedIndex(defaultExpandedIndex)
    }
  }, [defaultExpandedIndex, tests.length])

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
    <div className="space-y-5 animate-fade-in">

      {/* Header */}
      <div className="syn-surface overflow-hidden">
        <div className="syn-strip" />
        <div className="p-5">
        <div className="flex flex-col lg:flex-row lg:items-start gap-5">
          <div className="flex-1">
            <h3 className="font-bold text-brand-navy flex items-center gap-2 text-base">
              <span className="w-8 h-8 rounded-lg bg-grad-violet flex items-center justify-center">
                <TestTube size={15} className="text-white" />
              </span>
              Tests manuels générés
            </h3>
            <p className="text-xs text-brand-muted mt-2 ml-10">
              {localTests.length} test{localTests.length > 1 ? 's' : ''} — cliquez sur un titre pour voir le détail
            </p>
          </div>
          <Badge variant="violet" size="sm">{localTests.length}</Badge>
        </div>
        {showProjectPicker && (
          <div className="mt-4 pt-4 border-t border-brand-navy/[0.06] max-w-md">
            <ProjectPicker
              value={projectKey || undefined}
              onChange={handleProjectChange}
            />
          </div>
        )}
        </div>
      </div>

      {/* Tests */}
      <div className="space-y-3">
        {localTests.map((test, idx) => {
          const allSteps =
            test.steps ||
            test.étapes?.flatMap((e: any) => e.steps || []) ||
            []
          const isExpanded = !expandable || expandedIndex === idx
          const title = test.test_name || test.title || `Test ${idx + 1}`

          return (
            <div
              key={idx}
              className={`syn-test-card ${isExpanded ? 'syn-test-card--expanded' : ''}`}
            >
              <div className={`px-5 py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 syn-test-card-header transition-colors`}>
                <button
                  type="button"
                  onClick={() => toggleExpanded(idx)}
                  className={`flex items-start gap-3 text-left flex-1 min-w-0 group ${
                    expandable ? 'cursor-pointer' : 'cursor-default'
                  }`}
                >
                  {expandable && (
                    <span className={`mt-1 flex-shrink-0 transition-colors ${isExpanded ? 'text-brand-violet' : 'text-brand-muted'}`}>
                      {isExpanded ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                    </span>
                  )}
                  <div className="flex-1 min-w-0">
                    <h4 className="font-bold text-brand-navy text-base leading-snug group-hover:text-brand-violet transition-colors">
                      {title}
                    </h4>
                    <div className="flex flex-wrap items-center gap-2 mt-1.5">
                      {test.scenario_type && (
                        <span className="syn-badge syn-badge--violet">
                          {test.scenario_type}
                        </span>
                      )}
                      <span className="text-[11px] text-brand-muted">
                        {allSteps.length} étape{allSteps.length !== 1 ? 's' : ''}
                      </span>
                    </div>
                    {!isExpanded && test.objective && (
                      <p className="text-xs text-brand-muted mt-2 line-clamp-2 leading-relaxed">
                        {test.objective}
                      </p>
                    )}
                  </div>
                </button>
                <div className="flex items-center gap-2 flex-shrink-0 sm:ml-4">
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

              {isExpanded && (
                <div className="px-5 pb-5 space-y-5 border-t border-brand-navy/[0.05] pt-5 bg-gradient-to-b from-brand-offwhite/40 to-white">

                  {test.objective && (
                    <div className="rounded-xl border border-brand-violet/10 bg-brand-violet/[0.03] p-4">
                      <h5 className="syn-label flex items-center gap-1.5 mb-2 text-brand-violet">
                        <Target size={13} /> Objectif
                      </h5>
                      <p className="text-sm text-brand-navy leading-relaxed">{test.objective}</p>
                    </div>
                  )}

                  {test.description && (
                    <div className="rounded-xl border border-brand-navy/[0.08] bg-white p-4">
                      <h5 className="syn-label mb-2">Description</h5>
                      <p className="text-sm text-brand-navy leading-relaxed whitespace-pre-wrap">
                        {test.description}
                      </p>
                    </div>
                  )}

                  {allSteps.length > 0 && (
                    <div>
                      <h5 className="syn-label flex items-center gap-1.5 mb-3">
                        <ListChecks size={13} /> Étapes ({allSteps.length})
                      </h5>
                      <div className="border border-brand-navy/[0.08] rounded-xl overflow-hidden shadow-sm">
                        <table className="w-full text-sm text-left">
                          <thead className="syn-table-head">
                            <tr>
                              <th className="w-10 px-3 py-2.5 text-center">#</th>
                              <th className="px-3 py-2.5">Action</th>
                              <th className="px-3 py-2.5 hidden md:table-cell">Données</th>
                              <th className="px-3 py-2.5">Résultat attendu</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-brand-navy/[0.05]">
                            {allSteps.map((step: any, si: number) => (
                              <tr key={si} className="align-top bg-white hover:bg-brand-offwhite/60 transition-colors">
                                <td className="px-3 py-3 text-center font-bold text-brand-violet text-xs bg-brand-offwhite/50">
                                  {si + 1}
                                </td>
                                <td className="px-3 py-3">
                                  <span className="syn-badge syn-badge--violet !text-[9px]">
                                    {step.actor || 'Collaborateur'}
                                  </span>
                                  <p className="text-sm text-brand-navy mt-1.5 leading-relaxed">
                                    {step.titre || step.action}
                                  </p>
                                </td>
                                <td className="px-3 py-3 text-xs text-brand-muted font-mono whitespace-pre-wrap hidden md:table-cell">
                                  {step.data || '—'}
                                </td>
                                <td className="px-3 py-3 text-sm text-brand-navy leading-relaxed">
                                  {step.expected_result ? (
                                    <ul className="list-disc list-inside space-y-1">
                                      {step.expected_result.split('\n').map((line: string, i: number) => {
                                        const clean = line.replace(/^-\s*/, '').trim()
                                        return clean ? <li key={i}>{clean}</li> : null
                                      })}
                                    </ul>
                                  ) : '—'}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
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