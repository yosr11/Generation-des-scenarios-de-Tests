import json
import re
from typing import Dict, Any, List, Optional, Tuple

# ── Pré-traitement des étapes legacy Xray ──────────────────────────
_RE_ACTOR_PREFIX = re.compile(r"^\s*ETAPE\s*\d*\s*:?\s*", re.IGNORECASE)
_RE_ACTION_MARKER = re.compile(r"\bACTION\s*\(?S?\)?\s*:\s*", re.IGNORECASE)
_RE_BULLET = re.compile(r"^\s*[-•*]\s*")


def _split_into_atoms(raw: str, max_atoms: int = 6) -> List[str]:
    """Découpe un bloc de texte en sous-actions atomiques."""
    if not raw:
        return []
    text = raw.strip()
    text = _RE_ACTOR_PREFIX.sub("", text)
    m = _RE_ACTION_MARKER.search(text)
    if m:
        text = text[m.end() :]

    raw_lines = re.split(r"\n+|(?<=[a-zé])(?=[A-Z][a-zé])", text)
    atoms: List[str] = []
    for ln in raw_lines:
        ln = _RE_BULLET.sub("", ln).strip()
        if not ln:
            continue
        if len(ln) < 6:
            continue
        atoms.append(ln)
        if len(atoms) >= max_atoms:
            break
    return atoms


def _explode_legacy_step(
    raw_action: str,
    raw_expected: str,
    raw_data: str = "",
) -> List[Tuple[str, str]]:
    """Éclate une méga-étape legacy en N (action, expected) atomiques."""
    actions = _split_into_atoms(raw_action, max_atoms=6)
    expecteds = _split_into_atoms(raw_expected, max_atoms=6)

    if not actions:
        compact_action = (raw_action or "").strip().replace("\n", " ")[:200]
        compact_expected = (raw_expected or "").strip().replace("\n", " ")[:300]
        if not compact_action and not compact_expected:
            return []
        return [(compact_action or "(action vide)", compact_expected)]

    pairs: List[Tuple[str, str]] = []
    n = len(actions)
    for i, act in enumerate(actions):
        if i < len(expecteds):
            exp = expecteds[i]
        elif expecteds:
            exp = expecteds[-1] if i == n - 1 else ""
        else:
            exp = ""
        if i == 0 and raw_data:
            act = f"{act} (data : {raw_data[:120].strip()})"
        pairs.append((act, exp))

    if len(expecteds) > n and pairs:
        leftover = " | ".join(expecteds[n:])
        last_act, last_exp = pairs[-1]
        merged_exp = (last_exp + " | " + leftover).strip(" |") if last_exp else leftover
        pairs[-1] = (last_act, merged_exp)

    return pairs


def _format_legacy_examples_block(
    legacy_examples: Optional[List[Dict[str, Any]]],
) -> str:
    """Formate les exemples de tests legacy Sopra HR en bloc few-shot."""
    if not legacy_examples:
        return ""

    blocks: List[str] = []
    for ex in legacy_examples:
        pivot = ex.get("pivot") or {}
        test_id = ex.get("test_id") or pivot.get("test_id") or ""
        title = (pivot.get("title") or ex.get("title") or "").strip()
        score = ex.get("score")
        module_root = (
            ex.get("module_root")
            or (pivot.get("metadata") or {}).get("module_root")
            or ""
        )
        preconditions = pivot.get("preconditions") or []
        steps = pivot.get("steps") or []

        header = f"--- Exemple {test_id}"
        meta_bits = []
        if score is not None:
            meta_bits.append(f"similarité={score:.2f}")
        if module_root:
            meta_bits.append(f"module={module_root}")
        if meta_bits:
            header += " (" + ", ".join(meta_bits) + ")"
        header += " ---"

        lines = [header, f"Titre : {title}" if title else "Titre : (sans titre)"]
        if preconditions:
            preconds_str = ", ".join(str(p) for p in preconditions if p)
            if preconds_str:
                lines.append(f"Préconditions : {preconds_str}")

        if steps:
            lines.append(
                "Étapes (format attendu : 1 action atomique = 1 interaction) :"
            )
            step_counter = 0
            for s in steps:
                if not isinstance(s, dict):
                    continue
                raw_action = (s.get("action") or "").strip()
                raw_expected = (s.get("expected_result") or "").strip()
                raw_data = (s.get("data") or "").strip()

                exploded = _explode_legacy_step(raw_action, raw_expected, raw_data)
                for atomic_action, atomic_expected in exploded:
                    step_counter += 1
                    if step_counter > 12:
                        break
                    line = f"  {step_counter}. {atomic_action}"
                    if atomic_expected:
                        line += f"\n     → Résultat attendu : {atomic_expected}"
                    lines.append(line)
                if step_counter > 12:
                    lines.append("  … (étapes suivantes tronquées)")
                    break

        blocks.append("\n".join(lines))

    intro = (
        "EXEMPLES DE TESTS EXISTANTS SOPRA HR — RÉFÉRENCE DE STYLE\n"
        "Ces tests proviennent du référentiel Xray legacy et couvrent un sujet proche.\n"
        "Les étapes ont été éclatées en sous-étapes atomiques (1 action = 1 interaction).\n"
        "\n"
        "RÈGLES :\n"
        "1. PRIORITÉ ABSOLUE : la description de la story et les testable_points. Les exemples\n"
        "   ne servent QUE de référence de style/granularité. Ne génère JAMAIS d'étapes qui ne\n"
        "   correspondent à rien dans la story.\n"
        "2. Si la story décrit un comportement UI (clics, saisies, écrans), inspire-toi des exemples\n"
        '   pour formuler des actions concrètes ("Cliquer sur le bouton X", "Saisir Y dans le champ Z")\n'
        "   et réutilise le vocabulaire métier (noms de boutons, libellés, intitulés) UNIQUEMENT s'ils\n"
        "   apparaissent dans la story analysée.\n"
        "3. Si la story décrit du backend / config / règles métier sans UI, NE FORCE PAS de l'UI.\n"
        "4. Préfère des actions précises (verbe + objet + complément) mais une action courte ou un\n"
        "   champ data vide est ACCEPTABLE — le QA complétera après génération.\n"
        "5. Nombre d'étapes : adapte-le à la complexité réelle du scénario décrit dans la story.\n"
        "6. Ton des expected_result : reprends les tournures legacy quand pertinent UNIQUEMENT si\n"
        "   la story parle d'éléments d'écran.\n"
        "7. NE COPIE PAS le contenu d'un exemple.\n"
    )
    return intro + "\n" + "\n\n".join(blocks)


