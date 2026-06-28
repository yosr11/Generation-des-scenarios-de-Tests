import React from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Zap, GitBranch, Shield, ChevronRight,
  Bot, Layers, BarChart3, ArrowRight, Star
} from 'lucide-react'

const features = [
  {
    icon: Bot,
    title: 'Multi-Agent IA',
    desc: '5 agents spécialisés travaillent en synergie pour une couverture de test maximale.',
    gradient: 'from-rose-500 to-pink-500',
    glow: 'rgba(244,63,94,0.3)',
  },
  {
    icon: Zap,
    title: 'Automatisation avancée',
    desc: 'Du user story Jira aux scénarios de test en quelques secondes, sans effort manuel.',
    gradient: 'from-orange-500 to-red-500',
    glow: 'rgba(249,115,22,0.3)',
  },
  {
    icon: Layers,
    title: 'LangGraph Engine',
    desc: 'Orchestration intelligente des agents via LangGraph pour des résultats cohérents.',
    gradient: 'from-violet-600 to-purple-500',
    glow: 'rgba(124,58,237,0.3)',
  },
]

const stats = [
  { value: '5', label: 'Agents IA', icon: Bot },
  { value: '3', label: 'Itérations', icon: GitBranch },
  { value: '70%', label: 'Couverture', icon: BarChart3 },
  { value: '99%', label: 'Fiabilité', icon: Shield },
]

