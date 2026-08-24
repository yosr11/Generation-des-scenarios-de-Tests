"""Agent 4 — validation QA déterministe avec feedback qualitatif LLM optionnel."""

from __future__ import annotations

from typing import List

from app.models.agent4_validation import Agent4ValidationReport, Agent4ValidationResult
from app.models.test_manual import ManualTestCase
from app.services.agent4_coverage_service import analyze_coverage
from app.services.agent4_prescriptive_service import build_validation_envelope
from app.services.agent4_quality_llm_service import llm_quality_feedback
from app.services.agent4_ambiguity_service import (
    detect_testable_point_contradictions,
)


def validate_and_improve_tests(
    story_id: str,
    testable_points: List[str],
    tests: List[ManualTestCase],
    *,
    story_summary: str = "",
    coverage_threshold: float = 0.70,
    coverage_similarity_threshold: float = 0.7,
    duplicate_similarity_threshold: float = 0.8,
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2",
    run_llm_quality_feedback: bool = True,
    quality_model_alias: str = "nova-lite-2",
) -> Agent4ValidationResult:

    cov = analyze_coverage(
        testable_points, tests, coverage_similarity_threshold, embedding_model
    )

    env = build_validation_envelope(
        tests,
        cov,
        duplicate_similarity_threshold,
        embedding_model,
        coverage_threshold,
    )

    # ── Détection des contradictions entre testable_points (heuristique, pas de LLM) ──
    if testable_points:
        contradictions = detect_testable_point_contradictions(testable_points)
        if contradictions:
            existing_keys = {
                (
                    a.get("test_name", ""),
                    a.get("step_index", 0),
                    a.get("field", ""),
                    a.get("original_text", ""),
                )
                for a in env["ambiguity_findings"]
            }
            for c in contradictions:
                key = (c["test_name"], c["step_index"], c["field"], c["original_text"])
                if key not in existing_keys:
                    env["ambiguity_findings"].append(c)
            from app.services.agent4_prescriptive_service import (
                compute_validation_status,
            )

            env["validation_status"] = compute_validation_status(
                float(cov.coverage_rate),
                coverage_threshold,
                len(env["duplicate_pairs"]),
                len(env["ambiguity_findings"]),
            )

    # Prepare optional LLM qualitative feedback
    quality_payload = None
    if run_llm_quality_feedback:
        # story_summary is already passed as a parameter — use it directly
        metrics = {
            "coverage_rate": float(round(cov.coverage_rate, 4)),
            "covered_count": int(cov.covered_count),
            "total_points": int(cov.total_points),
            "uncovered_points": list(cov.uncovered_points),
            "duplicate_pairs_count": len(env["duplicate_pairs"]),
            "ambiguity_count": len(env["ambiguity_findings"]),
            "validation_status": env["validation_status"],
            "coverage_similarity_threshold": coverage_similarity_threshold,
            "coverage_threshold": coverage_threshold,
            "duplicate_similarity_threshold": duplicate_similarity_threshold,
        }
        tests_raw = [t.model_dump() for t in tests]
        quality_payload = llm_quality_feedback(
            story_id=story_id,
            story_summary=story_summary,
            testable_points=testable_points,
            tests=tests_raw,
            metrics=metrics,
            model_alias=quality_model_alias,
        )

    report = Agent4ValidationReport(
        coverage_rate=round(cov.coverage_rate, 4),
        uncovered_testable_points=list(cov.uncovered_points),
        duplicate_pairs=env["duplicate_pairs"],
        ambiguity_findings=env["ambiguity_findings"],
        validation_status=env["validation_status"],
        correction_instructions=env["correction_instructions"],
        llm_quality_feedback=quality_payload,
        llm_quality_model_alias=quality_model_alias if quality_payload else None,
    )

    sid = story_id or (tests[0].story_id if tests else "")
    return Agent4ValidationResult(story_id=sid, tests=list(tests), report=report)
