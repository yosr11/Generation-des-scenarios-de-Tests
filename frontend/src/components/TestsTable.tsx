import React, {useState} from 'react'
import { apiClient } from '../api/client'

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
                  <button className="text-blue-600 hover:text-blue-800 transition-colors" onClick={async () => {
                    const key = test.storyId
                    // Integrate this single test (uses storyName as test name)
                    try {
                      setLoadingId(key)
                      const payload = { project_key: 'YOUQA', test: { test_name: test.storyName, objective: test.storyName, steps: [] } }
                      await apiClient.integration.integrateTest(payload)
                      alert(`Test intégré pour ${test.storyName}`)
                    } catch (err:any) {
                      alert(`Erreur intégration: ${err?.message || JSON.stringify(err)}`)
                    } finally {
                      setLoadingId(null)
                    }
                  }}>{loadingId===test.storyId? 'Integrating...':'Integrate'}</button>

                  <button className="text-green-600 hover:text-green-800 transition-colors" onClick={async () => {
                    const issueKey = window.prompt('Issue key Jira (ex: YOUQA-123) to add step to:')
                    if (!issueKey) return
                    const action = window.prompt('Action de la step:') || ''
                    const expected = window.prompt('Expected result:') || ''
                    try {
                      setLoadingId(issueKey)
                      await apiClient.integration.addStepToTest(issueKey, { action, expected_result: expected })
                      alert(`Step ajoutée à ${issueKey}`)
                    } catch (err:any) {
                      alert(`Erreur ajout step: ${err?.message || JSON.stringify(err)}`)
                    } finally {
                      setLoadingId(null)
                    }
                  }}>Add Step</button>
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
    </div>
  )
}