export const LandingPage: React.FC = () => {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-brand-navy overflow-hidden relative" style={{ fontFamily: 'Outfit, sans-serif' }}>

      {/* ── Orbs de fond ─────────────────────── */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="orb orb-rose w-[600px] h-[600px] top-[-200px] left-[-100px] animate-pulse-glow" />
        <div className="orb orb-violet w-[500px] h-[500px] top-[30%] right-[-150px] animate-pulse-glow" style={{ animationDelay: '2s' }} />
        <div className="orb orb-orange w-[400px] h-[400px] bottom-[-100px] left-[30%] animate-pulse-glow" style={{ animationDelay: '4s' }} />
        {/* Grid overlay */}
        <div className="absolute inset-0" style={{
          backgroundImage: 'linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)',
          backgroundSize: '60px 60px',
        }} />
      </div>

      {/* ── Navbar ───────────────────────────── */}
      <nav className="relative z-20 flex items-center justify-between px-8 py-6 max-w-7xl mx-auto">
        <div className="flex items-center gap-3">
          <img src="/logo_sopra.png" alt="Sopra HR" className="h-8 w-auto object-contain"
            style={{ filter: 'brightness(0) invert(1)', opacity: 0.9 }} />
          <div className="w-px h-5 bg-white/20" />
          <span className="text-xl font-bold text-white">
            Synap<span style={{ color: '#f43f5e' }}>test</span>
          </span>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/login')}
            className="px-5 py-2.5 text-sm font-semibold text-brand-roselt hover:text-white border border-brand-rose/30 hover:border-brand-rose/60 rounded-xl transition-all"
          >
            Se connecter
          </button>
          <button
            onClick={() => navigate('/login')}
            className="btn-primary px-5 py-2.5 text-sm rounded-xl font-bold"
            style={{ background: 'linear-gradient(135deg, #ef4444, #f43f5e, #f97316)', boxShadow: '0 4px 18px rgba(244,63,94,0.45)' }}
          >
            Commencer →
          </button>
        </div>
      </nav>

      {/* ── Hero Section ─────────────────────── */}
      <section className="relative z-10 flex flex-col items-center text-center px-6 pt-20 pb-32 max-w-5xl mx-auto">

        {/* Badge */}
        <div className="animate-fade-in mb-8 inline-flex items-center gap-2 px-4 py-2 rounded-full glass-card border border-white/10 text-sm text-white/80">
          <Star size={14} className="text-brand-orange fill-brand-orange" />
          <span>Plateforme QA nouvelle génération</span>
          <span className="text-brand-rose">•</span>
          <span className="text-brand-orange font-semibold">Sopra HR Software</span>
        </div>

        {/* Headline */}
        <h1 className="animate-slide-up delay-100 text-6xl md:text-7xl font-extrabold text-white leading-[1.1] mb-6">
          Générez vos<br />
          <span className="text-gradient-hero">tests avec IA</span><br />
          en secondes
        </h1>

        {/* Subline */}
        <p className="animate-slide-up delay-200 text-xl text-white/60 max-w-2xl mb-10 leading-relaxed">
          Transformez vos user stories Jira en scénarios de tests exhaustifs grâce à une
          orchestration multi-agents intelligente alimentée par LangGraph.
        </p>

        {/* CTAs */}
        <div className="animate-slide-up delay-300 flex flex-col sm:flex-row gap-4">
          <button
            onClick={() => navigate('/login')}
            className="px-8 py-4 text-base flex items-center gap-2 font-bold text-white rounded-2xl transition-all hover:-translate-y-0.5"
            style={{ background: 'linear-gradient(135deg, #ef4444, #f43f5e, #f97316)', boxShadow: '0 6px 28px rgba(244,63,94,0.5)', outline: '2px solid rgba(255,255,255,0.15)', outlineOffset: '2px' }}
          >
            <Zap size={18} />
            Lancer le pipeline
            <ArrowRight size={16} />
          </button>
          <button
            onClick={() => navigate('/login')}
            className="px-8 py-4 text-base flex items-center gap-2 font-semibold text-brand-roselt rounded-2xl border border-brand-rose/30 hover:border-brand-rose/60 hover:bg-brand-rose/10 transition-all"
          >
            Voir la démo
            <ChevronRight size={16} />
          </button>
        </div>

        {/* Floating preview card */}
        <div className="animate-scale-in delay-400 mt-20 w-full max-w-3xl">
          <div className="glass-card-dark p-6 text-left shadow-float">
            {/* Fake terminal header */}
            <div className="flex items-center gap-2 mb-4">
              <div className="w-3 h-3 rounded-full bg-brand-rose" />
              <div className="w-3 h-3 rounded-full bg-brand-orange" />
              <div className="w-3 h-3 rounded-full bg-green-400" />
              <span className="ml-4 text-xs text-white/40 font-mono">synaptest — pipeline</span>
            </div>
            <div className="space-y-2 font-mono text-sm">
              <div className="flex items-center gap-3">
                <span className="text-brand-violet">[Agent 1]</span>
                <span className="text-white/70">Classifying story NUXEPM-2144...</span>
                <span className="ml-auto text-green-400 text-xs">✓ done</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-brand-pink">[Agent 2]</span>
                <span className="text-white/70">Analysing user story details...</span>
                <span className="ml-auto text-green-400 text-xs">✓ done</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-brand-orange">[Agent 3]</span>
                <span className="text-white/70">Generating test scenarios via RAG...</span>
                <span className="ml-auto animate-pulse text-brand-orange text-xs">● running</span>
              </div>
              <div className="flex items-center gap-3 opacity-40">
                <span className="text-brand-rose">[Agent 5]</span>
                <span className="text-white/50">Quality report generation...</span>
                <span className="ml-auto text-white/30 text-xs">waiting</span>
              </div>
              {/* Progress bar */}
              <div className="mt-4 pt-4 border-t border-white/10">
                <div className="flex justify-between text-xs text-white/40 mb-2">
                  <span>Progression pipeline</span>
                  <span>60%</span>
                </div>
                <div className="progress-track">
                  <div className="progress-fill" style={{ width: '60%' }} />
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Stats Strip ──────────────────────── */}
      <section className="relative z-10 py-12 border-y border-white/08">
        <div className="max-w-4xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-8 px-6">
          {stats.map((stat, i) => (
            <div
              key={i}
              className="animate-fade-in text-center"
              style={{ animationDelay: `${i * 0.1 + 0.5}s` }}
            >
              <p className="text-4xl font-extrabold text-gradient-warm mb-1">{stat.value}</p>
              <p className="text-sm text-white/50 font-medium">{stat.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Features ─────────────────────────── */}
      <section className="relative z-10 py-24 px-6 max-w-6xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-4xl font-bold text-white mb-4">
            Pourquoi <span className="text-gradient-violet">Synaptest</span> ?
          </h2>
          <p className="text-white/50 max-w-xl mx-auto">
            Une architecture multi-agents conçue pour automatiser chaque étape du processus QA.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {features.map((feat, i) => {
            const Icon = feat.icon
            return (
              <div
                key={i}
                className="animate-scale-in glass-card p-8 group hover:-translate-y-2 transition-all duration-300"
                style={{
                  animationDelay: `${i * 0.15}s`,
                  boxShadow: `0 8px 40px ${feat.glow}`,
                }}
              >
                <div className={`w-12 h-12 rounded-2xl bg-gradient-to-br ${feat.gradient} flex items-center justify-center mb-5 group-hover:scale-110 transition-transform`}>
                  <Icon size={22} className="text-white" />
                </div>
                <h3 className="text-white font-bold text-lg mb-3">{feat.title}</h3>
                <p className="text-white/55 text-sm leading-relaxed">{feat.desc}</p>
              </div>
            )
          })}
        </div>
      </section>

      {/* ── CTA Final ────────────────────────── */}
      <section className="relative z-10 py-20 px-6 text-center">
        <div className="max-w-2xl mx-auto glass-card p-12" style={{ boxShadow: 'var(--shadow-glow-rose)' }}>
          <h2 className="text-4xl font-extrabold text-white mb-4">
            Prêt à <span className="text-gradient-warm">révolutionner</span> vos tests ?
          </h2>
          <p className="text-white/55 mb-8">
            Connectez-vous et lancez votre premier pipeline en moins de 2 minutes.
          </p>
          <button
            onClick={() => navigate('/login')}
            className="px-10 py-4 text-base inline-flex items-center gap-3 font-bold text-white rounded-2xl transition-all hover:-translate-y-0.5"
            style={{ background: 'linear-gradient(135deg, #ef4444, #f43f5e, #ec4899)', boxShadow: '0 8px 32px rgba(244,63,94,0.55)', outline: '2px solid rgba(255,255,255,0.12)', outlineOffset: '3px' }}
          >
            <Zap size={18} />
            Commencer maintenant
            <ArrowRight size={16} />
          </button>
        </div>

        {/* Footer */}
        <p className="mt-12 text-white/25 text-sm">
          © 2026 · <span className="text-brand-rose font-semibold">Sopra HR Software</span> · Synaptest Platform
        </p>
      </section>
    </div>
  )
}
