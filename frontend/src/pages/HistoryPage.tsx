import React from 'react'
import { useAnalysisHistory } from '../hooks'
import { SkeletonLoader } from '../components/ui/Loader'
import { Badge } from '../components/ui/Badge'
import { Alert } from '../components/ui/Alert'
import { Button } from '../components/ui/Button'
import { Card, CardBody, CardHeader } from '../components/ui/Card'
import { useToast } from '../contexts/ToastContext'

export const HistoryPage: React.FC = () => {
  const [selectedStoryId, setSelectedStoryId] = React.useState<string>('')
  const [storySearch, setStorySearch] = React.useState('')
  const toast = useToast()

  const { data: analyses, loading: analysesLoading, error: analysesError } = useAnalysisHistory(
    selectedStoryId
  )

  const handleLoadHistory = () => {
    if (storySearch.trim()) {
      setSelectedStoryId(storySearch.trim().toUpperCase())
      toast.info(`Loading history for ${storySearch.trim().toUpperCase()}`)
    }
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-brand-navy">History</h1>
        <p className="text-sm text-gray-600 mt-1">View past analysis runs and results</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <Card className="lg:col-span-1">
          <CardHeader title="Select Story" />
          <CardBody className="space-y-4">
            <input
              type="text"
              placeholder="Enter Story ID"
              value={storySearch}
              onChange={(e) => setStorySearch(e.target.value.toUpperCase())}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
            />
            <Button variant="primary" fullWidth onClick={handleLoadHistory}>
              Load History
            </Button>
            {selectedStoryId && (
              <div className="p-3 bg-brand-bg rounded-lg">
                <p className="text-xs text-gray-500">Current Story</p>
                <p className="font-medium text-brand-navy text-sm mt-0.5">{selectedStoryId}</p>
              </div>
            )}
          </CardBody>
        </Card>

        <div className="lg:col-span-3">
          {selectedStoryId ? (
            <>
              {analysesError && (
                <Alert type="error" title="Failed to Load History" description={analysesError.message} />
              )}
              {analysesLoading ? (
                <Card className="p-6">
                  <SkeletonLoader />
                </Card>
              ) : analyses && analyses.length > 0 ? (
                <Card>
                  <CardHeader title={`Analyses (${analyses.length})`} />
                  <CardBody className="p-0">
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="bg-brand-bg border-b border-gray-200">
                            <th className="text-left py-3 px-4 font-semibold text-brand-navy">Model</th>
                            <th className="text-left py-3 px-4 font-semibold text-brand-navy">Date</th>
                            <th className="text-left py-3 px-4 font-semibold text-brand-navy">Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {analyses.map((analysis: any, idx: number) => (
                            <tr key={idx} className="border-b border-gray-100">
                              <td className="py-3 px-4">{analysis.model || 'N/A'}</td>
                              <td className="py-3 px-4 text-gray-600">
                                {new Date(analysis.created_at).toLocaleString()}
                              </td>
                              <td className="py-3 px-4">
                                <Badge variant={analysis.status === 'success' ? 'success' : 'warning'}>
                                  {analysis.status || 'pending'}
                                </Badge>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </CardBody>
                </Card>
              ) : (
                <Card className="py-12 text-center">
                  <p className="text-gray-600 text-sm">No analyses found for this story</p>
                </Card>
              )}
            </>
          ) : (
            <Card className="py-12 text-center">
              <p className="text-gray-600 text-sm">Select a story to view its analysis history</p>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
