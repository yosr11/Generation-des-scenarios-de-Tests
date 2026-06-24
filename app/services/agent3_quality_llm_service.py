"""
Agent 3 — LLM qualitative feedback (optional).
Generates a human-readable QA feedback from metrics + tests.
Must NOT change tests and must NOT decide VALID/INVALID.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from app.services.llm_client import call_groq

logger = logging.getLogger(__name__)


def build_quality_payload(
    story_id: str,
    story_summary: str,
    testable_points: List[str],
    tests_compact: List[Dict[str, Any]],
    metrics: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "story_id": story_id,
        "story_summary": (story_summary or "")[:1500],
        "testable_points": testable_points[:25],
        "tests": tests_compact[:20],
        "metrics": metrics,
        "instruction": (
            "Evaluate the overall quality of the manual tests as a QA engineer. "
            "Do NOT invent UI elements. Do NOT rewrite tests. "
            "IMPORTANT: All text values in your JSON response MUST be written in French. "
            "Return only a JSON object with fields: "
            "{score (0-10), summary (1-3 sentences in French), strengths (list in French), "
            "weaknesses (list in French), recommendations (list in French)}."
        ),
    }


def llm_quality_feedback(
    *,
    story_id: str,
    story_summary: str,
    testable_points: List[str],
    tests: List[Dict[str, Any]],
    metrics: Dict[str, Any],
    model_alias: str = "llama4",
) -> Optional[Dict[str, Any]]:
    system = (
        "You are a senior QA reviewer. "
        "Your task is to provide a concise qualitative assessment of test cases. "
        "IMPORTANT: All text values in your JSON response MUST be written in French, "
        "regardless of the language of the input data. "
        "Output ONLY valid JSON, no markdown, no extra text."
    )

    # Compact tests to reduce tokens
    compact = []
    for t in tests:
        compact.append({
            "test_name": t.get("test_name", ""),
            "objective": t.get("objective", ""),
            "steps": [
                {
                    "index": s.get("index"),
                    "action": s.get("action"),
                    "expected_result": s.get("expected_result"),
                }
                for s in (t.get("steps") or [])[:5]
            ],
        })

    user = build_quality_payload(
        story_id=story_id,
        story_summary=story_summary,
        testable_points=testable_points,
        tests_compact=compact,
        metrics=metrics,
    )

    try:
        raw = call_groq(
            system_prompt=system,
            user_prompt=json.dumps(user, ensure_ascii=False),
            model_alias=model_alias,
            temperature=0.2,
            max_tokens=900,
        )
        data = json.loads(raw)
        # basic validation
        if not isinstance(data, dict) or "score" not in data or "summary" not in data:
            return None
        return data
    except Exception as e:
        logger.warning("llm_quality_feedback failed: %s", e)
        return None