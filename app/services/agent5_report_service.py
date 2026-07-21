"""
Agent 5 - Service de Génération de Rapports Finaux.

Synthétise les résultats des agents 1-3 en un rapport structuré et lisible.
Utilise le LLM pour les sections narratives (findings, recommandations, next steps).
Les métriques factuelles (couverture, comptages) restent calculées de manière déterministe.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional


from app.models.agent5_report import (
    Agent5Report,
    ReportCoverageMetrics,
    ReportExecutiveSummary,
    ReportQualityAssurance,
    ReportQualityIssue,
    ReportRecommendation,
    ReportStory,
    ReportTestCase,
    ReportTestSuite,
)
from app.models.analysis import StoryAnalysisResult
from app.models.test_manual import ManualTestGenerationResult
from app.models.agent3_validation import Agent3ValidationResult
from app.services.llm_client import call_llm
from app.prompts.agent5_report_prompt import (
    build_agent5_report_system_prompt,
    build_agent5_report_user_prompt,
)
from app.utils.json_utils import extract_json_from_llm_response

logger = logging.getLogger(__name__)


class Agent5ReportGeneratorService:
    """Génère rapports finaux à partir des résultats d'agents précédents."""

    def __init__(self, llm_client=None, model_name: str = "nova-lite-2"):
        self.llm_client = llm_client
        self.model_alias = model_name

    def _infer_coverage_status(
        self, coverage_rate: float, total_testable_points: int = -1
    ) -> str:
        """Détermine le statut textuel basé sur le taux de couverture.

        Si total_testable_points == 0 → INCOMPLETE_STORY (la story est trop pauvre
        pour produire des points testables, retour PO requis).
        """
        if total_testable_points == 0:
            return "INCOMPLETE_STORY"
        if coverage_rate > 0.85:
            return "EXCELLENT"
        elif coverage_rate > 0.70:
            return "GOOD"
        elif coverage_rate > 0.50:
            return "FAIR"
        else:
            return "POOR"

    def _infer_overall_status(
        self,
        coverage_rate: float,
        validation_status: str,
        duplicate_count: int,
        ambiguity_count: int,
        total_testable_points: int = -1,
    ) -> str:
        """
        Détermine le statut global (APPROVED, REQUIRES_REVIEW, NEEDS_REWORK).

        Règles :
        - APPROVED : couverture ≥85% ET VALID ET duplicates ≤2 ET ambiguities ≤2
        - NEEDS_REWORK : couverture <70% OU INVALID OU duplicates >5 OU ambiguities >5
        - REQUIRES_REVIEW : cas intermédiaires
        """
        # Story incomplète (aucun point testable extrait) → retour PO obligatoire
        if total_testable_points == 0:
            return "NEEDS_REWORK"

        # Quand aucun point testable n'est défini, la couverture n'est pas significative
        # → on ignore le critère de couverture pour le statut global.
        coverage_blocks = total_testable_points != 0 and coverage_rate < 0.70
        coverage_meets_approved = total_testable_points == 0 or coverage_rate >= 0.85

        # Critères bloquants pour NEEDS_REWORK
        if (
            coverage_blocks
            or validation_status == "INVALID"
            or duplicate_count > 5
            or ambiguity_count > 5
        ):
            return "NEEDS_REWORK"

        # Critères pour APPROVED
        if (
            coverage_meets_approved
            and validation_status == "VALID"
            and duplicate_count <= 2
            and ambiguity_count <= 2
        ):
            return "APPROVED"

        # Sinon : REQUIRES_REVIEW
        return "REQUIRES_REVIEW"

    def _extract_key_findings(
        self,
        coverage_rate: float,
        coverage_status: str,
        duplicate_count: int,
        ambiguity_count: int,
        validation_status: str,
        llm_quality_score: Optional[int] = None,
        total_testable_points: int = -1,
    ) -> List[str]:
        """Extrait les top findings pour le résumé exécutif."""
        findings = []

        # Finding 1 : Couverture
        if total_testable_points == 0:
            findings.append(
                "⚠️ Story incomplète : aucun point testable n'a pu être extrait → retour PO requis pour clarifier les exigences"
            )
        else:
            findings.append(f"Couverture : {coverage_rate:.1%} ({coverage_status})")

        # Finding 2 : Validation status
        if validation_status == "INVALID":
            findings.append("❌ Validation échouée - révision requise")
        elif validation_status == "PARTIALLY_VALID":
            findings.append("⚠️ Validation partielle - review recommandée")
        else:
            findings.append("✅ Validation réussie")

        # Finding 3 : Doublons
        if duplicate_count > 5:
            findings.append(
                f"⚠️ Nombreux doublons détectés ({duplicate_count} paires) - fusion recommandée"
            )
        elif duplicate_count > 0:
            findings.append(f"ℹ️ {duplicate_count} doublon(s) sémantique(s) détecté(s)")

        # Finding 4 : Ambiguïtés
        if ambiguity_count > 5:
            findings.append(
                f"⚠️ Plusieurs étapes ambiguës ({ambiguity_count}) - clarification urgente"
            )
        elif ambiguity_count > 0:
            findings.append(f"ℹ️ {ambiguity_count} étape(s) ambiguë(s) identifiée(s)")

        # Finding 5 : Qualité LLM
        if llm_quality_score is not None:
            findings.append(f"Qualité LLM : {llm_quality_score}/10")

        return findings[:5]  # Max 5 findings

    def _extract_recommendations(
        self,
        coverage_rate: float,
        duplicate_count: int,
        ambiguity_count: int,
        validation_status: str,
        uncovered_points: List[str],
        overall_status: str,
        total_testable_points: int = -1,
    ) -> List[ReportRecommendation]:
        """Génère des recommandations basées sur l'état du rapport."""
        recommendations = []

        # Story incomplète : recommandation principale = retour PO
        if total_testable_points == 0:
            recommendations.append(
                ReportRecommendation(
                    priority="critical",
                    action="Retourner la user story au Product Owner pour clarification",
                    rationale=(
                        "Aucun point testable n'a pu être extrait de la story. "
                        "La description, les critères d'acceptation ou les règles métier "
                        "sont insuffisants pour produire des tests vérifiables. "
                        "Demander au PO : acteurs concernés, comportements attendus, "
                        "critères d'acceptation explicites."
                    ),
                )
            )
            return recommendations

        # Recommendations pour couverture basse
        if coverage_rate < 0.50:
            recommendations.append(
                ReportRecommendation(
                    priority="critical",
                    action="Augmenter la couverture des tests (< 50%)",
                    rationale=f"Couverture actuellement à {coverage_rate:.1%}. Générer tests additionnels pour points non couverts.",
                )
            )
        elif coverage_rate < 0.70:
            recommendations.append(
                ReportRecommendation(
                    priority="high",
                    action="Couvrir les points testables manquants",
                    rationale=f"Couverture : {coverage_rate:.1%}. Points à couvrir : {', '.join(uncovered_points[:3])}{'...' if len(uncovered_points) > 3 else ''}",
                )
            )

        # Recommendations pour validation
        if validation_status == "INVALID":
            recommendations.append(
                ReportRecommendation(
                    priority="critical",
                    action="Corriger les erreurs validation détectées",
                    rationale="La suite de tests présente des erreurs bloquantes détectées par l'agent 3.",
                )
            )
        elif validation_status == "PARTIALLY_VALID":
            recommendations.append(
                ReportRecommendation(
                    priority="high",
                    action="Revoir et corriger les tests partiellement valides",
                    rationale="Plusieurs tests ne satisfont pas les critères qualité.",
                )
            )

        # Recommendations pour doublons
        if duplicate_count > 5:
            recommendations.append(
                ReportRecommendation(
                    priority="high",
                    action="Fusionner ou supprimer les tests dupliqués",
                    rationale=f"{duplicate_count} paires dupliquées détectées (similarité > 0.88). Réduire redondance.",
                )
            )
        elif duplicate_count > 2:
            recommendations.append(
                ReportRecommendation(
                    priority="medium",
                    action="Vérifier et consolider les tests similaires",
                    rationale=f"{duplicate_count} doublons sémantiques. Évaluer si fusion/suppression appropriée.",
                )
            )

        # Recommendations pour ambiguïtés
        if ambiguity_count > 5:
            recommendations.append(
                ReportRecommendation(
                    priority="high",
                    action="Clarifier les étapes ambiguës",
                    rationale=f"{ambiguity_count} étapes avec formulations vagues ou imprécises détectées.",
                )
            )
        elif ambiguity_count > 2:
            recommendations.append(
                ReportRecommendation(
                    priority="medium",
                    action="Revoir les étapes ambiguës pour plus de précision",
                    rationale=f"{ambiguity_count} étapes nécessitent clarification (verbes génériques, résultats vagues).",
                )
            )

        # Recommendation finale : next step
        if overall_status == "APPROVED":
            recommendations.append(
                ReportRecommendation(
                    priority="low",
                    action="Suite du pipeline : Déploiement ou exécution des tests",
                    rationale="Suite de tests approuvée et prête pour exécution.",
                )
            )
        elif overall_status == "REQUIRES_REVIEW":
            recommendations.append(
                ReportRecommendation(
                    priority="high",
                    action="Review humain requis avant approbation",
                    rationale="Recommander une revue manuelle par Product Manager ou QA Lead.",
                )
            )
        else:  # NEEDS_REWORK
            recommendations.append(
                ReportRecommendation(
                    priority="critical",
                    action="Régénération / amélioration requise",
                    rationale="Suite insuffisante. Relancer Agent 2 avec feedback ou affiner spécification.",
                )
            )

        return recommendations

    def _generate_narrative_via_llm(
        self,
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
        duplicate_pairs_raw: list,
        ambiguity_findings_raw: list,
        llm_quality_score: Optional[int] = None,
        llm_quality_summary: str = "",
    ) -> Optional[Dict[str, Any]]:
        """
        Appelle le LLM pour générer les sections narratives du rapport.

        Returns:
            Dict avec key_findings, next_steps, recommendations ou None si échec.
        """
        try:
            system_prompt = build_agent5_report_system_prompt()

            # Sérialiser les objets Pydantic en dicts pour le prompt
            dup_dicts = []
            for dp in duplicate_pairs_raw:
                if hasattr(dp, "model_dump"):
                    dup_dicts.append(dp.model_dump())
                elif isinstance(dp, dict):
                    dup_dicts.append(dp)

            amb_dicts = []
            for af in ambiguity_findings_raw:
                if hasattr(af, "model_dump"):
                    amb_dicts.append(af.model_dump())
                elif isinstance(af, dict):
                    amb_dicts.append(af)

            user_prompt = build_agent5_report_user_prompt(
                story_id=story_id,
                story_title=story_title,
                story_type=story_type,
                overall_status=overall_status,
                coverage_rate=coverage_rate,
                coverage_status=coverage_status,
                total_testable_points=total_testable_points,
                covered_points=covered_points,
                uncovered_points=uncovered_points,
                validation_status=validation_status,
                total_tests=total_tests,
                nom_count=nom_count,
                alt_count=alt_count,
                exc_count=exc_count,
                duplicate_pairs=dup_dicts,
                ambiguity_findings=amb_dicts,
                llm_quality_score=llm_quality_score,
                llm_quality_summary=llm_quality_summary,
            )

            raw_response = call_llm(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model_alias=self.model_alias,
                temperature=0.3,
                max_tokens=2000,
            )

            parsed = extract_json_from_llm_response(raw_response)
            logger.info(f"[Agent5] LLM narrative generated for {story_id}")
            return parsed

        except Exception as e:
            logger.warning(
                f"[Agent5] LLM narrative failed for {story_id}, using fallback: {e}"
            )
            return None

    def generate_report(
        self,
        story_analysis: StoryAnalysisResult,
        test_generation: ManualTestGenerationResult,
        validation_result: Agent3ValidationResult,
        story_description: str = "",
        correction_iterations: int = 0,
        max_correction_iterations: int = 0,
    ) -> Agent5Report:
        """
        Génère un rapport complet à partir des résultats des 3 agents.

        Args:
            story_analysis: Résultat Agent 1
            test_generation: Résultat Agent 2
            validation_result: Résultat Agent 3
            story_description: Description complète de la story (pour contexte)

        Returns:
            Agent5Report structuré
        """
        story_id = story_analysis.story_id
        tests = validation_result.tests
        report = validation_result.report

        # Extraire données clés
        coverage_rate = report.coverage_rate
        uncovered_points = report.uncovered_testable_points
        duplicate_pairs = report.duplicate_pairs
        ambiguity_findings = report.ambiguity_findings
        validation_status = report.validation_status
        llm_quality_feedback = report.llm_quality_feedback

        num_tests = len(tests)
        nom_tests = sum(1 for t in tests if t.scenario_type.value == "NOM")
        alt_tests = sum(1 for t in tests if t.scenario_type.value == "ALT")
        exc_tests = sum(1 for t in tests if t.scenario_type.value == "EXC")

        high_priority = sum(1 for t in tests if t.priority.value == "High")

        # Compter points testables couverts
        total_testable_points = len(story_analysis.testable_points)
        covered_points = total_testable_points - len(uncovered_points)

        # Déterminer statuts
        coverage_status = self._infer_coverage_status(
            coverage_rate, total_testable_points
        )
        overall_status = self._infer_overall_status(
            coverage_rate,
            validation_status,
            len(duplicate_pairs),
            len(ambiguity_findings),
            total_testable_points,
        )

        # Construire sections du rapport

        # 1. STORY SUMMARY
        story_section = ReportStory(
            story_id=story_id,
            story_title=story_analysis.story_title,
            story_type=story_analysis.story_type,
            actors=story_analysis.actors,
            actions=story_analysis.actions,
            business_rules=story_analysis.business_rules,
            technical_scope=story_analysis.technical_scope,
        )

        # 2. TEST SUITE
        tests_summary = [
            ReportTestCase(
                test_name=t.test_name,
                objective=t.objective,
                scenario_type=t.scenario_type.value,
                priority=t.priority.value,
                step_count=len(t.steps),
            )
            for t in tests
        ]

        test_suite_section = ReportTestSuite(
            total_tests=num_tests,
            nom_count=nom_tests,
            alt_count=alt_tests,
            exc_count=exc_tests,
            high_priority_count=high_priority,
            tests_summary=tests_summary,
        )

        # 3. COVERAGE METRICS
        coverage_section = ReportCoverageMetrics(
            coverage_rate=round(
                coverage_rate * 100, 1
            ),  # Convert ratio → percentage for display
            total_testable_points=total_testable_points,
            covered_points=covered_points,
            uncovered_points=uncovered_points,
            coverage_status=coverage_status,
        )

        # 4. QUALITY ASSURANCE
        qa_issues = []
        for dup_pair in duplicate_pairs:
            qa_issues.append(
                ReportQualityIssue(
                    issue_type="duplicate",
                    severity="warning" if dup_pair.similarity < 0.95 else "critical",
                    description=f"Tests {dup_pair.test_name_a} et {dup_pair.test_name_b} sont sémantiquement similaires",
                    affected_tests=[dup_pair.test_name_a, dup_pair.test_name_b],
                    recommendation="Fusionner ou clarifier la différence entre les deux tests",
                )
            )

        for ambiguity in ambiguity_findings:
            amb_step = (
                ambiguity.get("step_index", "?")
                if isinstance(ambiguity, dict)
                else getattr(ambiguity, "step_index", "?")
            )
            amb_test = (
                ambiguity.get("test_name", "?")
                if isinstance(ambiguity, dict)
                else getattr(ambiguity, "test_name", "?")
            )
            amb_reason = (
                ambiguity.get("reason", "")
                if isinstance(ambiguity, dict)
                else getattr(ambiguity, "reason", "")
            )
            qa_issues.append(
                ReportQualityIssue(
                    issue_type="ambiguity",
                    severity="warning",
                    description=f"Étape {amb_step} du test {amb_test}: {amb_reason}",
                    affected_tests=[amb_test],
                    recommendation="Clarifier la formulation de l'étape avec des termes précis et vérifiables",
                )
            )

        llm_score = None
        llm_summary = ""
        if llm_quality_feedback:
            llm_score = llm_quality_feedback.score
            llm_summary = llm_quality_feedback.summary

        qa_section = ReportQualityAssurance(
            validation_status=validation_status,
            duplicate_pairs=len(duplicate_pairs),
            ambiguity_count=len(ambiguity_findings),
            issues=qa_issues,
            llm_quality_score=llm_score,
            llm_quality_summary=llm_summary,
        )

        # 5. EXECUTIVE SUMMARY + 6. RECOMMENDATIONS — via LLM avec fallback rule-based
        llm_narrative = self._generate_narrative_via_llm(
            story_id=story_id,
            story_title=story_analysis.story_title,
            story_type=story_analysis.story_type,
            overall_status=overall_status,
            coverage_rate=coverage_rate,
            coverage_status=coverage_status,
            total_testable_points=total_testable_points,
            covered_points=covered_points,
            uncovered_points=uncovered_points,
            validation_status=validation_status,
            total_tests=num_tests,
            nom_count=nom_tests,
            alt_count=alt_tests,
            exc_count=exc_tests,
            duplicate_pairs_raw=duplicate_pairs,
            ambiguity_findings_raw=ambiguity_findings,
            llm_quality_score=llm_score,
            llm_quality_summary=llm_summary,
        )

        if llm_narrative:
            # LLM a répondu — utiliser ses sections narratives
            key_findings = llm_narrative.get("key_findings", [])[:5]
            next_steps = llm_narrative.get("next_steps", [])[:3]

            raw_recs = llm_narrative.get("recommendations", [])
            recommendations = []
            for r in raw_recs:
                if isinstance(r, dict):
                    try:
                        recommendations.append(
                            ReportRecommendation(
                                priority=r.get("priority", "medium"),
                                action=r.get("action", ""),
                                rationale=r.get("rationale", ""),
                            )
                        )
                    except Exception:
                        pass

            processing_notes_llm = (
                f"Sections narratives générées par LLM ({self.model_alias})"
            )
        else:
            # Fallback : rule-based
            key_findings = self._extract_key_findings(
                coverage_rate,
                coverage_status,
                len(duplicate_pairs),
                len(ambiguity_findings),
                validation_status,
                llm_score,
                total_testable_points,
            )

            if total_testable_points == 0:
                next_steps = [
                    "Retourner la story au Product Owner pour clarification",
                    "Demander : acteurs, comportements attendus, critères d'acceptation explicites",
                    "Relancer le pipeline QA une fois la story enrichie",
                ]
            elif overall_status == "APPROVED":
                next_steps = [
                    "Suite prête pour exécution",
                    "Planifier campagne de test",
                    "Documenter résultats",
                ]
            elif overall_status == "REQUIRES_REVIEW":
                next_steps = [
                    "Effectuer review humain",
                    "Clarifier ambiguïtés identifiées",
                    "Évaluer fusion doublons",
                ]
            else:
                next_steps = [
                    "Corriger issues critiques",
                    "Générer tests additionnels pour couverture",
                    "Valider improvements avant re-soumission",
                ]

            recommendations = self._extract_recommendations(
                coverage_rate,
                len(duplicate_pairs),
                len(ambiguity_findings),
                validation_status,
                uncovered_points,
                overall_status,
                total_testable_points,
            )

            processing_notes_llm = (
                "Sections narratives générées en mode rule-based (fallback)"
            )

        executive_summary = ReportExecutiveSummary(
            overall_status=overall_status,
            key_findings=key_findings,
            next_steps=next_steps,
        )

        # Construire rapport final
        now = datetime.utcnow().isoformat() + "Z"

        agent_versions = {
            "agent3_embedding": report.llm_quality_model_alias or "semantic",
            "agent5_model": self.model_alias,
        }

        processing_notes = [processing_notes_llm]
        if test_generation.generation_status.value == "not_generated":
            processing_notes.append(
                "⚠️ Les tests n'ont pas pu être générés. Vérifier spécification."
            )
        if report.llm_quality_model_alias:
            processing_notes.append(
                f"Feedback qualité généré avec modèle: {report.llm_quality_model_alias}"
            )
        if correction_iterations > 0 or max_correction_iterations > 0:
            processing_notes.append(
                f"Itérations de gap-fill (Agent 3 → Agent 2): {correction_iterations}"
                + (
                    f" / {max_correction_iterations} max"
                    if max_correction_iterations
                    else ""
                )
            )

        final_report = Agent5Report(
            story_id=story_id,
            report_title=f"Rapport QA — {story_id}: {story_analysis.story_title}",
            report_version=now[:10].replace("-", "."),  # ex: "2026.06.02"
            generated_timestamp=now,
            executive_summary=executive_summary,
            story_summary=story_section,
            test_suite=test_suite_section,
            coverage_metrics=coverage_section,
            quality_assurance=qa_section,
            recommendations=recommendations,
            agent_versions=agent_versions,
            processing_notes=processing_notes,
        )

        logger.info(
            f"[Agent5] Report generated for {story_id}: status={overall_status}, coverage={coverage_rate:.1%}"
        )

        return final_report

    def export_to_markdown(self, report: Agent5Report) -> str:
        """Exporte le rapport en format Markdown lisible."""

        findings_list = "\n".join(
            f"- {f}" for f in report.executive_summary.key_findings
        )
        next_steps_list = "\n".join(
            f"- {s}" for s in report.executive_summary.next_steps
        )

        actors_str = (
            ", ".join(report.story_summary.actors)
            if report.story_summary.actors
            else "N/A"
        )
        rules_str = (
            ", ".join(report.story_summary.business_rules)
            if report.story_summary.business_rules
            else "N/A"
        )
        tech_str = (
            ", ".join(report.story_summary.technical_scope)
            if report.story_summary.technical_scope
            else "N/A"
        )

        tests_rows = []
        for test in report.test_suite.tests_summary[:10]:
            tests_rows.append(
                f"| {test.scenario_type} | {test.test_name} | {test.priority} | {test.step_count} étapes |"
            )
        if len(report.test_suite.tests_summary) > 10:
            tests_rows.append(
                f"| ... | ... et {len(report.test_suite.tests_summary) - 10} autres | | |"
            )

        tests_table = (
            "\n".join(tests_rows) if tests_rows else "| - | Aucun test | - | - |"
        )

        uncovered_str = (
            ", ".join(report.coverage_metrics.uncovered_points)
            if report.coverage_metrics.uncovered_points
            else "Aucun"
        )

        if report.coverage_metrics.total_testable_points == 0:
            coverage_line = (
                "- **Taux :** ⚠️ Non calculable — **story incomplète**, retour au PO requis "
                "(aucun point testable extrait : description, critères d'acceptation ou règles métier insuffisants)"
            )
        else:
            coverage_line = (
                f"- **Taux :** {report.coverage_metrics.coverage_rate:.1f}% "
                f"({report.coverage_metrics.covered_points}/{report.coverage_metrics.total_testable_points} points)"
            )

        issues_list = ""
        if report.quality_assurance.issues:
            for issue in report.quality_assurance.issues:
                issues_list += f"\n**{issue.issue_type.upper()}** ({issue.severity})\n"
                issues_list += f"- {issue.description}\n"
                issues_list += f"- Recommendation: {issue.recommendation}\n"
        else:
            issues_list = "Aucune issue détectée ✅"

        recommendations_list = ""
        for rec in report.recommendations:
            recommendations_list += f"\n**[{rec.priority.upper()}]** {rec.action}\n"
            recommendations_list += f"- {rec.rationale}\n"

        processing_notes_list = (
            "\n".join(f"- {note}" for note in (report.processing_notes or []))
            or "- Aucune note"
        )

        markdown = f"""
# Rapport QA Complet — {report.story_id}

## 📊 Résumé Exécutif

**Statut Global :** `{report.executive_summary.overall_status}`

### Findings Principaux
{findings_list}

### Prochaines Étapes
{next_steps_list}

---

## 📖 Synthèse User Story

| Propriété | Valeur |
|-----------|--------|
| **ID** | {report.story_id} |
| **Titre** | {report.story_summary.story_title} |
| **Type** | {report.story_summary.story_type} |

**Acteurs :** {actors_str}
**Règles Métier :** {rules_str}
**Périmètre Technique :** {tech_str}

---

## ✅ Suite de Tests Générée

- **Total :** {report.test_suite.total_tests} cas de test
  - NOM (Nominal) : {report.test_suite.nom_count}
  - ALT (Alternatif) : {report.test_suite.alt_count}
  - EXC (Exception) : {report.test_suite.exc_count}
- **Priorités :** Haute: {report.test_suite.high_priority_count}

### Tests (résumé)
| Type | Nom | Priorité | Étapes |
|------|-----|----------|--------|
{tests_table}

---

## 📈 Métriques de Couverture

{coverage_line}
- **Statut :** {report.coverage_metrics.coverage_status}
- **Points Non Couverts :** {uncovered_str}

---

## 🔍 Validation & Assurance Qualité

**Statut Validation :** `{report.quality_assurance.validation_status}`

- Doublons détectés : {report.quality_assurance.duplicate_pairs}
- Ambiguïtés détectées : {report.quality_assurance.ambiguity_count}

### Issues Détectées
{issues_list}

### Qualité LLM
- Score : {report.quality_assurance.llm_quality_score or 'N/A'}/10
- {report.quality_assurance.llm_quality_summary or 'Pas de feedback'}

---

## 💡 Recommandations

{recommendations_list}

---

## ⚙️ Notes de Traitement (Pipeline)

{processing_notes_list}

---

*Rapport généré le {report.generated_timestamp} — Version {report.report_version}*
"""
        return markdown.strip()
