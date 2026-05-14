import json
from typing import Dict, Any


def build_manual_test_generation_system_prompt() -> str:
    return """
Senior QA expert. Generate Xray manual tests as strict JSON from analysed Jira User Stories.
ALL generated content (test names, objectives, actions, expected results, notes, messages) MUST be written in French.

1. FIDELITY
- Sources: summary, description, acceptance criteria, analysis, RAG. NEVER invent anything absent (button, URL, file, email, interaction).
- data = the user (actor) who performs THIS action in THIS step. It answers "WHO does it?" (e.g. "Collaborateur", "Manager RH", "Gestionnaire RH de proximité", "Ingénieur"). MUST be filled in EVERY step, even if the same actor repeats. Take from the story actors or description. NEVER put system state, values or descriptions in data — ONLY the actor name.
- Cover ALL described behaviours. If insufficient information → generation_status="not_generated".

2. STRUCTURE
- test_name: MANDATORY format "[STORY_ID]-[TYPE]-[NNN] Description". Example: "NUXEPM-1344-NOM-001 Acces menu RH". NEVER use a free-text description as test_name (e.g. "de la présence d'une BodyPart" is FORBIDDEN).
- objective: French infinitive verb, NEVER "Verifier". Not a copy of a requirement.
- execution_context: role/permissions + platform/environment.
- preconditions: data, templates, prerequisite states.
- scenario_type: NOM (Nominal, cas standard) | ALT (Alternatif, variante valide) | EXC (Exception, cas d'erreur). priority: High|Medium|Low.
- labels: "non-regression" if critical path.
- step: action + data (optional) + expected_result (mandatory) + revision_po (""). Max 15 steps.

3. STEPS
- action = French INFINITIVE verb (Cliquer, Ouvrir, Saisir...). Conjugated forms are FORBIDDEN ("Clique" → "Cliquer").
- FORBIDDEN as action verb: Verifier → belongs in expected_result.
- Do NOT invent interactions absent from the story.
- expected_result: concrete observable effect. Rules:
  * NO negation anywhere in expected_result: "n'est pas", "ne ... pas", "aucun", "aucune", "jamais", "rien" are ALL FORBIDDEN. Rephrase positively (e.g. "n'est pas visible" → "est masqué", "Aucune erreur" → "Le système fonctionne sans erreur", "Aucun résultat" → "La liste est vide").
  * NO justification ("car", "parce que")
  * Concise, unambiguous (not "correctement", "normalement")
  * Do NOT paraphrase the action or restate it in past tense
- 1 action = 1 interaction. Consistent vocabulary (same action = same verb).
- A step MUST NOT duplicate a precondition.

4. SEQUENCE
- Realistic flow: login → navigation → action → result.
- Do NOT condense into 1-2 steps. Mutually exclusive alternatives → SEPARATE tests.
- 1 test = 1 business objective, 1 role. Role change = explicit step.

5. COVERAGE
- NOM = Nominal, cas standard (flux principal). ALT = Alternatif, variante valide. EXC = Exception, cas d'erreur.
- Proportionality: 1-2 actions → 1-2 tests, 3-5 → 3-5, 6+ → 5-8 minimum.
- Every action/capability covered by 1+ test. Restriction → 1 EXC test. Variant → 1 ALT test.
- No redundant tests. No vague generic test covering everything in 3 steps.
- notes: uncovered elements (secondary roles, untestable constraints, ambiguities).

6. DECISION
- manual/generated | automated/not_generated | needs_refinement/not_generated

7. JSON
{"story_id":"...","recommended_test_strategy":"manual|automated|needs_refinement","generation_status":"generated|not_generated","message":"...","tests":[{"story_id":"...","test_name":"...","objective":"...","execution_context":"...","preconditions":["..."],"scenario_type":"NOM|ALT|EXC","priority":"High|Medium|Low","labels":["..."],"steps":[{"index":1,"action":"...","data":"...","expected_result":"...","revision_po":""}]}],"notes":["..."]}

8. SELF-CHECK — verify before answering:
□ All actions/objectives use French infinitive, never "Verifier"
□ No invented data (URL, file, interaction)
□ expected_result: no negation, no justification, no paraphrase
□ execution_context and preconditions filled
□ Coverage: each action = 1+ test, restriction = 1 EXC
□ Notes non-empty if elements are uncovered

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
- test_name: MANDATORY format "[STORY_ID]-[TYPE]-[NNN] Description". Example: "YOU-13032-NOM-001 Completude etude impact". NEVER use a free-text description alone as test_name.
- objective: French infinitive verb, NEVER "Verifier que".
- revision_po: always "" (empty).
- data: only information PRESENT in the story. If nothing specific → "".
- expected_result: NO negation ("n'est pas", "aucun", "aucune", "jamais", "rien" are FORBIDDEN). Rephrase positively.
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
{"story_id":"...","recommended_test_strategy":"manual","generation_status":"generated","message":"...","tests":[{"story_id":"...","test_name":"...","objective":"...","execution_context":"Revue documentaire","preconditions":["..."],"scenario_type":"NOM","priority":"Medium","labels":["..."],"steps":[{"index":1,"action":"...","data":"...","expected_result":"...","revision_po":""}]}],"notes":["..."]}

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
- test_name: MANDATORY format "[STORY_ID]-[TYPE]-[NNN] Description". Example: "NUXEPM-2110-NOM-001 Completude du SFD". NEVER use a free-text description alone as test_name.
- expected_result: NO negation ("n'est pas", "aucun", "aucune", "jamais", "rien" are FORBIDDEN). Rephrase positively.
- Tests cover: document existence, structure, expected content, consistency with sources, stakeholder validation.
- Do NOT invent features or UI interactions.

=== JSON FORMAT ===
{"story_id":"...","recommended_test_strategy":"manual","generation_status":"generated","message":"...","tests":[{"story_id":"...","test_name":"...","objective":"...","execution_context":"Revue documentaire","preconditions":["..."],"scenario_type":"NOM","priority":"Medium","labels":["..."],"steps":[{"index":1,"action":"...","data":"...","expected_result":"...","revision_po":""}]}],"notes":["..."]}

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
- test_name: MANDATORY format "[STORY_ID]-[TYPE]-[NNN] Description". Example: "NUXEPM-2430-NOM-001 Nettoyage libelles francais". NEVER use a free-text description alone as test_name.
- expected_result: NO negation ("n'est pas", "aucun", "aucune", "jamais", "rien" are FORBIDDEN). Rephrase positively.
- Tests cover: executing a request/API, checking logs, data verification, integration validation.
- Do NOT invent a user interface or functional user journey.
- If the story describes an API endpoint, test the call and response.
- If the story describes a migration, test the before/after state.

=== JSON FORMAT ===
{"story_id":"...","recommended_test_strategy":"manual","generation_status":"generated","message":"...","tests":[{"story_id":"...","test_name":"...","objective":"...","execution_context":"Environnement technique de test","preconditions":["..."],"scenario_type":"NOM","priority":"High","labels":["..."],"steps":[{"index":1,"action":"...","data":"...","expected_result":"...","revision_po":""}]}],"notes":["..."]}

Return ONLY the JSON.
""".strip()


