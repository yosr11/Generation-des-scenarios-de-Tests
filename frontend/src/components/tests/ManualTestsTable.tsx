import React, { useState, useCallback } from 'react'
import { Pencil, Upload, TestTube, ChevronDown, ChevronUp, X } from 'lucide-react'
import { Badge } from '../ui/Badge'
import { apiClient } from '../../api/client'
import { useToast } from '../../contexts/ToastContext'
import { useAuth } from '../../contexts/AuthContext'

/* ── types ── */
interface ManualTestsTableProps {
  tests: any[]
  storyId?: string
  onTestsChange?: (tests: any[]) => void
}

export interface IntegrationResult {
  status: string
  created_count: number
  created_keys: string[]
  errors: string[]
  test_name?: string
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
  return {
    test_name: test.test_name || test.title || 'Untitled',
    objective: test.objective || test.test_name || '',
    scenario_type: test.scenario_type,
    steps: flatSteps.map((s: any) => ({
      action: s.action || '',
      expected_result: s.expected_result || s.result || '',
      data: s.data || '',
      actor: s.actor || '',
    })),
  }
}

const TYPE_STYLE: Record<string, { bg: string; text: string; border: string }> = {
  nominal:    { bg: 'rgba(124,58,237,0.08)',  text: '#7c3aed', border: 'rgba(124,58,237,0.2)' },
  alternatif: { bg: 'rgba(249,115,22,0.08)',  text: '#f97316', border: 'rgba(249,115,22,0.2)' },
  erreur:     { bg: 'rgba(244,63,94,0.08)',   text: '#f43f5e', border: 'rgba(244,63,94,0.2)' },
  default:    { bg: 'rgba(100,116,139,0.08)', text: '#64748b', border: 'rgba(100,116,139,0.2)' },
}