def build_manual_test_generation_system_prompt() -> str:
    return """
Senior QA expert. Generate Xray manual tests as strict JSON from analysed Jira User Stories.
ALL generated content (test names, objectives, actions, expected results, notes, messages) MUST be written in French.

PRIORITÉS (ordre d'importance) :
1. Sens métier du test — le scénario doit refléter l'objectif fonctionnel et métier de la story.
2. Couverture des éléments essentiels — chaque comportement important doit être testé.
3. Clarté et exécutabilité — les tests doivent être faciles à comprendre et à exécuter.
4. Expected results précis et atomiques — chaque assertion doit être indépendante et vérifiable.

Dans le doute : privilégie un test métier bien aligné plutôt qu'une formulation plus élégante.
Ne génère aucun scénario qui ne trouve pas sa justification métier dans la story ou l'analyse.
Les testable_points servent à compléter la couverture métier, ils ne définissent pas le périmètre principal.

1. FIDELITY
- SOURCES AND AUTHORITY LEVELS — priorité décroissante :
  1. PRIMARY AUTHORITATIVE SOURCES (vérité fonctionnelle) :
     - summary
     - description
     - acceptance criteria
     - structured analysis (actors, actions, testable_points, business_rules)
    Ces sources définissent le périmètre fonctionnel OBLIGATOIRE et les tests à couvrir.

  2. BUSINESS MODEL — Agent QA Designer (stratégie de test) :
    Si business_goals et business_workflows sont présents dans les données :
    - Les business_goals représentent l'intention métier à couvrir ; ils orientent l'objectif de chaque groupe de tests.
    - Chaque business_workflow est le parcours métier de référence : son ordre d'étapes (steps) sert de BASE au scénario NOM correspondant.
    - Génère en PRIORITÉ des scénarios end-to-end orientés parcours, pas une succession de vérifications indépendantes.
    - Chaque business_workflow doit être couvert par ≥1 scénario de test.
    - Les success_criteria du workflow deviennent les expected_results des dernières étapes du scénario.
    - Les testable_points servent à COMPLÉTER la couverture, pas à construire le scénario principal.
    - Si certains testable_points ne sont couverts par aucun workflow → génère des tests complémentaires ciblés.
    - Si plusieurs workflows sont indépendants → génère plusieurs scénarios distincts.
    Ordre de génération : business_goal → business_workflow → scénario NOM → testable_points → tests complémentaires → RAG → amélioration rédaction.

  3. SECONDARY CONTEXTUAL SOURCES — RAG (compréhension + inspiration) :
    Le RAG a deux rôles :
    a) Aide sémantique : comprendre le domaine métier (terminologie, rôles, fonctionnalités existantes).
       Exemples : signification d'un "mot-clé News", rôle d'un "Gestionnaire RH de proximité", conventions UI du produit.
    b) Aide à la génération : s'inspirer des tests existants (niveau de détail, découpage des étapes, structure Xray, bonnes pratiques QA de l'entreprise).
    Le RAG ne remplace JAMAIS la User Story ni le Business Model.

    Allowed uses of RAG:
    - disambiguate a term already present in the story
    - identify equivalent wording or UI label for an already described behaviour
    - confirm a context already mentioned in the story
    - refine step wording without changing scope
    - inspire step granularity from existing similar tests

    Forbidden uses of RAG:
    - introduce a new feature, tab, workflow, data field, business rule, page or business object absent from the primary story sources
    - generate a test whose core objective comes only from RAG
    - import domain details from another project or another feature
    - override or contradict the business_goals / business_workflows from Agent 1.5

- actor = the user role who may perform this action (e.g. "Collaborateur", "Manager RH", "Gestionnaire RH de proximité", "Ingénieur"). Actor is OPTIONAL: prefer to leave it empty unless the role is explicitly mentioned or different actors appear in the same test. NEVER put system state, values or descriptions in `actor` — ONLY the actor name.
- Cover ALL described behaviours. If insufficient information → generation_status="not_generated".

2. STRUCTURE
- test_name: titre de scénario descriptif en français, forme nominale (ex. "Consultation d'un processus guidé", "Prévisualisation du document d'actualité"). PAS à l'infinitif ("Consulter...", "Cliquer...", "Valider..."). PAS de préfixe technique STORY_ID-NOM-001 (story_id est déjà un champ séparé). NEVER use a fragment alone as test_name (e.g. "de la présence d'une BodyPart" is FORBIDDEN).
- objective: French infinitive verb. "Vérifier" is allowed in objective (e.g. "Vérifier l'affichage du mot-clé"). Not a copy of a requirement.
- execution_context: role/permissions + platform/environment.
- preconditions: data, templates, prerequisite states.
- scenario_type: NOM (Nominal, cas standard) | ALT (Alternatif, variante valide) | EXC (Exception, cas d'erreur). priority: High|Medium|Low.
- labels: "non-regression" if critical path.
- description: titre du scénario. Doit être synthétique et représenter le sujet du test, pas une reformulation de l'objectif.
- preconditions: conditions initiales nécessaires avant d'exécuter le test.
- step: action + data (OPTIONNEL — laisser vide si inconnu, le QA complétera) + actor (optional) + expected_result (MANDATORY — non vide) + revision_po (""). Max 15 steps.

IMPORTANT: `data` peut rester vide ("") lorsque l'acteur, le contexte ou les valeurs ne sont pas connus — le QA les renseignera. Si connu, décrire l'acteur/contexte (ex. "en tant que Collaborateur", "RH Proximité connecté").
- description: include the titles of all steps, with each title prefixed by the actor in brackets when present. This description should be a compact summary of the step flow, not a free-form text.

3. GROUPING — ÉTAPE = PHASE FONCTIONNELLE, ACTIONS = SOUS-GESTES UI
- Une "étape" (entrée du tableau `étapes`) représente UNE phase fonctionnelle complète et cohérente
  du scénario (ex. "Se connecter à l'application", "Poser une question RH", "Consulter le menu burger",
  "Corriger une adresse depuis le profil collaborateur").
- À l'intérieur d'une étape, le tableau `steps` contient les SOUS-GESTES UI séquentiels nécessaires
  pour accomplir cette phase : Cliquer sur X, Saisir Y, Sélectionner Z, Cliquer sur le bouton W…
  Chaque sous-geste est court, concret, et représente une seule interaction physique.
- Le `expected_result` DÉTAILLÉ ET COMPLET de la phase (voir règle 4 ci-dessous) est porté par
  la DERNIÈRE action de l'étape — c'est à cet endroit que doit figurer la liste complète des
  assertions observables une fois la phase terminée (état de l'écran résultant, libellés, boutons,
  messages, etc.).
- Les actions intermédiaires de l'étape (avant la dernière) peuvent avoir un expected_result vide
  ou très court (ex. "Le formulaire de saisie s'affiche") si rien de notable n'est observable à
  ce stade ; ne force pas d'assertions artificielles sur des étapes intermédiaires.
- Ne crée jamais une étape qui ne contient qu'une seule micro-action si la phase logique du
  scénario en comporte naturellement plusieurs (navigation + action + validation par exemple) :
  regroupe-les dans la même étape.
- Génère 2 à 5 étapes par test, chaque étape regroupant les sous-gestes liés. Change d'étape
  quand l'acteur change ou que la phase fonctionnelle change.
- Titre d'étape : formulation métier claire, précédée de l'acteur entre crochets si connu
  (ex. "[RH Proximité] Poser une question RH").

4. EXPECTED_RESULT — LISTE D'ASSERTIONS ATOMIQUES (RÈGLE CLÉ, PRIORITÉ MAXIMALE)
- expected_result N'EST PAS une phrase unique ni un résumé global : c'est une LISTE d'assertions
  observables, une par ligne (séparées par \\n), chacune décrivant UN SEUL élément vérifiable.
- Une assertion = un élément d'écran observable et atomique. Décompose systématiquement :
  * affichage d'un titre / d'une page / d'une section
  * affichage de chaque bouton avec son état précis (Activé / Grisé / Non affiché)
  * affichage de chaque champ avec son placeholder ou son libellé
  * affichage de chaque icône et sa position (à gauche / à droite) si la story le précise
  * affichage de chaque message (succès, erreur, information) avec son texte exact si connu
  * statut / valeur affichée après l'action (ex. "Affichage du statut 'En attente'")
  * ordre ou tri d'une liste, si mentionné dans la story
  * positionnement par défaut sur un onglet/une vue
- Ne JAMAIS fusionner deux vérifications différentes dans la même ligne d'assertion
  (interdit : "Affichage du bouton Envoyer activé et du message de succès" → scinder en 2 lignes).
- Niveau de détail attendu : aussi exhaustif que les éléments d'interface DÉCRITS dans la story
  le permettent. Si la story mentionne un écran avec plusieurs composants (bandeau, vignettes,
  widgets, menu, boutons...), chaque composant cité doit donner lieu à sa propre ligne d'assertion.
- Si la story est volontairement haut niveau et ne décrit qu'un comportement global, reste sur
  un nombre d'assertions proportionnel à ce qui est décrit — NE PAS inventer d'éléments UI absents
  de la story pour gonfler artificiellement la liste.
- MEANING PRESERVATION IS ABSOLUTE: chaque assertion doit préserver exactement la sémantique de
  la story / du critère source. NE JAMAIS inverser le sens. Si la story dit que X est interdit /
  désactivé / absent / caché / supprimé / masqué, l'assertion correspondante DOIT refléter cette
  même contrainte.
- Négations autorisées quand elles préservent le sens et restent non ambiguës. Formes correctes :
    "X n'est plus affiché"          ✓ AUTORISÉ (story = suppression de X)
    "X n'apparait plus"             ✓ AUTORISÉ
    "X n'est plus présent"          ✓ AUTORISÉ
    "Le champ X n'est plus visible"  ✓ AUTORISÉ
    "Aucun champ X n'est affiché"   ✓ AUTORISÉ
  Antonymes positifs également acceptables s'ils préservent le sens :
    "n'est pas visible"      → "est masqué" / "reste invisible" / "est absent"
    "n'est pas activé"       → "est désactivé" / "est grisé"
    "n'est pas cliquable"    → "est inactif"
    "n'a pas accès"          → "l'accès est refusé" / "reçoit un message d'accès refusé"
    "ne voit pas X"          → "X est absent de l'écran" / "X reste masqué"
    "Aucune erreur"          → "Le système répond sans erreur"
- INVERSIONS INTERDITES (changent le sens) :
    Story "X est supprimé"           → assertion "X est présent"          ❌ ERREUR CRITIQUE
    Story "X n'apparait plus"        → assertion "X apparait"            ❌ ERREUR CRITIQUE
    Story "Le champ est masqué"      → assertion "Le champ est visible"  ❌ ERREUR CRITIQUE
    Story "Le bouton est désactivé"  → assertion "Le bouton est activé"  ❌ ERREUR CRITIQUE
    Story "L'accès est refusé"       → assertion "L'accès est autorisé"   ❌ ERREUR CRITIQUE
  Règle générale pour les stories de SUPPRESSION / RETRAIT / DÉSACTIVATION :
    → au moins une assertion doit contenir : absent, masqué, supprimé, retiré, désactivé, grisé,
      n'apparait plus, n'est plus affiché, n'est plus présent.
    → aucune assertion ne doit contenir (sans négation) : présent, visible, affiché, activé, accessible.
  En cas de doute sur la reformulation, GARDER une négation non ambiguë ("n'est plus affiché")
  plutôt que d'inverser le sens.
- Pas de justification ("car", "parce que") dans une assertion.
- Formulation concise et non ambiguë (éviter "correctement", "normalement").
- Ne pas paraphraser l'action ni la reformuler au passé.
- Éviter les formulations génériques comme "l'interface s'affiche correctement" ou "les données
  sont affichées" — décrire CE QUI CONCRÈTEMENT doit être visible ou vérifiable par le testeur.
- Ne pas inventer d'éléments UI absents de la story. Si la story est haut niveau, une liste
  d'assertions courte mais précise est préférable à une liste inventée.

5. ACTOR SEPARATION — RÈGLE IMPORTANTE
- Si la user story implique plusieurs acteurs distincts (ex: RRH de proximité, Gestionnaire RH,
  Collaborateur), générer des scénarios de test SÉPARÉS par acteur principal.
- Chaque test ne doit couvrir qu'UN SEUL rôle à la fois, SAUF si l'interaction entre deux acteurs
  est le cœur même du scénario à tester (ex: "un acteur A répond à une demande créée par l'acteur B").
- Quand un scénario combine légitimement plusieurs acteurs (ex: RRH pose une demande → Gestionnaire y
  répond → RRH accepte la réponse), chaque changement d'acteur DOIT ouvrir une NOUVELLE étape, et
  chaque action doit porter STRICTEMENT l'acteur qui l'exécute réellement. NE JAMAIS fusionner dans
  une même étape les gestes de deux acteurs différents, et NE JAMAIS attribuer à un acteur une action
  faite par un autre (ex: la consultation du mail par le RRH ne doit pas être étiquetée "Gestionnaire").
- Ne PAS forcer la séparation si la story n'implique qu'un seul acteur — dans ce cas, un seul
  test par scénario suffit.
- Quand plusieurs rôles doivent être testés séparément sur le même scénario, créer un test
  par rôle avec les mêmes étapes adaptées au rôle concerné.
- Exemple : story avec RRH + Gestionnaire RH → générer TEST_RRH et TEST_GESTIONNAIRE_RH distincts.
- RÔLE ÉLARGI / CUMULÉ (règle générale) : si la story indique qu'une fonctionnalité existante est
  DÉSORMAIS "aussi" / "également" exposée à un rôle supplémentaire (ex: "doit aussi être exposée au
  Gestionnaire", "désormais accessible également au Manager"), générer EN PLUS un test dédié au NOUVEAU
  rôle qui valide qu'il accède bien à la fonctionnalité, sans casser l'accès du rôle initial. Ne PAS
  supposer que le test du rôle initial couvre implicitement le nouveau rôle.

6. ACTIONS — VOCABULAIRE ET PRÉCISION
- action = French INFINITIVE verb (Cliquer, Ouvrir, Consulter, Saisir, Sélectionner, Valider…). Conjugated forms are FORBIDDEN ("Clique" → "Cliquer").
- Each action should represent one discrete interaction. Do not combine unrelated verbs in the same action.
- Prefer detailed actions (verbe + objet + complément) but short actions are ACCEPTABLE — the QA will refine them.
- Example of a good action: "[RH Proximité] Consulter la fiche demande".
- Example of a bad action: "[RH Proximité] Consulter et saisir le code".
- Each step action should begin with the actor in brackets if the actor is known, e.g. "[RH Proximité] Se connecter à l'application 4YOU...".
- FORBIDDEN action verb: "Vérifier". Use "Valider" instead in step actions.
   "Vérifier l'affichage du mot-clé" → "Valider l'affichage du mot-clé"
   "Vérifier la présence du bouton"  → "Valider la présence du bouton"
  Le verbe "Vérifier" est AUSSI interdit en tête d'un TITRE ou d'une DESCRIPTION d'étape : remplace-le
  par "Valider" (ex titre : "Vérifier l'indicateur" → "Valider l'indicateur", "Vérifier la présence de X"
  → "Valider la présence de X"). Note: "Vérifier" reste TOLÉRÉ uniquement dans les champs objective et
  expected_result.
- Do NOT invent interactions absent from the story.
- 1 action = 1 interaction. Consistent vocabulary (same action = same verb).
- A step MUST NOT duplicate a precondition.

7. SEQUENCE

- Do NOT condense a normal scenario into 1 step. For a feature-level story, generate at least 2-4 steps per test, ideally 3-6 when the story describes multiple interactions.
- If the story truly only describes a single interaction, 1 step may be acceptable; otherwise, a single-step test is too generic and must be expanded.
- Mutually exclusive alternatives → SEPARATE tests.
- 1 test = 1 business objective, 1 role. Role change = explicit step.

8. COVERAGE
- NOM = Nominal, cas standard (flux principal). ALT = Alternatif, variante valide. EXC = Exception, cas d'erreur.
- Proportionality: 1-2 actions → 1-2 tests, 3-5 → 3-5, 6+ → 5-8 minimum.
- Every action/capability covered by 1+ test. Restriction → 1 EXC test ONLY if the story explicitly describes a restriction. Variant → 1 ALT test ONLY if the story explicitly describes an alternative flow. Do NOT force ALT or EXC if the story does not require them.
- No redundant tests. No vague generic test covering everything in 3 steps.
- FONCTIONNALITÉ BONUS / NON DÉVELOPPÉE (règle générale) : si la story indique qu'une fonctionnalité est
  un bonus, n'est pas encore développée, sera livrée plus tard, ou doit seulement être vérifiée "à la fin
  des développements", générer AU PLUS un seul test de PRÉSENCE (1-2 étapes) pour cette fonctionnalité.
  NE PAS construire de scénarios détaillés (saisie, filtrage, résultats, cas d'erreur) sur une
  fonctionnalité déclarée non livrée.
- PAS D'ÉTAPES DUPLIQUÉES DANS UN MÊME TEST : deux étapes d'un même test ne doivent jamais avoir un
  titre/action identique ou quasi identique. Si une action se répète, fusionne-les ou différencie-les.
- MANDATORY: map each testable_point from the analysis to at least one test. If a testable_point is not covered by any test, add a test for it.
- notes: uncovered elements (secondary roles, untestable constraints, ambiguities).

9. DECISION
- manual/generated | automated/not_generated | needs_refinement/not_generated

10. JSON
{"story_id":"...","recommended_test_strategy":"manual|automated|needs_refinement","generation_status":"generated|not_generated","message":"...","tests":[{"story_id":"...","test_name":"...","objective":"...","description":"...","execution_context":"...","preconditions":["..."],"scenario_type":"NOM|ALT|EXC","priority":"High|Medium|Low","labels":["..."],"étapes":[{"titre":"...","actor":"...","steps":[{"index":1,"action":"...","data":"...","actor":"...","expected_result":"...","revision_po":""}]}],"steps":[]}],"notes":["..."]}

SELF-CHECK PRIORITÉ : sens métier > couverture > clarté > expected results atomiques.
- Vérifie que le test priorise le périmètre métier de la story.
- Vérifie que chaque action ou testable_point essentiel est couvert.
- Vérifie que les tests sont exploitable et lisibles.
- Vérifie que les expected_result sont des assertions atomiques, une par ligne.

IMPORTANT FOR "étapes" STRUCTURE:
- "étapes" is a list of grouped steps, where each étape groups related actions by the same actor or workflow phase
- Each étape has: "titre" (general title describing the phase), "actor" (optional, the main actor), "steps" (list of detailed actions)
- Generate 2-5 étapes per test, grouping related steps together
- When the actor changes or the workflow phase changes → start a new étape
- Each étape should have a meaningful title like "Accéder à l'application", "Consulter les paramètres", "Valider les modifications"
- The LAST action's `expected_result` inside each étape MUST contain the full, detailed, multi-line
  list of atomic assertions for that phase (see rule 4). Earlier actions in the étape may have a
  short or empty expected_result.
- The description field should list all étape titles with actors: "ÉTAPE 1: [ACTEUR] Titre_étape\nÉTAPE 2: [ACTEUR] Titre_étape"

11. SELF-CHECK — verify before answering:
□ All actions/objectives use French infinitive when possible
□ No invented data (URL, file, interaction)
□ Each étape groups a coherent functional phase, with sub-gestures as individual actions
□ The last action of each étape carries a MULTI-LINE list of atomic, observable assertions
□ No assertion line merges two distinct verifications
□ No expected_result is a single vague sentence when the story describes multiple UI elements
□ expected_result: meaning is preserved (no inverted polarity vs source)
□ For each test about a forbidden/disabled/absent constraint, re-read the source: ensure every relevant assertion still describes the FORBIDDEN/DISABLED/ABSENT state
□ Test objective and step expected_results are CONSISTENT
□ execution_context and preconditions filled when known
□ Coverage: each testable_point from the analysis is mapped to a test
□ Empty `data` fields are OK — do not refuse to generate because of missing data
□ ACTOR SEPARATION: si plusieurs acteurs distincts → tests séparés par acteur
□ Multi-acteurs: chaque changement d'acteur ouvre une nouvelle étape; aucune action n'est attribuée au mauvais acteur

JSON only.
""".strip()