def build_manual_test_generation_user_prompt(
    story: Dict[str, Any],
    analysis: Dict[str, Any],
    rag_context: list = None,
) -> str:
    story_data = {
        "id": story.get("id", ""),
        "summary": story.get("summary", ""),
        "description_clean": story.get("description_clean", ""),
        "priority": story.get("priority", ""),
    }
    # Include optional fields only if non-empty
    for key in ["acceptance_criteria_clean", "epic_key", "epic_summary", "epic_description", "labels", "components", "issuelinks"]:
        val = story.get(key, "")
        if val and val != []:
            story_data[key] = val

    payload = {
        "story": story_data,
        "analysis": analysis,
    }

    # Compter les actions et restrictions pour rappeler la couverture attendue
    actions = analysis.get("actions", [])
    testable_points = analysis.get("testable_points", [])
    business_rules = analysis.get("business_rules", [])

    # Détecter les restrictions (business rules négatives)
    restrictions = [r for r in business_rules if any(neg in r.lower() for neg in ["n'est pas", "ne peut pas", "n'accede pas", "pas un acteur", "interdit", "ne doit pas"])]

    coverage_reminder = (
        f"\n\nMANDATORY COVERAGE REMINDER:\n"
        f"- The analysis contains {len(actions)} actions. Each action must be covered by at least 1 test.\n"
        f"- The analysis contains {len(testable_points)} testable points.\n"
    )
    if restrictions:
        coverage_reminder += f"- {len(restrictions)} restriction(s) detected in business rules → generate 1 EXC test per restriction:\n"
        for r in restrictions:
            coverage_reminder += f"  * \"{r}\"\n"
    
    coverage_reminder += "- If any action or testable_point is not covered by a test, it is an error.\n"

    prompt = f"""
Generate manual tests from the following data. Apply all system prompt rules.
All generated content (test names, objectives, actions, expected results) MUST be in French.

{json.dumps(payload, ensure_ascii=False, indent=2)}
{coverage_reminder}
"""

    if rag_context:
        rag_text = "\n".join(
            f"- [{c.get('source', 'doc')}] {c.get('text', '')}" for c in rag_context
        )
        prompt += f"""

DOCUMENTARY CONTEXT (RAG) — Use this information to enrich and refine test steps:
{rag_text}
"""

    return prompt.strip()


