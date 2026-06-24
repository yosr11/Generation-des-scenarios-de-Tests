import React from 'react'
import { useStories, useScenarios } from '../hooks'
import { SkeletonLoader } from '../components/ui/Loader'
import { Card, CardBody, CardHeader } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'
import {
  LayoutDashboard, FileText, TestTube,
  Activity, TrendingUp, Wifi, Calendar
} from 'lucide-react'

const STAT_CONFIGS = [
  {
    key: 'stories',
    label: 'Total Stories',
    icon: FileText,
    gradient: 'from-brand-violet to-brand-violetlt',
    glow: 'rgba(124,58,237,0.2)',
  },
  {
    key: 'scenarios',
    label: 'Scénarios Générés',
    icon: TestTube,
    gradient: 'from-brand-rose to-brand-pink',
    glow: 'rgba(244,63,94,0.2)',
  },
  {
    key: 'status',
    label: 'Statut API',
    icon: Wifi,
    gradient: 'from-emerald-500 to-teal-500',
    glow: 'rgba(16,185,129,0.2)',
  },
  {
    key: 'coverage',
    label: 'Couverture',
    icon: TrendingUp,
    gradient: 'from-brand-orange to-brand-orangelt',
    glow: 'rgba(249,115,22,0.2)',
  },
]

export const DashboardPage: React.FC = () => {
  const { data: stories, loading: storiesLoading, error: storiesError } = useStories(true)
  const { data: scenarios, loading: scenariosLoading } = useScenarios()

  const coverage = Math.round(
    ((scenarios?.length || 0) / Math.max(stories?.length || 1, 1)) * 100
  )

  const stats = [
    { key: 'stories',   value: stories?.length || 0 },
    { key: 'scenarios', value: scenarios?.length || 0 },
    { key: 'status',    value: 'Actif' },
    { key: 'coverage',  value: `${coverage}%` },
  ]

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-fade-in">

      {/* Page Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-2xl flex items-center justify-center flex-shrink-0"
          style={{ background: 'var(--grad-violet)' }}>
          <LayoutDashboard size={18} className="text-white" />
        </div>
        <div>
          <h1 className="text-2xl font-extrabold text-brand-navy">Dashboard</h1>
          <p className="text-sm text-brand-muted">Vue d'ensemble de l'activité et des métriques</p>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {STAT_CONFIGS.map((cfg, idx) => {
          const stat = stats.find(s => s.key === cfg.key)
          const Icon = cfg.icon
          return (
            <div
              key={cfg.key}
              className="stat-card p-5 bg-white border border-gray-100 animate-slide-up"
              style={{
                animationDelay: `${idx * 0.08}s`,
                boxShadow: `0 4px 20px ${cfg.glow}`,
              }}
            >
              <div className="flex items-start justify-between mb-4">
                <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${cfg.gradient} flex items-center justify-center`}>
                  <Icon size={18} className="text-white" />
                </div>
                <Activity size={14} className="text-gray-300" />
              </div>
              <p className="text-3xl font-extrabold text-brand-navy leading-none mb-1">
                {storiesLoading || scenariosLoading ? (
                  <span className="inline-block w-12 h-8 bg-gray-100 rounded animate-pulse" />
                ) : (
                  stat?.value
                )}
              </p>
              <p className="text-xs font-semibold text-brand-muted uppercase tracking-widest">{cfg.label}</p>
            </div>
          )
        })}
      </div>

      {/* Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Recent Stories */}
        <Card>
          <CardHeader title="Stories Récentes" accent action={
            <Badge variant="violet" size="sm" dot>Live</Badge>
          } />
          <CardBody className="p-0">
            {storiesLoading || scenariosLoading ? (
              <div className="p-6">
                <SkeletonLoader />
              </div>
            ) : storiesError ? (
              <div className="p-6">
                <p className="text-brand-red text-sm flex items-center gap-2">
                  <span>⚠</span> Échec du chargement des stories
                </p>
              </div>
            ) : stories && stories.length > 0 ? (
              <ul className="divide-y divide-gray-50">
                {stories.slice(0, 5).map((story: any, idx: number) => (
                  <li
                    key={idx}
                    className="px-6 py-3.5 hover:bg-brand-violet/3 transition-colors flex items-center gap-3"
                  >
                    <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                      style={{ background: 'linear-gradient(135deg, rgba(124,58,237,0.1), rgba(244,63,94,0.08))' }}>
                      <FileText size={13} className="text-brand-violet" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-bold text-brand-navy text-sm font-mono">{story.id}</p>
                      <p className="text-xs text-brand-muted truncate mt-0.5">{story.title || 'Sans titre'}</p>
                    </div>
                    <Badge variant="violet" size="sm">Jira</Badge>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="p-6 text-center py-12">
                <FileText size={32} className="text-gray-200 mx-auto mb-2" />
                <p className="text-brand-muted text-sm">Aucune story trouvée</p>
              </div>
            )}
          </CardBody>
        </Card>

        {/* System Info */}
        <Card>
          <CardHeader title="Informations Système" accent action={
            <Badge variant="success" size="sm" dot>Opérationnel</Badge>
          } />
          <CardBody className="p-0">
            {[
              { label: 'Backend API',       value: 'Prêt',                 ok: true },
              { label: 'Version Frontend',  value: '1.0.0',                ok: true },
              { label: 'Moteur IA',         value: 'LangGraph v0.2',       ok: true },
              { label: 'Modèle LLM',        value: 'GPT-4o',               ok: true },
              {
                label: 'Dernière mise à jour',
                value: new Date().toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' }),
                ok: null,
              },
            ].map((item, i) => (
              <div
                key={i}
                className="flex items-center justify-between px-6 py-3.5 border-b border-gray-50 last:border-0 hover:bg-gray-50/50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className={`w-1.5 h-1.5 rounded-full ${
                    item.ok === true  ? 'bg-emerald-400' :
                    item.ok === false ? 'bg-brand-red'   : 'bg-gray-300'
                  }`} />
                  <span className="text-sm text-brand-muted">{item.label}</span>
                </div>
                <span className={`text-sm font-semibold ${
                  item.ok === true ? 'text-emerald-600' :
                  item.ok === null ? 'text-brand-navy'  : 'text-brand-red'
                }`}>
                  {item.value}
                </span>
              </div>
            ))}
          </CardBody>
        </Card>

        {/* Coverage Graph (visual only) */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader title="Couverture des Tests" description="Ratio scénarios générés / stories analysées" accent />
            <CardBody>
              <div className="flex items-end gap-3 h-24 px-2">
                {[35, 58, 72, 45, 89, 70, 65, coverage].map((v, i) => (
                  <div key={i} className="flex-1 flex flex-col items-center gap-1">
                    <div
                      className="w-full rounded-t-lg transition-all duration-500"
                      style={{
                        height: `${v}%`,
                        background: i === 7 ? 'var(--grad-cta)' : 'var(--grad-violet)',
                        opacity: i === 7 ? 1 : 0.4 + (i * 0.07),
                        boxShadow: i === 7 ? 'var(--shadow-glow-rose)' : 'none',
                      }}
                    />
                  </div>
                ))}
              </div>
              <div className="mt-3 flex items-center justify-between text-xs text-brand-muted px-2">
                <span>7 dernières sessions</span>
                <span className="flex items-center gap-1 font-bold text-brand-rose">
                  <TrendingUp size={12} /> Session actuelle : {coverage}%
                </span>
              </div>
            </CardBody>
          </Card>
        </div>

      </div>
    </div>
  )
}