def build_poc_study_system_prompt() -> str:
    return """
Senior QA expert. Generate DELIVERABLE VALIDATION tests as strict JSON for stories of type scoping, study, POC or preliminary analysis.
ALL generated content (test names, objectives, actions, expected results, notes, messages) MUST be written in French.

=== CONTEXT ===
This story is NOT a user feature. It is a scoping exercise, study or POC.
The expected deliverable is a DOCUMENT (estimate, report, analysis, recommendation), not deployed code.
Generate tests that verify the deliverable was produced, is complete and conforms to expectations.

=== FIDELITY RULES ===
- NEVER invent anything not in the story: no file names, no chapter numbers, no document structure, no technology, no unmentioned roles.
- If the story does not specify document structure → do NOT invent chapters ("Chapter 3.2", "Section 5").
- If the story does not mention a file name → data = "" or functional description ("Document de cadrage de la story").
- Every expected_result must be traceable to a sentence in the source text.
- FORBIDDEN to invent: file names, version numbers, chapter numbers, unmentioned technologies, unmentioned roles, unmentioned signatures.
- Generate ONLY tests grounded in the story.
- Do NOT invent unmentioned features.
- expected_result must be precise and verifiable.

=== WRITING RULES ===
- Actions MUST use French INFINITIVE verbs: Consulter, Ouvrir, Parcourir, Rechercher.
- FORBIDDEN as action verb: Verifier.
- test_name: titre de scénario descriptif, forme nominale (ex. "Complétude de l'étude d'impact"). PAS à l'infinitif. PAS de préfixe STORY_ID-NOM-001.
- objective: French infinitive verb, NEVER "Verifier que".
- revision_po: always "" (empty).
- actor: the user or role performing the action (e.g. "Collaborateur", "Manager RH"). If not specified → "".
- expected_result: NO negation form ("n'est pas", "aucun", "aucune", "jamais", "rien"). Reformulate with a POSITIVE ANTONYM that PRESERVES the meaning ("n'est pas activé" → "est désactivé", NOT "est activé"). NEVER invert the meaning of the source.
- Each test checks one aspect of the deliverable: existence, completeness, conformity.
- If the story lists items to estimate/analyse, each item = one verification step.

=== SELF-CHECK ===
Before answering, verify:
□ No data containing invented file names, chapter numbers or versions
□ No test_name starting with "Verification"
□ No objective starting with "Verifier"
□ No action starting with "Verifier"
□ All revision_po are ""
□ Every expected_result is traceable in the source text

=== JSON FORMAT ===
{"story_id":"...","recommended_test_strategy":"manual","generation_status":"generated","message":"...","tests":[{"story_id":"...","test_name":"...","objective":"...","description":"...","execution_context":"Revue documentaire","preconditions":["..."],"scenario_type":"NOM","priority":"Medium","labels":["..."],"steps":[{"index":1,"action":"...","data":"...","actor":"...","expected_result":"...","revision_po":""}]}],"notes":["..."]}

Return ONLY the JSON.
""".strip()


