import React from 'react'

/* ──────────────────────────────────────────────────────────────
   XrayTestView — Affichage d'un test manuel au format Xray.

   Structure (identique à Jira Xray) :
   - Section « Description » : la liste des TITRES d'étapes,
     chaque ligne « [acteur] <verbe en gras> <reste> ».
   - Une ligne par ÉTAPE dans le tableau :
       Action(s) : « ÉTAPE : [acteur vert] <verbe> <titre> »
                   puis « ACTION(S) : » + liste des actions de l'étape.
       Data | Expected Result (puces imbriquées) | Révision PO.
   - Préconditions rendues comme premières étapes.
   - On respecte TOUT, y compris les valeurs vides ([] / None).
────────────────────────────────────────────────────────────── */

const XRAY_GREEN = '#15803d' // vert acteur (crochets étape)
// Utiliser la même couleur pour les crochets dans la description
const DESC_ACTOR = XRAY_GREEN

/* Formate la priorité au format Xray : P1-High / P2-Medium / P3-Low. */
function formatPriority(priority?: string): string {
  if (!priority) return ''
  const p = priority.trim().toLowerCase()
  if (p.includes('high') || p.includes('haut') || p === 'p1') return 'P1-High'
  if (p.includes('medium') || p.includes('moyen') || p === 'p2') return 'P2-Medium'
  if (p.includes('low') || p.includes('bas') || p.includes('faible') || p === 'p3') return 'P3-Low'
  return priority
}

/* Met en gras le premier mot (le verbe) d'un texte. */
const VerbText: React.FC<{ text: string }> = ({ text }) => {
  const trimmed = (text || '').trim()
  if (!trimmed) return <span className="text-brand-muted">—</span>
  const firstSpace = trimmed.indexOf(' ')
  if (firstSpace === -1) {
    return <strong className="font-semibold text-brand-navy">{trimmed}</strong>
  }
  return (
    <>
      <strong className="font-semibold text-brand-navy">{trimmed.slice(0, firstSpace)}</strong>
      <span className="text-brand-navy">{trimmed.slice(firstSpace)}</span>
    </>
  )
}

/* Crochet acteur — toujours affiché (même vide) pour « respecter les [] ». */
const ActorBracket: React.FC<{ actor?: string; color: string }> = ({ actor, color }) => (
  <span className="font-semibold" style={{ color }}>
    [{actor || ''}]
  </span>
)

/* ── Résultat attendu en puces imbriquées (selon l'indentation). ── */
interface ExpLine {
  level: number
  text: string
}

function parseExpected(value?: string): ExpLine[] {
  if (!value) return []
  return value
    .split('\n')
    .filter((l) => l.trim())
    .map((raw) => {
      const leading = raw.match(/^[\s]*/)?.[0] ?? ''
      const spaces = leading.replace(/\t/g, '  ').length
      const level = Math.min(Math.floor(spaces / 2), 4)
      const text = raw.replace(/^[\s]*[-•*▪◦o]\s*/, '').trim()
      return { level, text }
    })
    .filter((l) => l.text)
}

const BULLETS = ['disc', 'circle', 'square', 'circle', 'disc']

const ExpectedResult: React.FC<{ value?: string }> = ({ value }) => {
  const lines = parseExpected(value)
  if (!lines.length) return <span className="text-brand-muted">—</span>
  return (
    <ul className="space-y-1">
      {lines.map((l, i) => (
        <li
          key={i}
          className="leading-snug"
          style={{
            marginLeft: `${l.level * 1.1}rem`,
            listStyleType: BULLETS[l.level],
            listStylePosition: 'outside',
            display: 'list-item',
          }}
        >
          {l.text}
        </li>
      ))}
    </ul>
  )
}

/* ── Modèle d'une étape agrégée ── */
interface XrayEtape {
  titre: string
  actor: string
  actions: string[]
  data: string
  expected: string
  revision: string
  isPrecondition?: boolean
}

