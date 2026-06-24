import React, { useState } from 'react'
import { apiClient } from '../api/client'
import { Button } from './ui/Button'
import { IntegrationResultPanel, IntegrationResult } from './tests/IntegrationResultPanel'
import { TestEditPanel } from './tests/TestEditPanel'
import { useToast } from '../contexts/ToastContext'
import { useAuth } from '../contexts/AuthContext'

interface TestScore {
  storyId: string
  storyName: string
  score: number
  status: 'pass' | 'fail' | 'pending'
}

interface TestsTableProps {
  data: TestScore[]
}

export default function TestsTable({ data }: TestsTableProps) {
  const [loadingId, setLoadingId] = useState<string | null>(null)
  const [integrationResult, setIntegrationResult] = useState<IntegrationResult | null>(null)
  const [editingTest, setEditingTest] = useState<any | null>(null)
  const toast = useToast()
  const { selectedProject } = useAuth()
  const projectKey = selectedProject?.key || 'YOUQA'
  const getStatusBadge = (status: string) => {
    const badges = {
      pass: 'bg-green-100 text-green-800',
      fail: 'bg-red-100 text-red-800',
      pending: 'bg-yellow-100 text-yellow-800',
    }
    return badges[status as keyof typeof badges] || 'bg-gray-100 text-gray-800'
  }

  const getScoreBadge = (score: number) => {
    if (score >= 9) return 'bg-green-100 text-green-800'
    if (score >= 7) return 'bg-blue-100 text-blue-800'
    if (score >= 5) return 'bg-yellow-100 text-yellow-800'
    return 'bg-red-100 text-red-800'
  }

  return (
    <div className="card">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Tests Générés</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="text-left py-3 px-4 font-semibold text-gray-900">Story ID</th>
              <th className="text-left py-3 px-4 font-semibold text-gray-900">Nom du Test</th>
              <th className="text-center py-3 px-4 font-semibold text-gray-900">Score</th>
              <th className="text-center py-3 px-4 font-semibold text-gray-900">Statut</th>
              <th className="text-center py-3 px-4 font-semibold text-gray-900">Actions</th>
            </tr>
          </thead>
          <tbody>
            {data.map((test) => (
              <tr key={test.storyId} className="border-b border-gray-200 hover:bg-gray-50 transition-colors">
                <td className="py-3 px-4 text-gray-600 font-mono text-xs">{test.storyId}</td>
                <td className="py-3 px-4 text-gray-900">{test.storyName}</td>
                <td className="py-3 px-4 text-center">
                  <span className={`inline-block px-3 py-1 rounded-full text-sm font-semibold ${getScoreBadge(test.score)}`}>
                    {test.score.toFixed(1)}/10
                  </span>
                </td>
                <td className="py-3 px-4 text-center">
                  <span className={`inline-block px-3 py-1 rounded-full text-xs font-semibold ${getStatusBadge(test.status)}`}>
                    {test.status.toUpperCase()}
                  </span>
                </td>
                <td className="py-3 px-4 text-center space-x-2">
                  <button
                    className="text-brand-navy hover:text-brand-orange transition-colors text-sm font-medium"
                    onClick={async () => {
                    const key = test.storyId
                    try {
                      setLoadingId(key)
                      const payload = {
                        project_key: projectKey,
                        test: { test_name: test.storyName, objective: test.storyName, steps: [] },
                      }
                      const resp = await apiClient.integration.integrateTest(payload)
                      setIntegrationResult({ ...resp, test_name: test.storyName })
                      toast.success('Integration completed')
                    } catch (err: any) {
                      toast.error(err?.message || 'Integration failed')
                    } finally {
                      setLoadingId(null)
                    }
                  }}
                  >
                    {loadingId === test.storyId ? 'Integrating...' : 'Integrate'}
                  </button>

                  <button
                    className="text-brand-orange hover:text-brand-red transition-colors text-sm font-medium"
                    onClick={() =>
                      setEditingTest({
                        test_name: test.storyName,
                        objective: test.storyName,
                        steps: [],
                      })
                    }
                  >
                    Edit
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {data.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          Aucun test généré pour le moment.
        </div>
      )}

      {editingTest && (
        <TestEditPanel
          test={editingTest}
          storyId={data[0]?.storyId || 'UNKNOWN'}
          onClose={() => setEditingTest(null)}
          onSaved={(updated) => {
            setEditingTest(null)
            toast.success('Test updated')
          }}
        />
      )}

      {integrationResult && (
        <IntegrationResultPanel
          result={integrationResult}
          onClose={() => setIntegrationResult(null)}
        />
      )}
    </div>
  )
}
