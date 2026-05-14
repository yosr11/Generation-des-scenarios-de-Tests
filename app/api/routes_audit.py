"""
Agent 3 : audit heuristique des formulations vagues (routes historiques `/audit/...`).
Pour le validateur complet (couverture, doublons, ambiguïtés, instructions de correction), voir `/agent3/...`.
"""

import re
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from app.utils.json_utils import load_json
from app.models.test_manual import ManualTestCase, ManualTestStep
from app.repositories.analysis_repository import get_latest_analysis
from app.repositories.story_repository import get_story_by_id
from app.models.analysis import StoryAnalysisResult
from app.api.manual_test_generation import generate_manual_tests

# Expressions vagues à détecter
VAGUE_PATTERNS = [
    r"\bvérifier que\b",
    r"\bs'assurer que\b",
    r"\bvalider que\b",
    r"\bconfirmer que\b",
    r"\bcontrôler que\b",
    r"\bvérifier\b(?!\s+que)",  # "vérifier" seul
]

VAGUE_REGEX = [re.compile(p, re.IGNORECASE) for p in VAGUE_PATTERNS]

class VagueTestResult(BaseModel):
    story_id: str
    test_name: str
    field: str
    text: str
    pattern: str


def detect_vague_formulations(test: ManualTestCase) -> List[VagueTestResult]:
    results = []
    # Champs à auditer
    fields = [
        ("objective", test.objective),
    ]
    for step in test.steps:
        fields.append((f"step_action_{step.index}", step.action))
        fields.append((f"step_expected_{step.index}", step.expected_result))
    for field, text in fields:
        for regex in VAGUE_REGEX:
            if regex.search(text):
                results.append(VagueTestResult(
                    story_id=test.story_id,
                    test_name=test.test_name,
                    field=field,
                    text=text,
                    pattern=regex.pattern
                ))
    return results

# Service principal
class VagueAuditService:
    @staticmethod
    def audit_tests_from_json(json_path: str) -> List[VagueTestResult]:
        data = load_json(json_path)
        results = []
        for story in data.get("results", []):
            for test_block in story.get("tests", {}).get("tests", []):
                test = ManualTestCase(**test_block)
                results.extend(detect_vague_formulations(test))
        return results

# FastAPI route
router = APIRouter(prefix="/audit", tags=["Test_Audit"])

@router.get("/vague_formulations", response_model=List[VagueTestResult])
def get_vague_formulations(input_json: str = Query(..., description="Chemin du JSON à auditer")):
    try:
        results = VagueAuditService.audit_tests_from_json(input_json)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/vague_formulations/by_story/{story_id}", response_model=List[VagueTestResult])
def audit_vague_formulations_by_story(story_id: str):
    """
    Audit des tests générés pour une story donnée (entrée = story_id).
    Utilise l'analyse Agent 1 et les tests Agent 2 stockés en base.
    """
    # 1. Charger l'analyse Agent 1 (optionnel, pour vérification)
    analysis = get_latest_analysis(story_id)
    if not analysis:
        raise HTTPException(status_code=404, detail=f"Aucune analyse trouvée pour {story_id}.")

    # 2. Charger les tests générés Agent 2
    story = get_story_by_id(story_id)
    if not story or not story.get("tests"):
        raise HTTPException(status_code=404, detail=f"Aucun test généré trouvé pour {story_id}.")

    # 3. Parser les tests (format ManualTestCase)
    test_blocks = story["tests"]
    if isinstance(test_blocks, str):
        import json
        test_blocks = json.loads(test_blocks)
    tests = [ManualTestCase(**t) for t in test_blocks]

    # 4. Audit
    results = []
    for test in tests:
        results.extend(detect_vague_formulations(test))
    return results

@router.get("/vague_formulations/by_story_live/{story_id}", response_model=List[VagueTestResult])
def audit_vague_formulations_by_story_live(story_id: str, request: Request):
    """
    Audit en temps réel : génère les tests à la volée (Agent 2) puis applique l'audit (Agent 3), sans dépendre de la base.
    """
    # 1. Générer les tests à la volée (Agent 2)
    result = generate_manual_tests(story_id)
    tests = result.tests if hasattr(result, "tests") else result["tests"]
    tests = [ManualTestCase(**t) for t in tests]
    # 2. Audit
    results = []
    for test in tests:
        results.extend(detect_vague_formulations(test))
    return results
