import React, { useState } from 'react'
import { X, Send, Save } from 'lucide-react'
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
      toast.success('Test refined successfully')
    } catch (err: any) {
      toast.error(err?.message || 'Refinement failed')
    } finally {
      setRefining(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await apiClient.testEditing.saveEdited(storyId, [editedTest])
      onSaved(editedTest)
      toast.success('Test saved')
    } catch (err: any) {
      toast.error(err?.message || 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const steps = editedTest?.steps || editedTest?.étapes?.flatMap((e: any) => e.steps || []) || []

  return (
    <>
      <div className="fixed inset-0 bg-black/30 z-40" onClick={onClose} aria-hidden />
      <aside className="fixed top-0 right-0 h-full w-full max-w-lg bg-white shadow-2xl z-50 flex flex-col">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200 bg-brand-navy text-white">
          <div>
            <h3 className="font-semibold">Edit Test</h3>
            <p className="text-xs text-white/70 mt-0.5">{editedTest?.test_name || 'Manual test'}</p>
          </div>
          <button type="button" onClick={onClose} className="p-1 hover:bg-white/10 rounded">
            <X size={20} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          <div className="bg-brand-bg rounded-lg p-4">
            <p className="text-xs font-medium text-gray-500 uppercase mb-1">Objective</p>
            <p className="text-sm text-brand-navy">{editedTest?.objective || '—'}</p>
          </div>

          {steps.length > 0 && (
            <div>
              <p className="text-sm font-semibold text-brand-navy mb-2">Steps ({steps.length})</p>
              <ol className="space-y-2">
                {steps.map((step: any, idx: number) => (
                  <li key={idx} className="bg-white border border-gray-200 rounded-lg p-3 text-sm">
                    <p className="font-medium">{step.action || step.titre}</p>
                    {step.expected_result && (
                      <p className="text-gray-600 mt-1">Expected: {step.expected_result}</p>
                    )}
                  </li>
                ))}
              </ol>
            </div>
          )}

          {assistantReply && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <p className="text-xs font-medium text-green-700 uppercase mb-1">AI Result</p>
              <p className="text-sm text-green-900">{assistantReply}</p>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-brand-navy mb-1.5">
              Refine with AI
            </label>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={3}
              placeholder="e.g. Add a step to verify error message..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm resize-none"
            />
            <Button
              type="button"
              variant="primary"
              size="sm"
              className="mt-2"
              isLoading={refining}
              onClick={handleRefine}
            >
              <Send size={14} />
              Apply refinement
            </Button>
          </div>

          {refining && (
            <div className="flex justify-center py-4">
              <Loader size="sm" text="Refining test..." />
            </div>
          )}
        </div>

        <div className="px-5 py-4 border-t border-gray-200 flex gap-2">
          <Button type="button" variant="outline" onClick={onClose} className="flex-1">
            Close
          </Button>
          <Button
            type="button"
            variant="primary"
            isLoading={saving}
            onClick={handleSave}
            className="flex-1"
          >
            <Save size={14} />
            Save changes
          </Button>
        </div>
      </aside>
    </>
  )
}