/* ──────────────────────────────────────────────────────
   Test Edit Panel (drawer)
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

  const steps = editedTest?.steps || editedTest?.étapes?.flatMap((e: any) => e.steps || []) || []

  const handleRefine = useCallback(async (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (!message.trim()) return
    setRefining(true)
    setAiReply(null)
    try {
      const resp = await apiClient.testEditing.refineChat({
        test: editedTest, message: message.trim(), chat_history: chatHistory, story_id: storyId,
      })
      setEditedTest(resp.test)
      setAiReply(resp.assistant_message)
      setChatHistory(prev => [...prev,
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
  }, [message, editedTest, chatHistory, storyId, toast])

  const handleSave = useCallback(async (e: React.MouseEvent) => {
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
  }, [editedTest, storyId, onSaved, toast])

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
        <div className="px-6 py-4 flex items-center gap-3 border-b border-gray-100"
          style={{ background: 'linear-gradient(135deg,#0a0f2e,#1a1f4e)' }}>
          <div className="flex-1 min-w-0">
            <p className="text-[10px] text-white/40 uppercase tracking-widest">Éditer le test</p>
            <input
              className="font-bold text-white text-sm bg-white/10 rounded px-2 py-1 mt-0.5 w-full border border-transparent focus:border-white/30 focus:outline-none placeholder:text-white/30"
              value={editedTest?.test_name || editedTest?.title || ''}
              placeholder="Test manuel"
              onChange={(e) => setEditedTest({ ...editedTest, test_name: e.target.value, title: e.target.value })}
              onClick={(e) => e.stopPropagation()}
            />
          </div>
          <button type="button" onClick={(e) => { e.preventDefault(); e.stopPropagation(); onClose() }}
            className="p-2 rounded-xl text-white/40 hover:text-white hover:bg-white/10 transition-all flex-shrink-0">
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4 bg-gray-50/60">

          {/* Objective */}
          <div className="bg-white rounded-2xl p-4 border border-gray-100 shadow-sm">
            <p className="text-[10px] font-bold text-brand-muted uppercase tracking-widest mb-2">Objectif</p>
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
                <span className="text-xs font-bold text-brand-muted bg-gray-100 px-2 py-0.5 rounded-full">{steps.length}</span>
              </div>
              <ol className="divide-y divide-gray-50">
                {steps.map((step: any, i: number) => (
                  <li key={i} className="px-4 py-3 flex items-start gap-3">
                    <span className="w-6 h-6 rounded-lg flex items-center justify-center text-white text-[11px] font-bold flex-shrink-0 mt-0.5"
                      style={{ background: 'linear-gradient(135deg,#2563eb,#4f46e5)' }}>
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
                          // Also support flat structure fallback
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
            <div className="rounded-2xl p-4 animate-fade-in"
              style={{ background: 'rgba(16,185,129,0.06)', border: '1px solid rgba(16,185,129,0.2)' }}>
              <p className="text-[10px] font-bold text-emerald-600 uppercase tracking-widest mb-2">✨ Réponse IA</p>
              <p className="text-sm text-emerald-900 leading-relaxed">{aiReply}</p>
            </div>
          )}

          {/* Refine */}
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
            <p className="text-xs font-bold text-brand-navy uppercase tracking-widest mb-3">🤖 Affiner avec l'IA</p>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onClick={(e) => e.stopPropagation()}
              rows={3}
              placeholder="ex : Ajouter une étape pour vérifier le message d'erreur..."
              className="w-full px-4 py-3 border-2 border-gray-100 rounded-xl text-sm resize-none text-brand-navy placeholder:text-gray-300 focus:border-brand-violet transition-all"
            />
            <div className="flex justify-end mt-3">
              <button type="button"
                onClick={handleRefine}
                disabled={refining || !message.trim()}
                className="px-5 py-2.5 rounded-xl text-sm font-bold text-white flex items-center gap-2 transition-all hover:-translate-y-0.5 disabled:opacity-40 disabled:cursor-not-allowed"
                style={{ background: 'linear-gradient(135deg,#6366f1,#8b5cf6)' }}>
                {refining ? (
                  <><span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Affinement…</>
                ) : (<>✨ Affiner</>)}
              </button>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-5 py-4 border-t border-gray-100 bg-white flex gap-3">
          <button type="button"
            onClick={(e) => { e.preventDefault(); e.stopPropagation(); onClose() }}
            className="flex-1 py-3 rounded-xl text-sm font-semibold text-brand-navy border-2 border-gray-100 hover:border-gray-200 transition-all">
            Annuler
          </button>
          <button type="button"
            onClick={handleSave}
            disabled={saving}
            className="flex-1 py-3 rounded-xl text-sm font-bold text-white flex items-center justify-center gap-2 transition-all hover:-translate-y-0.5 disabled:opacity-50"
            style={{ background: 'linear-gradient(135deg,#2563eb,#4f46e5)', boxShadow: '0 4px 16px rgba(37,99,235,0.35)' }}>
            {saving
              ? <><span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Sauvegarde…</>
              : <>💾 Sauvegarder</>}
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
      <div className="absolute inset-0 bg-brand-navy/50 backdrop-blur-sm"
        onClick={(e) => { e.preventDefault(); e.stopPropagation(); onClose() }} />

      <div
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-md bg-white rounded-3xl overflow-hidden"
        style={{ boxShadow: '0 25px 60px rgba(10,15,46,0.3)', zIndex: 1 }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-5 flex items-center gap-3" style={{ background: grad }}>
          <div className="w-10 h-10 rounded-xl bg-white/20 flex items-center justify-center text-xl flex-shrink-0">
            {isSuccess ? '✅' : isPartial ? '⚠️' : '❌'}
          </div>
          <div className="flex-1">
            <h3 className="font-bold text-white">Résultat Xray</h3>
            {result.test_name && <p className="text-xs text-white/70 mt-0.5 truncate">{result.test_name}</p>}
          </div>
          <button type="button"
            onClick={(e) => { e.preventDefault(); e.stopPropagation(); onClose() }}
            className="p-2 rounded-xl text-white/60 hover:text-white hover:bg-white/10 transition-all">
            <X size={16} />
          </button>
        </div>

        {/* Body */}
        <div className="p-5 space-y-4">
          <div className="flex items-center gap-3 p-3 rounded-xl bg-gray-50">
            <span className="text-sm text-brand-muted">Statut :</span>
            <Badge variant={isSuccess ? 'success' : isPartial ? 'warning' : 'error'} dot>
              {result.status}
            </Badge>
            {result.created_count > 0 && (
              <span className="ml-auto text-sm font-bold text-brand-navy">{result.created_count} créé(s)</span>
            )}
          </div>

          {result.created_keys.length > 0 && (
            <div>
              <p className="text-xs font-bold text-brand-navy uppercase tracking-widest mb-2">Clés créées</p>
              <ul className="space-y-2">
                {result.created_keys.map(k => (
                  <li key={k} className="px-4 py-2.5 rounded-xl text-sm font-mono font-semibold"
                    style={{ background: 'rgba(16,185,129,0.06)', border: '1px solid rgba(16,185,129,0.2)', color: '#065f46' }}>
                    🔗 {k}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {result.errors.length > 0 && (
            <div>
              <p className="text-xs font-bold text-brand-rose uppercase tracking-widest mb-2">Erreurs</p>
              <ul className="space-y-2">
                {result.errors.map((err, i) => (
                  <li key={i} className="px-4 py-2.5 rounded-xl text-sm"
                    style={{ background: 'rgba(244,63,94,0.06)', border: '1px solid rgba(244,63,94,0.2)', color: '#be123c' }}>
                    {err}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <div className="px-5 pb-5">
          <button type="button"
            onClick={(e) => { e.preventDefault(); e.stopPropagation(); onClose() }}
            className="w-full py-3.5 rounded-xl text-sm font-bold text-white transition-all hover:-translate-y-0.5"
            style={{ background: grad, boxShadow: '0 4px 16px rgba(10,15,46,0.15)' }}>
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
}) => {
  const [localTests, setLocalTests] = useState(tests)
  const [editingTest, setEditingTest] = useState<any | null>(null)
  const [editingIndex, setEditingIndex] = useState<number | null>(null)
  const [integratingIndex, setIntegratingIndex] = useState<number | null>(null)
  const [integrationResult, setIntegrationResult] = useState<IntegrationResult | null>(null)
  const [expandedRow, setExpandedRow] = useState<number | null>(null)
  const toast = useToast()
  const { selectedProject } = useAuth()

  React.useEffect(() => { setLocalTests(tests) }, [tests])

  const projectKey = selectedProject?.key || 'YOUQA'

  const handleIntegrate = useCallback(async (e: React.MouseEvent, test: any, index: number) => {
    e.preventDefault()
    e.stopPropagation()
    setIntegratingIndex(index)
    try {
      const payload = buildPayload(test)
      const resp = await apiClient.integration.integrateTest({ project_key: projectKey, test: payload })
      setIntegrationResult({ ...resp, test_name: payload.test_name })
      if (resp.status === 'success') toast.success(`Intégré : ${resp.created_keys.join(', ')}`)
      else if (resp.errors?.length) toast.error('Intégration avec des erreurs')
    } catch (err: any) {
      toast.error(err?.message || 'Échec de l\'intégration')
      setIntegrationResult({ status: 'error', created_count: 0, created_keys: [], errors: [err?.message || 'Erreur'], test_name: test.test_name })
    } finally {
      setIntegratingIndex(null)
    }
  }, [projectKey, toast])

  const handleEditClick = useCallback((e: React.MouseEvent, test: any, idx: number) => {
    e.preventDefault()
    e.stopPropagation()
    setEditingTest(test)
    setEditingIndex(idx)
  }, [])

  const handleSaved = useCallback((updatedTest: any) => {
    if (editingIndex === null) return
    const next = [...localTests]
    next[editingIndex] = updatedTest
    setLocalTests(next)
    onTestsChange?.(next)
    setEditingTest(null)
    setEditingIndex(null)
  }, [editingIndex, localTests, onTestsChange])

  if (!localTests.length) return null

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="bg-white rounded-3xl border border-gray-100 shadow-card p-6 flex items-center justify-between">
        <div>
          <h3 className="font-bold text-brand-navy flex items-center gap-2">
            <TestTube size={18} className="text-blue-600" /> Tests Manuels Générés
          </h3>
          <p className="text-xs text-brand-muted mt-1">{localTests.length} test(s) généré(s)</p>
        </div>
        <Badge variant="rose" size="sm">{localTests.length}</Badge>
      </div>

      <div className="space-y-8">
        {localTests.map((test, idx) => {
          const allSteps = test.steps || test.étapes?.flatMap((e: any) => e.steps || []) || []

          return (
            <div key={idx} className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
              {/* Test Header */}
              <div className="bg-gray-50 px-6 py-4 border-b border-gray-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <h4 className="font-bold text-brand-navy text-lg">{test.test_name || test.title || `Test ${idx + 1}`}</h4>
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={(e) => handleEditClick(e, test, idx)}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-brand-navy bg-white border border-gray-200 hover:border-blue-500 hover:text-blue-600 transition-all shadow-sm"
                  >
                    <Pencil size={14} /> Éditer
                  </button>
                  <button
                    type="button"
                    disabled={integratingIndex === idx}
                    onClick={(e) => handleIntegrate(e, test, idx)}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold text-white transition-all shadow-sm disabled:opacity-50"
                    style={{ background: 'linear-gradient(135deg,#2563eb,#4f46e5)' }}
                  >
                    {integratingIndex === idx ? <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <Upload size={14} />} Xray
                  </button>
                </div>
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
                        <span className="text-blue-500">[{step.actor || 'Collaborateur'}]</span> {step.titre || step.action}
                      </p>
                    ))}
                  </div>
                </div>

                {/* Steps Table */}
                <div className="border border-gray-200 rounded-xl overflow-hidden shadow-sm">
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
                        <tr key={si} className="align-top bg-white hover:bg-gray-50/50 transition-colors">
                          <td className="px-4 py-4 border-r border-gray-200 text-center font-bold text-brand-navy bg-[#f4f5f7]">
                            {si + 1}
                          </td>
                          <td className="px-4 py-4 border-r border-gray-200">
                            <p className="text-sm text-gray-900 mb-3 leading-relaxed">
                              <span className="text-blue-500">[{step.actor || 'Collaborateur'}]</span> {step.titre || step.action}
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

      {/* Modals rendered via Portal-like pattern, outside table DOM */}
      {editingTest !== null && editingIndex !== null && (
        <TestEditDrawer
          test={editingTest}
          storyId={storyId}
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
