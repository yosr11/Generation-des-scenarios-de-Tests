import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

from app.prompts.scenario_generation_prompt import (
    build_manual_test_generation_system_prompt,
    build_manual_test_generation_user_prompt,
    build_manual_test_gap_coverage_user_prompt,
    build_manual_test_json_reformat_prompt,
    build_manual_test_repair_system_prompt,
    build_manual_test_repair_user_prompt,
    build_poc_study_system_prompt,
    build_documentation_system_prompt,
    build_technical_system_prompt,
)
from pydantic import ValidationError

from app.models.test_manual import (
    ManualTestGenerationResult,
    ManualGenerationStatus,
    RecommendedTestStrategy,
)
from app.services.manual_test_validator import validate_manual_generation_result
from app.utils.json_utils import extract_json_from_llm_response


def _fix_golden_rule_violations(data: Dict[str, Any]) -> None:
    """Corrige automatiquement les violations des golden rules QA."""
    FORBIDDEN_ACTION_VERBS = {
        "Vérifier": "Valider",
        "vérifier": "valider",
    }
    VAGUE_WORDS = ["correctement", "normalement", "avec succès", "comme prévu", "de manière attendue",
                    "est correcte", "est correct", "sont correctes", "sont corrects"]

    for test in data.get("tests", []):
        test_name = test.get("test_name", "")
        for old_word, new_word in [("Vérifier ", ""), ("Vérification ", ""), ("vérifier ", ""), ("vérification ", "")]:
            test_name = test_name.replace(old_word, new_word)
        test["test_name"] = test_name

        objective = test.get("objective", "")
        if objective.startswith("Vérifier"):
            objective = "Valider" + objective[8:]
        test["objective"] = objective

        for step in test.get("steps", []):
            if not isinstance(step, dict):
                continue
            action = step.get("action", "")
            for forbidden, replacement in FORBIDDEN_ACTION_VERBS.items():
                if action.startswith(forbidden):
                    action = replacement + action[len(forbidden):]
                    break
            # Fix "Consulter que" → extract the real subject
            if action.startswith("Consulter que "):
                action = "Consulter " + action[14:]
            if action.startswith("Consulter qu'"):
                action = "Consulter " + action[13:]
            step["action"] = action

            er = step.get("expected_result", "")
            for vague in VAGUE_WORDS:
                er = er.replace(f" {vague}", "")
            er = er.replace(" n'est pas ", " est ").replace(" ne sont pas ", " sont ").replace(" n'affiche pas ", " masque ")
            step["expected_result"] = er


