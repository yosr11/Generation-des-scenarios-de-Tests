"""

from pydantic import BaseModel
from typing import List
from .execution import ExecutionResult
from .test_case import TestCase

class Report(BaseModel):
    story_id: str
    generated_tests: List[TestCase] = []
    executed: List[ExecutionResult] = []
    summary: str = ""
"""
