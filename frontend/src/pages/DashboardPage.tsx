import React from 'react'
import { useStories, useScenarios } from '../hooks'
import { SkeletonLoader } from '../components/ui/Loader'
import { Card, CardBody, CardHeader } from '../components/ui/Card'

export const DashboardPage: React.FC = () => {
  const { data: stories, loading: storiesLoading, error: storiesError } = useStories(true)
  const { data: scenarios, loading: scenariosLoading } = useScenarios()

  const stats = [
    { title: 'Total Stories', value: stories?.length || 0 },
    { title: 'Generated Scenarios', value: scenarios?.length || 0 },
    { title: 'API Status', value: 'Active' },
    {
      title: 'Coverage',
      value: Math.round(((scenarios?.length || 0) / Math.max(stories?.length || 1, 1)) * 100) + '%',
    },
  ]

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-brand-navy">Dashboard</h1>
        <p className="text-sm text-gray-600 mt-1">System overview and recent activity</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat, idx) => (
          <Card key={idx}>
            <CardBody>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{stat.title}</p>
              <p className="text-3xl font-bold text-brand-navy mt-1">{stat.value}</p>
            </CardBody>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader title="Recent Stories" />
          <CardBody>
            {storiesLoading || scenariosLoading ? (
              <SkeletonLoader />
            ) : storiesError ? (
              <p className="text-brand-red text-sm">Failed to load stories</p>
            ) : stories && stories.length > 0 ? (
              <ul className="space-y-2">
                {stories.slice(0, 5).map((story: any, idx) => (
                  <li key={idx} className="p-3 rounded-lg bg-brand-bg">
                    <p className="font-medium text-brand-navy text-sm">{story.id}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{story.title || 'No title'}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-gray-500 text-sm">No stories found</p>
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="System Information" />
          <CardBody className="space-y-3 text-sm">
            <div className="flex justify-between py-2 border-b border-gray-100">
              <span className="text-gray-600">Backend API</span>
              <span className="font-medium text-green-600">Ready</span>
            </div>
            <div className="flex justify-between py-2 border-b border-gray-100">
              <span className="text-gray-600">Frontend Version</span>
              <span className="font-medium text-brand-navy">1.0.0</span>
            </div>
            <div className="flex justify-between py-2">
              <span className="text-gray-600">Last Updated</span>
              <span className="font-medium text-brand-navy">{new Date().toLocaleDateString()}</span>
            </div>
          </CardBody>
        </Card>
      </div>
    </div>
  )
}