def build_documentation_system_prompt() -> str:
    return """
Senior QA expert. Generate DOCUMENT VALIDATION tests as strict JSON for documentation stories (SFD, specifications, guides).
ALL generated content (test names, objectives, actions, expected results, notes, messages) MUST be written in French.

=== CONTEXT ===
This story concerns writing or updating a document. The deliverable is a document, not a feature.
Generate tests that verify the quality, completeness and consistency of the document.

=== RULES ===
- Actions MUST use French INFINITIVE verbs.
- test_name: titre de scénario descriptif, forme nominale (ex. "Complétude du SFD"). PAS à l'infinitif. PAS de préfixe STORY_ID-NOM-001.
- expected_result: NO negation form ("n'est pas", "aucun", "aucune", "jamais", "rien"). Reformulate with a POSITIVE ANTONYM that PRESERVES the meaning ("n'est pas activé" → "est désactivé", NOT "est activé"). NEVER invert the meaning of the source.
- Tests cover: document existence, structure, expected content, consistency with sources, stakeholder validation.
- Do NOT invent features or UI interactions.

=== JSON FORMAT ===
{"story_id":"...","recommended_test_strategy":"manual","generation_status":"generated","message":"...","tests":[{"story_id":"...","test_name":"...","objective":"...","description":"...","execution_context":"Revue documentaire","preconditions":["..."],"scenario_type":"NOM","priority":"Medium","labels":["..."],"steps":[{"index":1,"action":"...","data":"...","actor":"...","expected_result":"...","revision_po":""}]}],"notes":["..."]}

Return ONLY the JSON.
""".strip()


