import React, { useState } from 'react'
import { X, Send, Save, Bot, ChevronRight, Sparkles } from 'lucide-react'
import { Button } from '../ui/Button'
import { Loader } from '../ui/Loader'
import { apiClient } from '../../api/client'
import { useToast } from '../../contexts/ToastContext'

interface TestEditPanelProps {
  test: any
  storyId: string
  onClose: () => void
  onSaved: (updatedTest: any) => void
}

export const TestEditPanel: React.FC<TestEditPanelProps> = ({
  test,
  storyId,
  onClose,
  onSaved,
}) => {
  const [editedTest, setEditedTest] = useState<any>(test)
  const [message, setMessage] = useState('')
  const [chatHistory, setChatHistory] = useState<{ role: string; content: string }[]>([])
  const [assistantReply, setAssistantReply] = useState<string | null>(null)
  const [refining, setRefining] = useState(false)
  const [saving, setSaving] = useState(false)
  const toast = useToast()

  const handleRefine = async () => {
    if (!message.trim()) return
    setRefining(true)
    setAssistantReply(null)
    try {
      const resp = await apiClient.testEditing.refineChat({
        test: editedTest,
        message: message.trim(),
        chat_history: chatHistory,
        story_id: storyId,
      })
      setEditedTest(resp.test)
      setAssistantReply(resp.assistant_message)
      setChatHistory((prev) => [
        ...prev,
        { role: 'user', content: message.trim() },
        { role: 'assistant', content: resp.assistant_message },
      ])
      setMessage('')
      toast.success('Test affiné avec succès')
    } catch (err: any) {
      toast.error(err?.message || 'Échec du raffinement')
    } finally {
      setRefining(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await apiClient.testEditing.saveEdited(storyId, [editedTest])
      onSaved(editedTest)
      toast.success('Test sauvegardé')
    } catch (err: any) {
      toast.error(err?.message || 'Échec de la sauvegarde')
    } finally {
      setSaving(false)
    }
  }

  const steps = editedTest?.steps || editedTest?.étapes?.flatMap((e: any) => e.steps || []) || []

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-brand-navy/40 z-40 backdrop-blur-sm animate-fade-in"
        onClick={onClose}
        aria-hidden
      />

      {/* Drawer */}
      <aside className="fixed top-0 right-0 h-full w-full max-w-lg z-50 flex flex-col animate-slide-up shadow-float bg-white">

        {/* Header */}
        <div className="px-6 py-4 flex items-center gap-3 border-b border-gray-100"
          style={{ background: 'var(--grad-sidebar)' }}>
          <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
            style={{ background: 'rgba(244,63,94,0.2)', border: '1px solid rgba(244,63,94,0.3)' }}>
            <Bot size={17} className="text-brand-rose" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-bold text-white text-sm">Éditer le Test</h3>
            <p className="text-xs text-white/50 truncate mt-0.5">
              {editedTest?.test_name || 'Test manuel'}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-xl text-white/50 hover:text-white hover:bg-white/10 transition-all"
          >
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-5 space-y-5 bg-brand-offwhite">

          {/* Objective */}
          <div className="bg-white rounded-2xl p-4 border border-gray-100 shadow-sm">
            <p className="text-[10px] font-bold text-brand-muted uppercase tracking-widest mb-2">Objectif</p>
            <p className="text-sm text-brand-navy leading-relaxed">{editedTest?.objective || '—'}</p>
          </div>

          {/* Steps */}
          {steps.length > 0 && (
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
                <p className="text-xs font-bold text-brand-navy uppercase tracking-widest">
                  Étapes
                </p>
                <span className="text-xs font-bold text-brand-muted bg-gray-100 px-2 py-0.5 rounded-full">
                  {steps.length}
                </span>
              </div>
              <ol className="divide-y divide-gray-50">
                {steps.map((step: any, idx: number) => (
                  <li key={idx} className="px-4 py-3 flex items-start gap-3">
                    <span
                      className="w-6 h-6 rounded-lg flex items-center justify-center flex-shrink-0 text-[11px] font-bold text-white mt-0.5"
                      style={{ background: 'var(--grad-cta)' }}
                    >
                      {idx + 1}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-brand-navy">{step.action || step.titre}</p>
                      {step.expected_result && (
                        <p className="text-xs text-brand-muted mt-1 flex items-center gap-1">
                          <ChevronRight size={11} />
                          {step.expected_result}
                        </p>
                      )}
                    </div>
                  </li>
                ))}
              </ol>
            </div>
          )}

          {/* AI Reply */}
          {assistantReply && (
            <div className="rounded-2xl p-4 animate-fade-in"
              style={{
                background: 'rgba(16,185,129,0.06)',
                border: '1px solid rgba(16,185,129,0.2)',
              }}>
              <div className="flex items-center gap-2 mb-2">
                <Sparkles size={13} className="text-emerald-500" />
                <p className="text-[10px] font-bold text-emerald-600 uppercase tracking-widest">
                  Réponse de l'IA
                </p>
              </div>
              <p className="text-sm text-emerald-900 leading-relaxed">{assistantReply}</p>
            </div>
          )}

          {/* AI Refine */}
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
            <div className="flex items-center gap-2 mb-3">
              <Bot size={14} className="text-brand-violet" />
              <p className="text-xs font-bold text-brand-navy uppercase tracking-widest">
                Affiner avec l'IA
              </p>
            </div>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={3}
              placeholder="ex : Ajouter une étape pour vérifier le message d'erreur..."
              onKeyDown={(e) => {
                if (e.key === 'Enter' && e.ctrlKey) handleRefine()
              }}
              className="w-full px-4 py-3 border-2 border-gray-100 rounded-xl text-sm resize-none text-brand-navy placeholder:text-gray-300 focus:border-brand-violet transition-all"
            />
            <div className="flex items-center justify-between mt-3">
              <p className="text-[10px] text-gray-400">Ctrl+Entrée pour envoyer</p>
              <Button
                type="button"
                variant="violet"
                size="sm"
                isLoading={refining}
                disabled={!message.trim()}
                onClick={handleRefine}
              >
                <Send size={13} />
                Affiner
              </Button>
            </div>
          </div>

          {refining && (
            <div className="flex justify-center py-4">
              <Loader size="sm" text="Raffinement en cours..." />
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-4 border-t border-gray-100 bg-white flex gap-3">
          <Button type="button" variant="outline" onClick={onClose} className="flex-1">
            Annuler
          </Button>
          <Button
            type="button"
            variant="primary"
            isLoading={saving}
            onClick={handleSave}
            className="flex-1"
          >
            <Save size={14} />
            Sauvegarder
          </Button>
        </div>
      </aside>
    </>
  )
}
