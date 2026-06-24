import React from 'react'
import { useAnalysisHistory } from '../hooks'
import { SkeletonLoader } from '../components/ui/Loader'
import { Badge } from '../components/ui/Badge'
import { Alert } from '../components/ui/Alert'

export const HistoryPage: React.FC = () => {
  const [selectedStoryId, setSelectedStoryId] = React.useState<string>('')
  const [storySearch, setStorySearch] = React.useState('')

  const { data: analyses, loading: analysesLoading, error: analysesError } = useAnalysisHistory(
    selectedStoryId
  )

  const handleLoadHistory = () => {
    if (storySearch.trim()) {
      setSelectedStoryId(storySearch.trim().toUpperCase())
    }
  }

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <h1 className="text-3xl font-bold mb-2">📚 History</h1>
      <p className="text-gray-600 mb-8">View past analysis runs and results</p>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left Sidebar - Search */}
        <div className="lg:col-span-1">
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h2 className="text-lg font-semibold mb-4">Select Story</h2>

            <input
              type="text"
              placeholder="Enter Story ID"
              value={storySearch}
              onChange={(e) => setStorySearch(e.target.value.toUpperCase())}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg mb-4 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />

            <button
              onClick={handleLoadHistory}
              className="w-full bg-blue-600 text-white py-2 rounded-lg font-medium hover:bg-blue-700"
            >
              Load History
            </button>

            {selectedStoryId && (
              <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <p className="text-xs text-gray-600">Current Story</p>
                <p className="font-medium text-gray-900 mt-1">{selectedStoryId}</p>
              </div>
            )}
          </div>
        </div>

        {/* Right Side - Results */}
        <div className="lg:col-span-3">
          {selectedStoryId ? (
            <>
              {analysesError && (
                <Alert
                  type="error"
                  title="Failed to Load History"
                  description={analysesError.message}
                />
              )}

              {analysesLoading ? (
                <div className="bg-white border border-gray-200 rounded-lg p-6">
                  <SkeletonLoader />
                </div>
              ) : analyses && analyses.length > 0 ? (
                <div className="bg-white border border-gray-200 rounded-lg p-6">
                  <h3 className="text-lg font-semibold mb-4">Analyses ({analyses.length})</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-gray-200">
                          <th className="text-left py-2 px-3 font-semibold">Model</th>
                          <th className="text-left py-2 px-3 font-semibold">Date</th>
                          <th className="text-left py-2 px-3 font-semibold">Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {analyses.map((analysis: any, idx: number) => (
                          <tr key={idx} className="border-b border-gray-100 hover:bg-gray-50">
                            <td className="py-2 px-3 font-medium">{analysis.model || 'N/A'}</td>
                            <td className="py-2 px-3 text-gray-600">
                              {new Date(analysis.created_at).toLocaleDateString()}{' '}
                              {new Date(analysis.created_at).toLocaleTimeString([], {
                                hour: '2-digit',
                                minute: '2-digit',
                              })}
                            </td>
                            <td className="py-2 px-3">
                              <Badge variant={analysis.status === 'success' ? 'success' : 'warning'}>
                                {analysis.status || 'pending'}
                              </Badge>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
                  <p className="text-gray-600">No analyses found for this story</p>
                </div>
              )}
            </>
          ) : (
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
              <p className="text-gray-600">Select a story to view its analysis history</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}