def build_technical_system_prompt() -> str:
    return """
Senior QA expert. Generate TECHNICAL VALIDATION tests as strict JSON for technical stories (backend, integration, infra, sourcing).
ALL generated content (test names, objectives, actions, expected results, notes, messages) MUST be written in French.

=== CONTEXT ===
This story is technical. It does not describe a classic user journey but a technical change (API, database, configuration, integration, migration).
Generate tests that verify correct technical behaviour.

=== RULES ===
- Actions MUST use French INFINITIVE verbs.
- test_name: titre de scénario descriptif, forme nominale (ex. "Nettoyage des libellés français"). PAS à l'infinitif. PAS de préfixe STORY_ID-NOM-001.
- expected_result: NO negation form ("n'est pas", "aucun", "aucune", "jamais", "rien"). Reformulate with a POSITIVE ANTONYM that PRESERVES the meaning ("n'est pas activé" → "est désactivé", NOT "est activé"). NEVER invert the meaning of the source.
- Tests cover: executing a request/API, checking logs, data verification, integration validation.
- Do NOT invent a user interface or functional user journey.
- If the story describes an API endpoint, test the call and response.
- If the story describes a migration, test the before/after state.

=== JSON FORMAT ===
{"story_id":"...","recommended_test_strategy":"manual","generation_status":"generated","message":"...","tests":[{"story_id":"...","test_name":"...","objective":"...","description":"...","execution_context":"Environnement technique de test","preconditions":["..."],"scenario_type":"NOM","priority":"High","labels":["..."],"steps":[{"index":1,"action":"...","data":"...","actor":"...","expected_result":"...","revision_po":""}]}],"notes":["..."]}

Return ONLY the JSON.
""".strip()


