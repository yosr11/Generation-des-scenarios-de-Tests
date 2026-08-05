"""
from pydantic import BaseModel
from typing import Dict, Optional, List

class ExecutionResult(BaseModel):
    test_id: str
    verdict: str            # "PASS" | "FAIL" | "SKIP"
    reason: Optional[str] = None
    evidence: List[str] = []

    #Valeurs possibles :"PASS" → le test a réussi,"FAIL" → le test a échoué,"SKIP" → le test a été sauté / non exécuté
"""
