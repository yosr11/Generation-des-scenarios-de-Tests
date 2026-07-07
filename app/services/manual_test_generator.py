import json
import logging
from typing import Dict, Any, List, Optional
from urllib import response

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
from app.services.manual_test_validator import (
    validate_manual_generation_result,
    collect_golden_rule_warnings,
)
from app.services.token_tracker import record_from_response
from app.utils.json_utils import extract_json_from_llm_response
from app.utils.test_steps_utils import normalize_test_etapes_and_steps, normalize_test_display_name


def _attach_golden_rule_warnings(result: ManualTestGenerationResult) -> ManualTestGenerationResult:
    """Ajoute les avertissements QA sans bloquer la génération."""
    warnings = collect_golden_rule_warnings(result)
    if not warnings:
        return result

    message = (result.message or "").strip()
    if "avertissement" not in message.lower():
        suffix = f"{len(warnings)} avertissement(s) golden rules — complétion QA recommandée."
        message = f"{message} ({suffix})" if message else suffix.capitalize()

    strategy = result.recommended_test_strategy
    if strategy != RecommendedTestStrategy.NEEDS_REFINEMENT:
        strategy = RecommendedTestStrategy.NEEDS_REFINEMENT

    return result.model_copy(update={
        "golden_rule_warnings": warnings,
        "message": message,
        "recommended_test_strategy": strategy,
    })


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

    def _request_content(self, system_prompt: str, user_prompt: str, max_tokens: int = 4096, _retry: bool = False) -> str:
        # Nova models can produce very verbose outputs (tests lists). Allow larger outputs.
        try:
            if "nova" in (self.model_name or "").lower():
                max_tokens = max(max_tokens, 8192)
        except Exception:
            pass

        tpm_limit = self.MODEL_TPM_LIMITS.get(self.model_name)
        if tpm_limit:
            est_input = (len(system_prompt) + len(user_prompt)) // 3
            safe_max = tpm_limit - est_input - 200
            if safe_max < max_tokens:
                max_tokens = max(1024, safe_max)

        try:
            response = self.llm_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0,
                response_format={"type": "json_object"},
                max_tokens=max_tokens,
            )
            # Enregistrer l'usage/tokens
            record_from_response(response, self.model_name)

            # Logs diagnostiques: dump brut + type/valeur du contenu
            try:
                logger.info("=== RAW LLM RESPONSE ===")
                # Certains clients exposent model_dump_json / model_dump
                if hasattr(response, "model_dump_json"):
                    try:
                        logger.info(response.model_dump_json(indent=2))
                    except Exception:
                        logger.info(str(response))
                else:
                    logger.info(str(response))
                logger.info("=========================")
            except Exception:
                logger.exception("Failed to log raw LLM response")

            # Extraire le contenu en étant robuste face a differents wrappers
            content = ""
            try:
                if hasattr(response, "choices"):
                    content = response.choices[0].message.content if response.choices else ""
                elif isinstance(response, dict):
                    # compat dict-style
                    content = response.get("output", {}).get("message", {}).get("content", "")
                    if isinstance(content, list) and len(content) > 0:
                        # Bedrock-like: content is a list of dicts with 'text'
                        first = content[0]
                        content = first.get("text", "") if isinstance(first, dict) else str(first)
                else:
                    # Fallback generic stringification
                    content = getattr(response, "text", None) or getattr(response, "content", None) or ""
            except Exception as e:
                logger.exception("Error while extracting content from LLM response: %s", e)
                content = ""

            return content or ""

        except Exception as e:
            if _retry or "json_validate_failed" not in str(e):
                raise

            # Retry avec plus de tokens (reste en json_object mode)
            retry_max = min(max_tokens * 2, 8192)
            if tpm_limit:
                est_input = (len(system_prompt) + len(user_prompt)) // 3
                retry_max = min(retry_max, tpm_limit - est_input - 200)
                retry_max = max(1024, retry_max)

            if retry_max <= max_tokens:
                raise  # Pas de marge supplémentaire, inutile de réessayer

            logger.warning(
                f"[Agent2] json_validate_failed, retrying with max_tokens={retry_max} (was {max_tokens})"
            )
            return self._request_content(system_prompt, user_prompt, max_tokens=retry_max, _retry=True)

    
    def _create_completion(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        content = self._request_content(system_prompt, user_prompt)
        logger.warning("[Agent2-DEBUG] content brut (500 chars): %r", content[:500] if content else "<VIDE>")

        # Extraction robuste : trouver le premier { et le dernier }
        content_clean = content.strip()
        start = content_clean.find("{")
        end = content_clean.rfind("}")
        if start != -1 and end != -1 and end > start:
            content_clean = content_clean[start:end + 1]

        logger.warning("[Agent2-DEBUG] content après strip: %r", content_clean[:200])

        try:
            return extract_json_from_llm_response(content_clean)
        except ValueError as exc:
            logger.warning("[Agent2-DEBUG] extract_json failed: %s", exc)
            light_system = build_manual_test_repair_system_prompt()
            reformat_prompt = build_manual_test_json_reformat_prompt(content_clean, str(exc))
            repaired_content = self._request_content(light_system, reformat_prompt)
            repaired_clean = repaired_content.strip()
            start2 = repaired_clean.find("{")
            end2 = repaired_clean.rfind("}")
            if start2 != -1 and end2 != -1 and end2 > start2:
                repaired_clean = repaired_clean[start2:end2 + 1]
            return extract_json_from_llm_response(repaired_clean)

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
            raw_name = test.get("test_name") or ""
            if raw_name:
                test["test_name"] = normalize_test_display_name(raw_name) or raw_name

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
                    normalized_steps.append({"action": step, "data": "", "actor": "", "expected_result": "", "index": step_idx, "revision_po": ""})
                elif isinstance(step, dict):
                    normalized_steps.append(step)
            test["steps"] = normalized_steps

            for step_idx, step in enumerate(test.get("steps", []), start=1):
                if not isinstance(step, dict):
                    continue
                if "index" not in step:
                    step["index"] = step_idx
                data_value = step.get("data", "")
                actor_value = step.get("actor", "")
                if not isinstance(data_value, str):
                    data_value = json.dumps(data_value, ensure_ascii=False) if data_value else ""
                if not isinstance(actor_value, str):
                    actor_value = json.dumps(actor_value, ensure_ascii=False) if actor_value else ""
                step["data"] = data_value
                step["actor"] = actor_value
                if not isinstance(step.get("expected_result"), str):
                    step["expected_result"] = json.dumps(step.get("expected_result", ""), ensure_ascii=False) if step.get("expected_result") else ""
                if not isinstance(step.get("action"), str):
                    step["action"] = json.dumps(step.get("action", ""), ensure_ascii=False) if step.get("action") else ""
                if "revision_po" not in step:
                    step["revision_po"] = ""

            normalize_test_etapes_and_steps(test)

        # Normalize notes (outside the test loop)
        # Normalize notes (outside the test loop)
        notes = data.get("notes")
        if isinstance(notes, str):
            data["notes"] = [notes] if notes.strip() else []
        elif notes is None:
            data["notes"] = []
        elif isinstance(notes, list):
            normalized_notes = []
            for note in notes:
                if isinstance(note, str):
                    if note.strip():
                        normalized_notes.append(note)
                elif isinstance(note, dict):
                    # Le LLM a renvoyé un objet au lieu d'une string : sérialiser proprement
                    normalized_notes.append(json.dumps(note, ensure_ascii=False))
                elif note is not None:
                    normalized_notes.append(str(note))
            data["notes"] = normalized_notes
        else:
            # Type inattendu (ex: dict unique) → wrapper en liste de string
            data["notes"] = [json.dumps(notes, ensure_ascii=False)] if notes else []

        data.setdefault("golden_rule_warnings", [])

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
        legacy_examples: Optional[List[Dict[str, Any]]] = None,
    ) -> ManualTestGenerationResult:
        story_id = story.get("id", "")

        story_type = (analysis.get("story_type") or "").strip().lower()
        prompt_builder = self.STORY_TYPE_PROMPTS.get(story_type, build_manual_test_generation_system_prompt)
        system_prompt = prompt_builder()

        user_prompt = build_manual_test_generation_user_prompt(
            story=story, analysis=analysis, rag_context=rag_context,
            legacy_examples=legacy_examples,
        )

        try:
            data = self._normalize_enums(self._ensure_story_ids(self._create_completion(system_prompt, user_prompt), story_id))
        except Exception as e:
            if "413" in str(e) or "too large" in str(e).lower() or "rate_limit" in str(e).lower() or "json_validate_failed" in str(e):
                user_prompt = build_manual_test_generation_user_prompt(
                    story=story, analysis=analysis, rag_context=None,
                    legacy_examples=None,
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
            try:
                repaired_result = ManualTestGenerationResult(**repaired_data)
            except ValidationError:
                repaired_result = result
            else:
                repaired_errors = validate_manual_generation_result(repaired_result)
                if not repaired_errors and repaired_result.tests:
                    result = repaired_result
                elif result.tests:
                    pass
                elif repaired_result.tests:
                    result = repaired_result

        if result.tests and result.generation_status == ManualGenerationStatus.NOT_GENERATED:
            result = result.model_copy(update={
                "generation_status": ManualGenerationStatus.GENERATED,
                "message": result.message or "Tests générés automatiquement",
            })

        if result.tests:
            return _attach_golden_rule_warnings(result)

        structural_errors = validate_manual_generation_result(result)
        return ManualTestGenerationResult(
            story_id=story_id,
            recommended_test_strategy=RecommendedTestStrategy.NEEDS_REFINEMENT,
            generation_status=ManualGenerationStatus.NOT_GENERATED,
            message="Impossible de générer des tests (structure JSON invalide).",
            tests=[],
            notes=structural_errors or validation_errors,
        )

    def generate_gap_coverage_tests(
        self,
        story: Dict[str, Any],
        analysis: Dict[str, Any],
        missing_testable_points: List[str],
        existing_tests: List[Dict[str, Any]],
        rag_context: Optional[List[Dict[str, Any]]] = None,
        duplicate_pairs: Optional[List[Dict[str, Any]]] = None,
        ambiguity_findings: Optional[List[Dict[str, Any]]] = None,
        correction_instructions: Optional[list] = None,
        legacy_examples: Optional[List[Dict[str, Any]]] = None,
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
            duplicate_pairs=duplicate_pairs,
            ambiguity_findings=ambiguity_findings,
            correction_instructions=correction_instructions,
            legacy_examples=legacy_examples,
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
                    legacy_examples=None,
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
            try:
                repaired_result = ManualTestGenerationResult(**repaired_data)
            except ValidationError:
                repaired_result = result
            else:
                repaired_errors = validate_manual_generation_result(repaired_result)
                if not repaired_errors and repaired_result.tests:
                    result = repaired_result
                elif result.tests:
                    pass
                elif repaired_result.tests:
                    result = repaired_result

        if result.tests and result.generation_status == ManualGenerationStatus.NOT_GENERATED:
            result = result.model_copy(update={
                "generation_status": ManualGenerationStatus.GENERATED,
                "message": result.message or "Tests générés automatiquement",
            })

        if result.tests:
            return _attach_golden_rule_warnings(result)

        structural_errors = validate_manual_generation_result(result)
        return ManualTestGenerationResult(
            story_id=story_id,
            recommended_test_strategy=RecommendedTestStrategy.NEEDS_REFINEMENT,
            generation_status=ManualGenerationStatus.NOT_GENERATED,
            message="Génération complémentaire : JSON invalide après réparation.",
            tests=[],
            notes=structural_errors or validation_errors,
        )
