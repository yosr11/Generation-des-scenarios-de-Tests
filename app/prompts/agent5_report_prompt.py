"""Prompts pour Agent 5 - Génération de Rapports Finaux."""

from typing import Any, Dict, List


def build_agent5_report_system_prompt() -> str:
    return """
Tu es un expert en reporting et synthèse QA. Tu génères les sections NARRATIVES d'un rapport final à partir des métriques calculées par le pipeline de validation d'une User Story Jira.

LANGUE : réponds TOUJOURS en français.

RÔLE :
- Tu reçois des métriques factuelles déjà calculées (couverture, doublons, ambiguïtés, statuts)
- Tu produis des textes de synthèse lisibles par un Product Manager, un QA Lead, et un développeur
- Tu restes FACTUEL : pas d'invention, pas d'interprétation au-delà des données fournies
- Tu es concis et direct, tu utilises des nombres précis

SECTIONS À GÉNÉRER :

1. key_findings (list[str], max 5) :
   - Observations principales synthétisées à partir des métriques
   - Chaque finding = 1 phrase factuelle et précise
   - Mentionner les tests spécifiques quand des noms sont fournis
   - Ex: "La couverture atteint 78% (GOOD) avec 3 points testables non couverts"

2. next_steps (list[str], exactement 3) :
   - Actions prioritaires adaptées au statut global
   - Concrètes et actionables, pas génériques

3. recommendations (list[object]) :
   Chaque recommandation contient :
   - priority : "critical" | "high" | "medium" | "low"
   - action : action recommandée (1 phrase)
   - rationale : justification basée sur les données (1-2 phrases, citer les métriques)

   Règles de priorité :
   - critical : couverture <50%, INVALID, >5 doublons avec sim >0.8
   - high : couverture 50-70%, ambiguïtés non clarifiées, review requis
   - medium : clarifier quelques étapes, merger 1-2 tests similaires
   - low : perfectionnements (améliorer objectifs, revoir labels)

OUTPUT FORMAT :
Retourne un JSON avec exactement ces 3 clés :
{
  "key_findings": ["...", "..."],
  "next_steps": ["...", "...", "..."],
  "recommendations": [
    {"priority": "...", "action": "...", "rationale": "..."},
    ...
  ]
}
""".strip()


def build_agent5_report_user_prompt(
    story_id: str,
    story_title: str,
    story_type: str,
    overall_status: str,
    coverage_rate: float,
    coverage_status: str,
    total_testable_points: int,
    covered_points: int,
    uncovered_points: List[str],
    validation_status: str,
    total_tests: int,
    nom_count: int,
    alt_count: int,
    exc_count: int,
    duplicate_pairs: List[Dict[str, Any]],
    ambiguity_findings: List[Dict[str, Any]],
    llm_quality_score: int = None,
    llm_quality_summary: str = "",
) -> str:
    """
    Construit le prompt utilisateur avec les métriques déjà calculées.
    Le LLM ne calcule rien — il rédige les sections narratives.
    """
    uncovered_str = ", ".join(uncovered_points) if uncovered_points else "Aucun"

    dup_details = ""
    for i, dup in enumerate(duplicate_pairs[:5], 1):
        sim = dup.get("similarity", 0.0)
        name_a = dup.get("test_name_a", "Test A")
        name_b = dup.get("test_name_b", "Test B")
        dup_details += f"  {i}. {name_a} ↔ {name_b} (similarité: {sim:.2f})\n"
    if len(duplicate_pairs) > 5:
        dup_details += f"  ... et {len(duplicate_pairs) - 5} autres paires\n"

    amb_details = ""
    for i, finding in enumerate(ambiguity_findings[:5], 1):
        amb_details += f"  {i}. Étape {finding.get('step_index', '?')} du test {finding.get('test_name', 'N/A')}: {finding.get('reason', 'Ambiguïté')}\n"
    if len(ambiguity_findings) > 5:
        amb_details += f"  ... et {len(ambiguity_findings) - 5} autres\n"

    quality_section = ""
    if llm_quality_score is not None:
        quality_section = f"""
FEEDBACK QUALITÉ LLM :
- Score: {llm_quality_score}/10
- Résumé: {llm_quality_summary}
"""

    prompt = f"""
Génère les sections narratives du rapport pour la story {story_id}.

=== MÉTRIQUES CALCULÉES ===

STORY :
- ID: {story_id}
- Titre: {story_title}
- Type: {story_type}

STATUT GLOBAL : {overall_status}

TESTS :
- Total: {total_tests} cas de test (NOM: {nom_count}, ALT: {alt_count}, EXC: {exc_count})

COUVERTURE :
- Taux: {coverage_rate:.1%} ({coverage_status})
- Points couverts: {covered_points}/{total_testable_points}
- Points NON couverts: {uncovered_str}

VALIDATION :
- Statut: {validation_status}
- Paires dupliquées: {len(duplicate_pairs)}
{dup_details}
- Étapes ambiguës: {len(ambiguity_findings)}
{amb_details}
{quality_section}

=== INSTRUCTIONS ===
Génère key_findings, next_steps et recommendations en JSON.
Adapte le ton et la sévérité des recommandations au statut global ({overall_status}).
"""
    return prompt.strip()


def build_agent5_markdown_formatter() -> str:
    """Template pour formatter le rapport en Markdown lisible."""
    return """
# Rapport QA Complet — {story_id}

## 📊 Résumé Exécutif

**Statut Global :** {overall_status}

### Findings Principaux
{key_findings_list}

### Prochaines Étapes
{next_steps_list}

---

## 📖 Synthèse User Story

| Propriété | Valeur |
|-----------|--------|
| **ID** | {story_id} |
| **Titre** | {story_title} |
| **Type** | {story_type} |

**Acteurs :** {actors}
**Règles Métier :** {business_rules}
**Périmètre Technique :** {technical_scope}

---

## ✅ Suite de Tests Générée

- **Total :** {total_tests} cas de test
  - NOM (Nominal) : {nom_count}
  - ALT (Alternatif) : {alt_count}
  - EXC (Exception) : {exc_count}
- **Priorités :**
  - Haute : {high_count}
  - Moyenne : {medium_count}
  - Basse : {low_count}

{tests_table}

---

## 📈 Métriques de Couverture

- **Taux :** {coverage_rate:.1%} ({covered_points}/{total_testable_points} points)
- **Statut :** {coverage_status}
- **Points Non Couverts :** {uncovered_points_list}

---

## 🔍 Validation & Assurance Qualité

**Statut Validation :** {validation_status}

### Issues Détectées
{issues_list}

### Qualité LLM
- Score : {llm_quality_score}/10
- {llm_quality_summary}

---

## 💡 Recommandations

{recommendations_list}

---

*Rapport généré le {generated_timestamp} — Version {report_version}*
"""
