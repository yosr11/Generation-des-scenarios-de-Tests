"""
Mini-orchestrator for multi-agent test pipeline:
- Agent 1: story analysis (not handled here)
- Agent 2: test generation
- Agent 3: QA validation (coverage, ambiguity, duplicates) — judge only

Handles retry loop externally; Agent 3 returns correction_instructions and validation_status.
"""
from typing import Any, Dict, List, Optional

from app.api.manual_test_generation import generate_manual_tests_for_story_data
from app.services.agent3_test_validator_service import validate_and_improve_tests


def run_pipeline_with_orchestration(
    story: Dict[str, Any],
    analysis: Dict[str, Any],
    max_retries: int = 2,
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2",
    model_alias: str = "qwen3",
) -> Dict[str, Any]:
    """
    Orchestrates Agent 2 then Agent 3; retries Agent 2 while Agent 3 status is not VALID.
    Correction payloads from Agent 3 are collected for injection into future Agent 2 prompts (wiring TBD).
    """
    retry_count = 0
    agent2_prompt_injections: List[Dict[str, Any]] = []
    last_agent3_result = None
    tests: List[Any] = []
    while retry_count <= max_retries:
        gen = generate_manual_tests_for_story_data(
            story,
            analysis,
            model_alias=model_alias,
            use_rag=False,
        )
        tests = list(gen.tests)
        sid = str(story.get("id") or "")
        agent3_result = validate_and_improve_tests(
            sid,
            list(analysis.get("testable_points") or []),
            tests,
            embedding_model=embedding_model,
        )
        last_agent3_result = agent3_result
        report = agent3_result.report
        if report.validation_status == "VALID":
            break
        if retry_count < max_retries and report.validation_status != "VALID":
            agent2_prompt_injections.append(
                {
                    "validation_status": report.validation_status,
                    "correction_instructions": [i.model_dump() for i in report.correction_instructions],
                }
            )
            retry_count += 1
        else:
            break
    return {
        "final_agent3_result": last_agent3_result,
        "retries": retry_count,
        "all_agent2_correction_payloads": agent2_prompt_injections,
        "final_tests": tests,
        "flagged_for_review": last_agent3_result is None
        or last_agent3_result.report.validation_status != "VALID",
    }