/* Construit les étapes agrégées à partir du test. */
function buildEtapes(test: any): XrayEtape[] {
  const etapes: XrayEtape[] = []

  // Helpers: nettoyer markup simple (asterisques, underscores, balises HTML)
  const cleanText = (t?: string) => {
    if (!t) return ''
    let s = String(t)
    // retirer balises HTML basiques
    s = s.replace(/<[^>]+>/g, '')
    // retirer emphase markdown *text* ou _text_
    s = s.replace(/\*(.*?)\*/g, '$1')
    s = s.replace(/_(.*?)_/g, '$1')
    // normaliser espaces
    return s.trim()
  }

  // Extraire acteur si présent au début du texte entre crochets [acteur] texte...
  const extractActor = (raw?: string) => {
    const s = cleanText(raw)
    const m = s.match(/^\s*\[(.*?)\]\s*(.*)$/)
    if (m) return { actor: m[1].trim(), text: m[2].trim() }
    return { actor: '', text: s }
  }

  // 1) Préconditions → premières étapes.
  const preconditions: string[] = Array.isArray(test.preconditions) ? test.preconditions : []
  preconditions.forEach((pre) => {
    const { actor, text } = extractActor(pre)
    etapes.push({
      titre: `Exécuter la précondition suivante: ${text}`,
      actor: actor || '',
      actions: [],
      data: '',
      expected: '',
      revision: '',
      isPrecondition: true,
    })
  })

  // 2) Étapes groupées (format normal Agent 2).
  const groupes: any[] = Array.isArray(test.étapes) && test.étapes.length ? test.étapes : []
  if (groupes.length) {
    groupes.forEach((g) => {
      const gSteps: any[] = Array.isArray(g.steps) ? g.steps : []
      const actions = gSteps.map((s) => cleanText(s.action || '')).filter(Boolean)
      const datas = gSteps.map((s) => cleanText(s.data || '')).filter(Boolean)
      const expecteds = gSteps.map((s) => cleanText(s.expected_result || '')).filter(Boolean)
      const revisions = gSteps.map((s) => cleanText(s.revision_po || '')).filter(Boolean)

      // titre possible dans g.titre ou dans la première action
      const rawTitle = g.titre || (gSteps[0]?.action ?? '')
      const extracted = extractActor(rawTitle)
      const actorFromGroup = g.actor || extracted.actor || gSteps[0]?.actor || ''
      etapes.push({
        titre: extracted.text || '',
        actor: actorFromGroup,
        actions,
        data: Array.from(new Set(datas)).join('\n'),
        expected: expecteds.join('\n'),
        revision: revisions.join(' · '),
      })
    })
    return etapes
  }

  // 3) Fallback : steps à plat → chaque step devient une étape.
  const flatSteps: any[] = Array.isArray(test.steps) ? test.steps : []
  flatSteps.forEach((s) => {
    const raw = s.action || s.titre || ''
    const { actor, text } = extractActor(raw)
    etapes.push({
      titre: cleanText(text),
      actor: actor || s.actor || '',
      actions: [],
      data: cleanText(s.data || ''),
      expected: cleanText(s.expected_result || ''),
      revision: cleanText(s.revision_po || ''),
    })
  })
  return etapes
}

/* ── Composant principal ── */
export const XrayTestView: React.FC<{ test: any }> = ({ test }) => {
  if (!test) return null

  const etapes = buildEtapes(test)
  const scenarioType = test.scenario_type || 'NOM'
  const labels: string[] = Array.isArray(test.labels) ? test.labels : []

  return (
    <div className="space-y-4">
      {/* Méta du test */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="syn-badge syn-badge--orange">{scenarioType}</span>
        {test.priority && <span className="syn-badge syn-badge--navy">{formatPriority(test.priority)}</span>}
        {labels.map((l, i) => (
          <span key={i} className="syn-badge syn-badge--violet">
            {l}
          </span>
        ))}
      </div>

      {test.objective && (
        <div>
          <p className="syn-label mb-1">Objectif</p>
          <p className="text-sm leading-relaxed text-brand-navy">{test.objective}</p>
        </div>
      )}

      {test.execution_context && (
        <div>
          <p className="syn-label mb-1">Contexte d'exécution</p>
          <p className="text-sm leading-relaxed text-brand-navy">{test.execution_context}</p>
        </div>
      )}

      {/* Description = titres des étapes */}
      {etapes.length > 0 && (
        <div>
          <p className="syn-label mb-2">Description</p>
          <ul className="list-disc space-y-1.5 pl-5">
            {etapes.map((e, i) => (
              <li key={i} className="text-sm leading-snug">
                <ActorBracket actor={e.actor} color={DESC_ACTOR} />{' '}
                <VerbText text={e.titre} />
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Tableau Xray des étapes */}
      <div>
        <p className="syn-label mb-2">Étapes de test (format Xray)</p>
        {etapes.length ? (
          <div className="overflow-hidden rounded-xl border border-brand-navy/[0.08]">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="syn-table-head">
                  <th className="w-10 px-3 py-2.5 text-left">#</th>
                  <th className="px-3 py-2.5 text-left">Action(s)</th>
                  <th className="w-36 px-3 py-2.5 text-left">Data</th>
                  <th className="px-3 py-2.5 text-left">Expected Result</th>
                  <th className="w-28 px-3 py-2.5 text-left">Révision PO</th>
                </tr>
              </thead>
              <tbody>
                {etapes.map((e, i) => (
                  <tr
                    key={i}
                    className="border-t border-brand-navy/[0.06] align-top odd:bg-white even:bg-brand-offwhite/30"
                  >
                    <td className="px-3 py-3 text-xs font-bold text-brand-violet tabular-nums">{i + 1}</td>
                    <td className="px-3 py-3">
                      <p className="leading-snug">
                        <span className="text-[10px] font-bold uppercase tracking-widest text-brand-muted">
                          {e.isPrecondition ? 'PRÉCONDITION' : 'ÉTAPE'}
                        </span>{' '}
                        : <ActorBracket actor={e.actor} color={XRAY_GREEN} />{' '}
                        <VerbText text={e.titre} />
                      </p>
                      {e.actions.length > 0 && (
                        <div className="mt-2">
                          <p className="text-[10px] font-bold uppercase tracking-widest text-brand-muted">
                            ACTION(S) :
                          </p>
                          <ul className="mt-1 list-disc space-y-1 pl-4">
                            {e.actions.map((a, ai) => (
                              <li key={ai} className="leading-snug">
                                <VerbText text={a} />
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </td>
                    <td className="px-3 py-3 font-mono text-xs text-brand-navy whitespace-pre-wrap">
                      {e.data || ''}
                    </td>
                    <td className="px-3 py-3 text-xs text-brand-navy">
                      <ExpectedResult value={e.expected} />
                    </td>
                    <td className="px-3 py-3 text-xs text-brand-muted">{e.revision || 'None'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-brand-muted">Aucune étape.</p>
        )}
      </div>
    </div>
  )
}