def build_manual_test_gap_coverage_user_prompt(
    story: Dict[str, Any],
    analysis: Dict[str, Any],
    missing_testable_points: list,
    existing_tests: list,
    rag_context: list = None,
) -> str:
    """
    User prompt for Agent 2 when Agent 3 requests supplementary tests for uncovered
    testable_points only. Reuses the standard user payload then adds explicit gap instructions.
    """
    base = build_manual_test_generation_user_prompt(story, analysis, rag_context)
    summaries = [
        f"- {t.get('test_name', '')}: {t.get('objective', '')}"
        for t in existing_tests
    ]
    summaries_text = "\n".join(summaries) if summaries else "(aucun test existant)"
    missing_text = "\n".join(f"- {p}" for p in missing_testable_points)
    return f"""{base}

=== COUVERTURE DES LACUNES (demande Agent 3) ===
Les points testables ci-dessous ne sont PAS couverts de façon suffisante par les tests existants.
Génère UNIQUEMENT des tests NOUVEAUX (complémentaires) qui couvrent explicitement chaque point manquant.
Respecte le schéma JSON complet (story_id, recommended_test_strategy, generation_status, message, tests, notes).
Ne duplique pas les scénarios déjà couverts ; complète la couverture.

Tests déjà présents (résumé) :
{summaries_text}

Points testables à couvrir absolument :
{missing_text}

Règle : le tableau "tests" doit contenir uniquement les nouveaux cas de test nécessaires pour ces points.
""".strip()


def build_manual_test_repair_system_prompt() -> str:
    return """
Senior QA expert. Fix manual test JSON so it complies with golden rules.
Answer ONLY with strict JSON. ALL content MUST remain in French.
Key rules:
- action must start with a French infinitive verb (Cliquer, Ouvrir, Consulter, Saisir, etc.).
- "Verifier" is FORBIDDEN as an action or at the start of an objective.
- objective must start with a French action verb.
- Test data must be concrete, not vague placeholders.
- expected_result must describe an observable effect, not repeat the action.
- 1 test = 1 business objective. Do not mix different behaviours.
- Do not mix different roles in the same test.
- Do not invent unjustified ALT or EXC scenarios.
Return ONLY the corrected JSON.
""".strip()


def build_manual_test_repair_user_prompt(
  generated_payload: Dict[str, Any],
  validation_errors: list[str],
) -> str:
  return f"""
The JSON below contains manual tests that are almost correct, but some golden rules are not respected.

Your task: fix the existing JSON without changing the business meaning unnecessarily.
ALL generated content MUST remain in French.

Correction rules:
- Keep the JSON structure exactly as-is.
- Fix only what is needed to comply with golden rules.
- Replace any action starting with "Verifier" with a concrete user action.
- Replace any objective starting with "Verifier" with an action-verb objective.
- Replace vague test data with concrete, realistic data.
- Move expected observations into expected_result.
- Fix redundant tests or unclear objectives if needed.
- Do not mix incompatible roles in the same test.
- Remove any invented ALT or EXC test not clearly justified by the story.
- Do not delete a full test if a simple rewording suffices.
- Keep the same story_id.
- Return ONLY the final corrected JSON.

Errors to fix:
{json.dumps(validation_errors, ensure_ascii=False, indent=2)}

JSON to fix:
{json.dumps(generated_payload, ensure_ascii=False, indent=2)}
""".strip()


def build_manual_test_json_reformat_prompt(raw_response: str, parse_error: str) -> str:
  return f"""
The following response was supposed to be strict JSON for manual test generation, but it is invalid.

Your task:
- Reconstruct a valid strict JSON from this response.
- Preserve the business meaning when understandable.
- Do NOT add invented scenarios.
- If a part is incomplete or ambiguous, simplify rather than invent.
- ALL content MUST remain in French.
- Return ONLY strict JSON.

Parsing error:
{parse_error}

Raw response to reformat:
{raw_response}
""".strip()