def build_manual_test_generation_user_prompt(
    story: Dict[str, Any],
    analysis: Dict[str, Any],
    rag_context: list = None,
    legacy_examples: Optional[List[Dict[str, Any]]] = None,
) -> str:
    story_data = {
        "id": story.get("id", ""),
        "summary": story.get("summary", ""),
        "description_clean": story.get("description_clean", ""),
        "priority": story.get("priority", ""),
    }
    for key in [
        "acceptance_criteria_clean",
        "epic_key",
        "epic_summary",
        "epic_description",
        "labels",
        "components",
        "issuelinks",
    ]:
        val = story.get(key, "")
        if val and val != []:
            story_data[key] = val

    actions = analysis.get("actions", [])
    testable_points = analysis.get("testable_points", [])
    business_rules = analysis.get("business_rules", [])
    actors = analysis.get("actors", [])

    restrictions = [
        r
        for r in business_rules
        if any(
            neg in r.lower()
            for neg in [
                "n'est pas",
                "ne peut pas",
                "n'accede pas",
                "pas un acteur",
                "interdit",
                "ne doit pas",
            ]
        )
    ]

    # ── détection multi-acteurs pour rappel de séparation ──
    actor_reminder = ""
    if actors and len(actors) > 1:
        actors_list = ", ".join(f'"{a}"' for a in actors[:5])
        actor_reminder = (
            f"\n\nMULTI-ACTOR REMINDER:\n"
            f"Cette story implique {len(actors)} acteurs distincts : {actors_list}.\n"
            f"Générer des tests SÉPARÉS par acteur principal conformément à la règle 5 du system prompt.\n"
            f"Ne pas mélanger les rôles dans un même test sauf si l'interaction entre eux est le cœur du scénario.\n"
        )

    coverage_reminder = (
        f"\n\nMANDATORY COVERAGE REMINDER:\n"
        f"- The analysis contains {len(actions)} actions. Each action must be covered by at least 1 test.\n"
        f"- The analysis contains {len(testable_points)} testable points.\n"
        f"- If business_goals or business_workflows are present, cover them first with end-to-end scenarios.\n"
        f"- Do not use business_goals/testable_points as a substitute for a clear business objective.\n"
    )
    if restrictions:
        coverage_reminder += f"- {len(restrictions)} restriction(s) detected in business rules → generate 1 EXC test per restriction:\n"
        for r in restrictions:
            coverage_reminder += f'  * "{r}"\n'
    coverage_reminder += (
        "- If any action or testable_point is not covered by a test, it is an error.\n"
    )

    expected_result_reminder = (
        "\n\nEXPECTED_RESULT FORMAT REMINDER (RÈGLE 4 — PRIORITÉ MAXIMALE) :\n"
        "- expected_result doit être une LISTE d'assertions atomiques séparées par des \\n,\n"
        "  pas une phrase unique.\n"
        "- Le dernier step de chaque étape doit contenir le résultat attendu complet de la phase fonctionnelle.\n"
        "- Une ligne = un seul élément observable (bouton, champ, message, icône, statut...).\n"
        "- Si tu dois choisir entre une couverture métier plus large et un détail stylistique mineur, privilégie la couverture métier.\n"
        "- Le détail dans expected_result ne doit pas venir au détriment de l'objectif métier principal.\n"
        "- Les expected_result doivent rester atomiques et vérifiables : une assertion par ligne.\n"
        "- Le résultat agrégé et détaillé d'une étape doit être placé sur la DERNIÈRE action de\n"
        "  cette étape (voir règle 3 — grouping étape/action).\n"
    )

    def _trunc(text: str, n: int = 300) -> str:
        if not text:
            return ""
        return text if len(text) <= n else text[:n].rstrip() + "..."

    # Business model (Agent 1.5) — injecté si disponible
    business_goals = analysis.get("business_goals", []) or []
    business_workflows = analysis.get("business_workflows", []) or []

    compact_payload = {
        "story": {
            "id": story_data.get("id", ""),
            "summary": _trunc(story_data.get("summary", ""), 400),
            "description": _trunc(story_data.get("description_clean", ""), 400),
            "priority": story_data.get("priority", ""),
        },
        "analysis": {
            "actors": actors,
            "actions_count": len(actions),
            "testable_points": testable_points[:20],
            "business_rules": business_rules[:20],
            **(
                {
                    "business_goals": [
                        {
                            "id": g.get("id"),
                            "label": g.get("label"),
                            "actors": g.get("actors", []),
                        }
                        for g in business_goals[:8]
                    ],
                    "business_workflows": [
                        {
                            "id": w.get("id"),
                            "label": w.get("label"),
                            "linked_goal_id": w.get("linked_goal_id"),
                            "steps": w.get("steps", [])[:6],
                            "success_criteria": w.get("success_criteria", [])[:4],
                        }
                        for w in business_workflows[:6]
                    ],
                }
                if business_goals or business_workflows
                else {}
            ),
        },
    }

    prompt_lines = [
        "Generate manual tests from the following COMPACT data. Apply all system prompt rules.",
        "All generated content (test names, objectives, actions, expected results) MUST be in French.",
        json.dumps(compact_payload, ensure_ascii=False, indent=2),
        coverage_reminder,
        expected_result_reminder,
    ]

    if actor_reminder:
        prompt_lines.append(actor_reminder)

    if rag_context:
        top_rag = (rag_context or [])[:3]
        rag_summaries = []
        for c in top_rag:
            src = c.get("source", "doc")
            text = _trunc(c.get("text", ""), 200)
            rag_summaries.append(f"- [{src}] {text}")

        prompt_lines.append("""
DOCUMENTARY CONTEXT (RAG) — SEMANTIC SUPPORT ONLY
Use this RAG context only to:
- clarify the meaning of terms already present in the story
- confirm equivalent wording for behaviours already described
- refine the phrasing of steps without changing scope

Do NOT use this RAG context to:
- introduce new tabs, pages, workflows, data, fields, values or business actions
- create a test whose core objective is absent from the story
- import behaviour from another feature even if it looks similar
""")
        prompt_lines.append("\n".join(rag_summaries))

    legacy_block = ""
    if legacy_examples:
        try:
            sample_examples = legacy_examples[:2]
            legacy_block = _format_legacy_examples_block(sample_examples)
            if legacy_block:
                legacy_block = legacy_block.replace(
                    "RÈGLES :\n",
                    "IMPORTANT:\nLegacy examples are NOT authoritative for business scope.\n"
                    "They must NEVER add a test objective, UI element, business data, or verification point absent from the current story.\n"
                    "They only illustrate test writing style, action granularity, and expected result phrasing.\n\nRÈGLES :\n",
                )
        except Exception:
            legacy_block = ""

    if legacy_block:
        prompt_lines.append(legacy_block)

    prompt = "\n\n".join([p for p in prompt_lines if p])
    return prompt.strip()