class ManualTestGeneratorService:
    """
    Compatible avec un client type OpenAI / Groq :
    client.chat.completions.create(...)
    """

    def __init__(self, llm_client, model_name: str):
        self.llm_client = llm_client
        self.model_name = model_name

    # Groq free tier TPM limits per model (input + max_tokens must fit)
    MODEL_TPM_LIMITS = {
        "qwen/qwen3-32b": 6000,
    }

    def _request_content(self, system_prompt: str, user_prompt: str, max_tokens: int = 4096) -> str:
        tpm_limit = self.MODEL_TPM_LIMITS.get(self.model_name)
        if tpm_limit:
            est_input = (len(system_prompt) + len(user_prompt)) // 3
            safe_max = tpm_limit - est_input - 200
            if safe_max < max_tokens:
                max_tokens = max(1024, safe_max)

        response = self.llm_client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

    def _create_completion(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        content = self._request_content(system_prompt, user_prompt)
        try:
            return extract_json_from_llm_response(content)
        except ValueError as exc:
            light_system = build_manual_test_repair_system_prompt()
            reformat_prompt = build_manual_test_json_reformat_prompt(content, str(exc))
            repaired_content = self._request_content(light_system, reformat_prompt)
            return extract_json_from_llm_response(repaired_content)

    @staticmethod
    def _ensure_story_ids(data, story_id: str) -> Dict[str, Any]:
        if isinstance(data, list):
            data = {"story_id": story_id, "tests": data, "message": "Tests générés automatiquement"}
        if not data.get("story_id"):
            data["story_id"] = story_id
        for test in data.get("tests", []):
            if not test.get("story_id"):
                test["story_id"] = story_id
        return data

    @staticmethod
    def _normalize_enums(data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalise les valeurs d'enum que le LLM peut renvoyer en français."""
        strategy_map = {
            "manuel": "manual", "manuelle": "manual",
            "automatisé": "automated", "automatisée": "automated", "automatise": "automated",
            "à affiner": "needs_refinement", "a affiner": "needs_refinement",
            "functional testing": "manual", "functional": "manual", "test manuel": "manual",
        }
        status_map = {
            "généré": "generated", "genere": "generated", "complété": "generated", "complete": "generated",
            "completed": "generated", "done": "generated", "success": "generated",
            "non généré": "not_generated", "non genere": "not_generated", "non_genere": "not_generated",
            "failed": "not_generated", "error": "not_generated",
        }

        if "message" not in data or not data["message"]:
            data["message"] = "Tests générés automatiquement"

        raw_strategy = (data.get("recommended_test_strategy") or "").strip().lower()
        if raw_strategy in strategy_map:
            data["recommended_test_strategy"] = strategy_map[raw_strategy]
        elif raw_strategy not in ("manual", "automated", "needs_refinement"):
            data["recommended_test_strategy"] = "manual"

        raw_status = (data.get("generation_status") or "").strip().lower()
        if raw_status in status_map:
            data["generation_status"] = status_map[raw_status]
        elif raw_status not in ("generated", "not_generated"):
            data["generation_status"] = "generated" if data.get("tests") else "not_generated"

        scenario_type_map = {
            "validation": "NOM", "nominal": "NOM", "nom": "NOM",
            "technique": "NOM", "technical": "NOM",
            "alternatif": "ALT", "alternative": "ALT", "alt": "ALT",
            "exception": "EXC", "erreur": "EXC", "exc": "EXC",
        }
        for test in data.get("tests", []):
            # Normalize execution_context: dict → string
            ec = test.get("execution_context", "")
            if isinstance(ec, dict):
                test["execution_context"] = ", ".join(f"{k}: {v}" for k, v in ec.items() if v)
            elif not isinstance(ec, str):
                test["execution_context"] = str(ec) if ec else ""

            raw_st = (test.get("scenario_type") or "").strip().lower()
            if raw_st in scenario_type_map:
                test["scenario_type"] = scenario_type_map[raw_st]
            elif raw_st not in ("nom", "alt", "exc"):
                test["scenario_type"] = "NOM"

            normalized_steps = []
            for step_idx, step in enumerate(test.get("steps", []), start=1):
                if isinstance(step, str):
                    normalized_steps.append({"action": step, "data": "", "expected_result": "", "index": step_idx, "revision_po": ""})
                elif isinstance(step, dict):
                    normalized_steps.append(step)
            test["steps"] = normalized_steps

            for step_idx, step in enumerate(test.get("steps", []), start=1):
                if not isinstance(step, dict):
                    continue
                if "index" not in step:
                    step["index"] = step_idx
                if not isinstance(step.get("data"), str):
                    step["data"] = json.dumps(step.get("data", ""), ensure_ascii=False) if step.get("data") else ""
                if not isinstance(step.get("expected_result"), str):
                    step["expected_result"] = json.dumps(step.get("expected_result", ""), ensure_ascii=False) if step.get("expected_result") else ""
                if not isinstance(step.get("action"), str):
                    step["action"] = json.dumps(step.get("action", ""), ensure_ascii=False) if step.get("action") else ""
                if "revision_po" not in step:
                    step["revision_po"] = ""

        _fix_golden_rule_violations(data)

        return data

    # Map story_type to the appropriate system prompt builder
    STORY_TYPE_PROMPTS = {
        "poc_or_study": build_poc_study_system_prompt,
        "documentation": build_documentation_system_prompt,
        "technical": build_technical_system_prompt,
    }

    def generate(
        self,
        story: Dict[str, Any],
        analysis: Dict[str, Any],
        rag_context: Optional[List[Dict[str, Any]]] = None,
    ) -> ManualTestGenerationResult:
        story_id = story.get("id", "")

        story_type = (analysis.get("story_type") or "").strip().lower()
        prompt_builder = self.STORY_TYPE_PROMPTS.get(story_type, build_manual_test_generation_system_prompt)
        system_prompt = prompt_builder()

        user_prompt = build_manual_test_generation_user_prompt(
            story=story, analysis=analysis, rag_context=rag_context,
        )

        try:
            data = self._normalize_enums(self._ensure_story_ids(self._create_completion(system_prompt, user_prompt), story_id))
        except Exception as e:
            if "413" in str(e) or "too large" in str(e).lower() or "rate_limit" in str(e).lower():
                user_prompt = build_manual_test_generation_user_prompt(
                    story=story, analysis=analysis, rag_context=None,
                )
                data = self._normalize_enums(self._ensure_story_ids(self._create_completion(system_prompt, user_prompt), story_id))
            else:
                raise

        try:
            result = ManualTestGenerationResult(**data)
        except ValidationError as exc:
            repair_system = build_manual_test_repair_system_prompt()
            reformat_prompt = build_manual_test_json_reformat_prompt(
                json.dumps(data, ensure_ascii=False), str(exc)
            )
            repaired_data = self._normalize_enums(self._ensure_story_ids(
                self._create_completion(repair_system, reformat_prompt), story_id
            ))
            result = ManualTestGenerationResult(**repaired_data)

        validation_errors = validate_manual_generation_result(result)
        if validation_errors:
            repair_system = build_manual_test_repair_system_prompt()
            repair_prompt = build_manual_test_repair_user_prompt(data, validation_errors)
            repaired_data = self._normalize_enums(self._ensure_story_ids(
                self._create_completion(repair_system, repair_prompt),
                story_id,
            ))
            repaired_result = ManualTestGenerationResult(**repaired_data)
            repaired_errors = validate_manual_generation_result(repaired_result)

            if not repaired_errors:
                return repaired_result

            return ManualTestGenerationResult(
                story_id=story_id,
                recommended_test_strategy=RecommendedTestStrategy.NEEDS_REFINEMENT,
                generation_status=ManualGenerationStatus.NOT_GENERATED,
                message="Les tests générés ne respectent pas complètement les golden rules.",
                tests=[],
                notes=repaired_errors,
            )

        return result

    def generate_gap_coverage_tests(
        self,
        story: Dict[str, Any],
        analysis: Dict[str, Any],
        missing_testable_points: List[str],
        existing_tests: List[Dict[str, Any]],
        rag_context: Optional[List[Dict[str, Any]]] = None,
    ) -> ManualTestGenerationResult:
        """
        Agent 2 — génération ciblée pour des testable_points non couverts (typiquement invoquée par l'orchestrateur).
        """
        story_id = story.get("id", "")
        story_type = (analysis.get("story_type") or "").strip().lower()
        prompt_builder = self.STORY_TYPE_PROMPTS.get(story_type, build_manual_test_generation_system_prompt)
        system_prompt = prompt_builder()

        user_prompt = build_manual_test_gap_coverage_user_prompt(
            story=story,
            analysis=analysis,
            missing_testable_points=missing_testable_points,
            existing_tests=existing_tests,
            rag_context=rag_context,
        )

        try:
            data = self._normalize_enums(
                self._ensure_story_ids(self._create_completion(system_prompt, user_prompt), story_id)
            )
        except Exception as e:
            if "413" in str(e) or "too large" in str(e).lower() or "rate_limit" in str(e).lower():
                user_prompt = build_manual_test_gap_coverage_user_prompt(
                    story=story,
                    analysis=analysis,
                    missing_testable_points=missing_testable_points,
                    existing_tests=existing_tests,
                    rag_context=None,
                )
                data = self._normalize_enums(
                    self._ensure_story_ids(self._create_completion(system_prompt, user_prompt), story_id)
                )
            else:
                raise

        try:
            result = ManualTestGenerationResult(**data)
        except ValidationError as exc:
            repair_system = build_manual_test_repair_system_prompt()
            reformat_prompt = build_manual_test_json_reformat_prompt(
                json.dumps(data, ensure_ascii=False), str(exc)
            )
            repaired_data = self._normalize_enums(
                self._ensure_story_ids(self._create_completion(repair_system, reformat_prompt), story_id)
            )
            result = ManualTestGenerationResult(**repaired_data)

        validation_errors = validate_manual_generation_result(result)
        if validation_errors:
            repair_system = build_manual_test_repair_system_prompt()
            repair_prompt = build_manual_test_repair_user_prompt(data, validation_errors)
            repaired_data = self._normalize_enums(
                self._ensure_story_ids(self._create_completion(repair_system, repair_prompt), story_id)
            )
            repaired_result = ManualTestGenerationResult(**repaired_data)
            repaired_errors = validate_manual_generation_result(repaired_result)
            if not repaired_errors:
                return repaired_result
            return ManualTestGenerationResult(
                story_id=story_id,
                recommended_test_strategy=RecommendedTestStrategy.NEEDS_REFINEMENT,
                generation_status=ManualGenerationStatus.NOT_GENERATED,
                message="Génération complémentaire : JSON invalide après réparation.",
                tests=[],
                notes=repaired_errors,
            )

        return result
