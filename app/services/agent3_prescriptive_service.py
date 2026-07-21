"""
Agent 3 — agrégation déterministe : statut de validation et instructions de correction structurées.
Aucun LLM, aucune génération, aucune modification des tests.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from app.models.agent3_validation import (
    AddTestInstruction,
    CorrectionInstruction,
    DuplicatePairReport,
    FixObjectiveInstruction,
    FixStepInstruction,
    MergeDuplicatesInstruction,
)
from app.models.test_manual import ManualTestCase
from app.services.agent3_ambiguity_service import detect_ambiguous_steps
from app.services.agent3_coverage_service import CoverageAnalysisResult
from app.services.agent3_duplicate_service import find_semantic_duplicate_removal


def _map_ambiguity_to_preset_reason(field: str, detector_reason: str) -> str:
    d = (detector_reason or "").lower()
    if field == "objective":
        return "vague objective"
    if "résultat attendu vague" in d or "adverbe" in d or "peu observable" in d:
        return "unclear expected result"
    if (
        "non actionnable" in d
        or "étape trop courte" in d
        or "champs non nommés" in d
        or "formulaire" in d
    ):
        return "non-actionable step"
    if "vague" in d or "correctement" in d:
        return "weak measurable criteria"
    return "missing functional precision"


def _duplicate_pair_reports(
    tests: List[ManualTestCase], dup_pairs: List[Tuple[int, int, float]]
) -> Tuple[List[DuplicatePairReport], List[MergeDuplicatesInstruction]]:
    seen: set[Tuple[int, int]] = set()
    reports: List[DuplicatePairReport] = []
    merges: List[MergeDuplicatesInstruction] = []
    for i, j, sim in dup_pairs:
        a, b = (min(i, j), max(i, j))
        if (a, b) in seen:
            continue
        seen.add((a, b))
        na = tests[a].test_name if 0 <= a < len(tests) else str(a)
        nb = tests[b].test_name if 0 <= b < len(tests) else str(b)
        reports.append(
            DuplicatePairReport(
                test_index_a=a,
                test_index_b=b,
                test_name_a=na,
                test_name_b=nb,
                similarity=round(float(sim), 4),
            )
        )
        merges.append(
            MergeDuplicatesInstruction(
                test_index_a=a,
                test_index_b=b,
                test_name_a=na,
                test_name_b=nb,
                similarity=float(sim),
                rationale="Tests sémantiquement redondants : à fusionner en aval (orchestrateur / auteur de tests).",
            )
        )
    return reports, merges


def build_correction_instructions(
    tests: List[ManualTestCase],
    uncovered_points: List[str],
    dup_pairs: List[Tuple[int, int, float]],
    amb_findings_flat: List[Dict[str, Any]],
) -> List[CorrectionInstruction]:
    instructions: List[CorrectionInstruction] = []

    for p in uncovered_points:
        instructions.append(
            AddTestInstruction(
                testable_point=p,
                rationale="Aucun test existant ne couvre ce point testable (similarité sous le seuil).",
            )
        )

    _, merge_instr = _duplicate_pair_reports(tests, dup_pairs)
    instructions.extend(merge_instr)

    for row in amb_findings_flat:
        name = str(row.get("test_name") or "")
        ti = next((i for i, t in enumerate(tests) if t.test_name == name), -1)
        reason = _map_ambiguity_to_preset_reason(
            str(row.get("field") or ""),
            str(row.get("reason") or ""),
        )
        orig = str(row.get("original_text") or "")[:500]
        fld = str(row.get("field") or "")
        if fld == "objective" and ti >= 0:
            instructions.append(
                FixObjectiveInstruction(
                    test_index=ti,
                    test_name=name,
                    rationale=f"{reason}: préciser des critères observables et mesurables.",
                    original_text=orig,
                )
            )
        elif ti >= 0:
            instructions.append(
                FixStepInstruction(
                    test_index=ti,
                    test_name=name,
                    step_index=int(row.get("step_index") or 0),
                    field=fld,
                    rationale=f"{reason}: reformuler en critère observable (pas de vague « correctement »).",
                    original_text=orig,
                )
            )

    return instructions


def compute_validation_status(
    coverage_rate: float,
    coverage_threshold: float,
    duplicate_pairs_count: int,
    ambiguity_count: int,
) -> str:
    if coverage_rate < coverage_threshold:
        return "INVALID"
    if duplicate_pairs_count == 0 and ambiguity_count == 0:
        return "VALID"
    return "PARTIALLY_VALID"


def build_validation_envelope(
    tests: List[ManualTestCase],
    cov: CoverageAnalysisResult,
    duplicate_similarity_threshold: float,
    embedding_model: str,
    coverage_threshold: float,
) -> Dict[str, Any]:
    dup = find_semantic_duplicate_removal(
        tests, duplicate_similarity_threshold, embedding_model
    )
    dup_pairs = dup.pairs_reported

    dup_reports, _ = _duplicate_pair_reports(tests, dup_pairs)

    amb_flat: List[Dict[str, Any]] = []
    for t in tests:
        for f in detect_ambiguous_steps(t):
            amb_flat.append(
                {
                    "test_name": f.test_name,
                    "step_index": f.step_index,
                    "field": f.field,
                    "reason": f.reason,
                    "original_text": f.original_text[:500] if f.original_text else "",
                }
            )

    ambiguity_count = len(amb_flat)
    duplicate_pairs_count = len(dup_reports)
    coverage_rate = float(cov.coverage_rate)

    corr = build_correction_instructions(
        tests, list(cov.uncovered_points), dup_pairs, amb_flat
    )

    validation_status = compute_validation_status(
        coverage_rate, coverage_threshold, duplicate_pairs_count, ambiguity_count
    )

    return {
        "validation_status": validation_status,
        "duplicate_pairs": [r.model_dump() for r in dup_reports],
        "correction_instructions": corr,
        "ambiguity_findings": amb_flat,
    }