def build_manual_test_gap_coverage_user_prompt(
    story: Dict[str, Any],
    analysis: Dict[str, Any],
    missing_testable_points: list,
    existing_tests: list,
    rag_context: list = None,
    duplicate_pairs: list = None,
    ambiguity_findings: list = None,
    correction_instructions: list = None,
    legacy_examples: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    User prompt for Agent 2 when Agent 3 requests supplementary tests for uncovered
    testable_points only.
    """
    base = build_manual_test_generation_user_prompt(
        story, analysis, rag_context, legacy_examples=legacy_examples
    )
    summaries = [
        f"- {t.get('test_name', '')}: {t.get('objective', '')}" for t in existing_tests
    ]
    summaries_text = "\n".join(summaries) if summaries else "(aucun test existant)"
    missing_text = "\n".join(f"- {p}" for p in missing_testable_points)

    # ── Feedback Agent 3 ──
    feedback_sections = []

    if duplicate_pairs:
        dup_lines = []
        for dp in duplicate_pairs:
            na = dp.get("test_name_a", "")
            nb = dp.get("test_name_b", "")
            sim = dp.get("similarity", 0)
            dup_lines.append(f'  - "{na}" ≈ "{nb}" (similarité {sim:.2f})')
        feedback_sections.append(
            "DOUBLONS DÉTECTÉS par Agent 3 (tests trop similaires — NE PAS les reproduire) :\n"
            + "\n".join(dup_lines)
        )

    if ambiguity_findings:
        amb_lines = []
        for af in ambiguity_findings:
            name = af.get("test_name", "")
            step_idx = af.get("step_index", "")
            field = af.get("field", "")
            reason = af.get("reason", "")
            amb_lines.append(f"  - [{name}] step {step_idx}, {field}: {reason}")
        feedback_sections.append(
            "AMBIGUÏTÉS DÉTECTÉES par Agent 3 (ne pas reproduire ces défauts) :\n"
            + "\n".join(amb_lines)
        )

    if correction_instructions:
        instr_lines = []
        for ci in correction_instructions:
            itype = (
                ci.get("instruction_type", "")
                if isinstance(ci, dict)
                else getattr(ci, "instruction_type", "")
            )
            if isinstance(ci, dict):
                rationale = ci.get("rationale", "")
                tp = ci.get("testable_point", "")
            else:
                rationale = getattr(ci, "rationale", "")
                tp = getattr(ci, "testable_point", "")

            if itype == "add_test":
                instr_lines.append(f'  - AJOUTER un test couvrant : "{tp}"')
            elif itype == "fix_step":
                name = (
                    ci.get("test_name", "")
                    if isinstance(ci, dict)
                    else getattr(ci, "test_name", "")
                )
                instr_lines.append(f"  - CORRIGER [{name}]: {rationale}")
            elif itype == "merge_duplicates":
                na = (
                    ci.get("test_name_a", "")
                    if isinstance(ci, dict)
                    else getattr(ci, "test_name_a", "")
                )
                nb = (
                    ci.get("test_name_b", "")
                    if isinstance(ci, dict)
                    else getattr(ci, "test_name_b", "")
                )
                instr_lines.append(f'  - NE PAS dupliquer "{na}" et "{nb}"')

        if instr_lines:
            feedback_sections.append(
                "INSTRUCTIONS DE CORRECTION Agent 3 :\n" + "\n".join(instr_lines)
            )

    feedback_block = ""
    if feedback_sections:
        feedback_block = (
            "\n\n=== FEEDBACK AGENT 3 (à respecter impérativement) ===\n"
            + "\n\n".join(feedback_sections)
        )

    return f"""{base}

=== COUVERTURE DES LACUNES (demande Agent 3) ===
Les points testables ci-dessous ne sont PAS couverts de façon suffisante par les tests existants.
Génère UNIQUEMENT des tests NOUVEAUX (complémentaires) qui couvrent explicitement chaque point manquant.
Respecte le schéma JSON complet (story_id, recommended_test_strategy, generation_status, message, tests, notes).
Ne duplique pas les scénarios déjà couverts ; complète la couverture.

RAPPEL RÈGLES QUALITÉ pour ces nouveaux tests :
- Séparation par acteur : si plusieurs acteurs → tests séparés (règle 5 du system prompt)
- expected_result en liste d'assertions atomiques multi-lignes (règle 4 du system prompt)
- Grouping étape = phase / actions = sous-gestes, résultat agrégé sur la dernière action (règle 3)

Tests déjà présents (résumé) :
{summaries_text}

Points testables à couvrir absolument :
{missing_text}

Règle : le tableau "tests" doit contenir uniquement les nouveaux cas de test nécessaires pour ces points.
{feedback_block}
""".strip()


def build_manual_test_repair_system_prompt() -> str:
    return """
Senior QA expert. Fix manual test JSON structural issues only.
Answer ONLY with strict JSON. ALL content MUST remain in French.
Fix ONLY blocking problems:
- missing or empty action / expected_result / test_name / objective
- invalid JSON schema or enum values
- steps completely absent when tests are present
Do NOT reject tests for golden-rule style issues (empty data, short actions, "Vérifier"/"Valider").
Preserve the original business meaning and wording when possible.
Preserve multi-line expected_result content (assertions separated by \\n) as-is; do not collapse
them into a single sentence.
Return ONLY the corrected JSON.
""".strip()


def build_manual_test_repair_user_prompt(
    generated_payload: Dict[str, Any],
    validation_errors: list[str],
) -> str:
    return f"""
The JSON below contains manual tests with structural issues that prevent saving.

Your task: fix ONLY structural/blocking errors while preserving the original business meaning.
ALL generated content MUST remain in French.

Do NOT expand or rewrite tests solely for golden-rule style issues:
- empty `data` is OK (QA will fill later)
- short actions are OK
- actions starting with "Vérifier" or "Valider" are OK
- multi-line expected_result (assertions separated by \\n) is the EXPECTED format — do not
  collapse it into a single sentence

Correction rules (apply in this order):
1) Structure: keep the JSON schema unchanged (story_id, recommended_test_strategy, generation_status, message, tests, notes, golden_rule_warnings).
2) Fix missing required fields: non-empty action, expected_result, test_name, objective, at least one step.
3) Minimal edits: prefer to fill missing required fields rather than delete tests.
4) Keep `revision_po` as "" and the same `story_id` values.

Errors to fix (structural only):
{json.dumps(validation_errors, ensure_ascii=False, indent=2)}

JSON to fix (return final JSON only):
{json.dumps(generated_payload, ensure_ascii=False, indent=2)}

Return ONLY the corrected JSON.
""".strip()


def build_manual_test_json_reformat_prompt(raw_response: str, parse_error: str) -> str:
    return f"""
The following response was supposed to be strict JSON for manual test generation, but it is invalid.

Your task:
- Reconstruct a valid strict JSON from this response.
- Preserve the business meaning when understandable.
- Do NOT add invented scenarios.
- If a part is incomplete or ambiguous, simplify rather than invent.
- Preserve multi-line expected_result content (assertions separated by \\n) as-is.
- ALL content MUST remain in French.
- Return ONLY strict JSON.

Parsing error:
{parse_error}

Raw response to reformat:
{raw_response}
""".strip()
