import React from 'react'
import { useStories, useScenarios } from '../hooks'
import { SkeletonLoader } from '../components/ui/Loader'

export const DashboardPage: React.FC = () => {
  const { data: stories, loading: storiesLoading, error: storiesError } = useStories(true)
  const { data: scenarios, loading: scenariosLoading } = useScenarios()

  const stats = [
    {
      title: 'Total Stories',
      value: stories?.length || 0,
      icon: '📚',
    },
    {
      title: 'Generated Scenarios',
      value: scenarios?.length || 0,
      icon: '✓',
    },
    {
      title: 'API Status',
      value: 'Active',
      icon: '🟢',
    },
    {
      title: 'Coverage',
      value: Math.round(((scenarios?.length || 0) / Math.max(stories?.length || 1, 1)) * 100) + '%',
      icon: '⚡',
    },
  ]

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <h1 className="text-3xl font-bold mb-2">📊 Dashboard</h1>
      <p className="text-gray-600 mb-8">System overview and recent activity</p>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {stats.map((stat, idx) => (
          <div key={idx} className="bg-white border border-gray-200 rounded-lg p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">{stat.title}</p>
                <p className="text-3xl font-bold text-gray-900">{stat.value}</p>
              </div>
              <span className="text-4xl">{stat.icon}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Stories */}
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">Recent Stories</h2>
          {storiesLoading ? (
            <SkeletonLoader />
          ) : storiesError ? (
            <p className="text-red-600">Failed to load stories</p>
          ) : stories && stories.length > 0 ? (
            <ul className="space-y-2">
              {stories.slice(0, 5).map((story: any, idx) => (
                <li key={idx} className="p-3 rounded bg-gray-50 hover:bg-gray-100">
                  <p className="font-medium text-gray-900">{story.id}</p>
                  <p className="text-sm text-gray-500 mt-1">{story.title || 'No title'}</p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-gray-500">No stories found</p>
          )}
        </div>

        {/* System Info */}
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">System Information</h2>
          <div className="space-y-3">
            <div className="flex justify-between py-2 border-b border-gray-100">
              <span className="text-gray-600">Backend API</span>
              <span className="font-medium text-green-600">Ready</span>
            </div>
            <div className="flex justify-between py-2 border-b border-gray-100">
              <span className="text-gray-600">Frontend Version</span>
              <span className="font-medium">1.0.0</span>
            </div>
            <div className="flex justify-between py-2">
              <span className="text-gray-600">Last Updated</span>
              <span className="font-medium">{new Date().toLocaleDateString()}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}