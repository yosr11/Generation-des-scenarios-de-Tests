"""
Appels Agent 2 pour combler les testable_points manquants (Agent 3).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.models.test_manual import ManualTestCase, ManualTestGenerationResult
from app.services.manual_test_generator import ManualTestGeneratorService
from app.services.llm_client import build_llm_client

logger = logging.getLogger(__name__)


def run_agent2_gap_fill(
    story: Dict[str, Any],
    analysis: Dict[str, Any],
    missing_testable_points: List[str],
    current_tests: List[ManualTestCase],
    rag_context: Optional[List[Dict[str, Any]]],
    model_alias: str,
) -> ManualTestGenerationResult:
    llm_client, model_name = build_llm_client(model_alias)
    service = ManualTestGeneratorService(llm_client=llm_client, model_name=model_name)
    existing = [t.model_dump() for t in current_tests]
    return service.generate_gap_coverage_tests(
        story=story,
        analysis=analysis,
        missing_testable_points=missing_testable_points,
        existing_tests=existing,
        rag_context=rag_context,
    )
