import React, { useState } from 'react'
import { Pencil, Upload } from 'lucide-react'
import { Button } from '../ui/Button'
import { Badge } from '../ui/Badge'
import { Loader } from '../ui/Loader'
import { TestEditPanel } from './TestEditPanel'
import { IntegrationResultPanel, IntegrationResult } from './IntegrationResultPanel'
import { apiClient } from '../../api/client'
import { useToast } from '../../contexts/ToastContext'
import { useAuth } from '../../contexts/AuthContext'

interface ManualTestsTableProps {
  tests: any[]
  storyId: string
  onTestsChange?: (tests: any[]) => void
}

function buildIntegrationPayload(test: any) {
  const rawSteps = test.steps || []
  const flatSteps = rawSteps.length
    ? rawSteps
    : (test.étapes || []).flatMap((etape: any) =>
        (etape.steps || []).map((s: any) => ({
          action: s.action || etape.titre || '',
          expected_result: s.expected_result || '',
          data: s.data || '',
          actor: s.actor || etape.actor || '',
        }))
      )

  return {
    test_name: test.test_name || test.title || 'Untitled test',
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
  const toast = useToast()
  const { selectedProject } = useAuth()

  React.useEffect(() => {
    setLocalTests(tests)
  }, [tests])

  const projectKey = selectedProject?.key || 'YOUQA'

  const handleIntegrate = async (test: any, index: number) => {
    setIntegratingIndex(index)
    try {
      const payload = buildIntegrationPayload(test)
      const resp = await apiClient.integration.integrateTest({
        project_key: projectKey,
        test: payload,
      })
      setIntegrationResult({
        ...resp,
        test_name: payload.test_name,
      })
      if (resp.status === 'success') {
        toast.success(`Integrated: ${resp.created_keys.join(', ')}`)
      } else if (resp.errors?.length) {
        toast.error('Integration completed with errors')
      }
    } catch (err: any) {
      toast.error(err?.message || 'Integration failed')
      setIntegrationResult({
        status: 'error',
        created_count: 0,
        created_keys: [],
        errors: [err?.message || 'Integration failed'],
        test_name: test.test_name,
      })
    } finally {
      setIntegratingIndex(null)
    }
  }

  const handleSaved = (updatedTest: any) => {
    if (editingIndex === null) return
    const next = [...localTests]
    next[editingIndex] = updatedTest
    setLocalTests(next)
    onTestsChange?.(next)
    setEditingTest(null)
    setEditingIndex(null)
  }

  if (!localTests.length) return null

  return (
    <>
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-200">
          <h3 className="font-semibold text-brand-navy">Generated Manual Tests</h3>
          <p className="text-xs text-gray-500 mt-1">{localTests.length} test(s) — edit or integrate into Xray</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-brand-bg border-b border-gray-200">
                <th className="text-left py-3 px-4 font-semibold text-brand-navy">Test name</th>
                <th className="text-left py-3 px-4 font-semibold text-brand-navy">Type</th>
                <th className="text-left py-3 px-4 font-semibold text-brand-navy">Steps</th>
                <th className="text-right py-3 px-4 font-semibold text-brand-navy">Actions</th>
              </tr>
            </thead>
            <tbody>
              {localTests.map((test, idx) => {
                const stepCount =
                  test.steps?.length ||
                  (test.étapes || []).reduce(
                    (acc: number, e: any) => acc + (e.steps?.length || 0),
                    0
                  )
                return (
                  <tr key={idx} className="border-b border-gray-100 hover:bg-brand-bg/50">
                    <td className="py-3 px-4 font-medium text-brand-navy">
                      {test.test_name || test.title}
                    </td>
                    <td className="py-3 px-4">
                      {test.scenario_type && (
                        <Badge variant="warning">{test.scenario_type}</Badge>
                      )}
                    </td>
                    <td className="py-3 px-4 text-gray-600">{stepCount}</td>
                    <td className="py-3 px-4">
                      <div className="flex items-center justify-end gap-2">
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            setEditingTest(test)
                            setEditingIndex(idx)
                          }}
                        >
                          <Pencil size={14} />
                          Edit
                        </Button>
                        <Button
                          type="button"
                          variant="primary"
                          size="sm"
                          isLoading={integratingIndex === idx}
                          onClick={() => handleIntegrate(test, idx)}
                        >
                          <Upload size={14} />
                          Xray
                        </Button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {editingTest && editingIndex !== null && (
        <TestEditPanel
          test={editingTest}
          storyId={storyId}
          onClose={() => {
            setEditingTest(null)
            setEditingIndex(null)
          }}
          onSaved={handleSaved}
        />
      )}

      {integrationResult && (
        <IntegrationResultPanel
          result={integrationResult}
          onClose={() => setIntegrationResult(null)}
        />
      )}
    </>
  )
}
