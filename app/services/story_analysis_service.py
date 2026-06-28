# app/services/story_analysis_service.py
import json
import re
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

from pydantic import ValidationError

from app.models.analysis import StoryAnalysisResult, StoryClassificationResult
from app.prompts.story_analysis_prompt import (
    build_story_analysis_system_prompt,
    build_story_analysis_user_prompt,
)
from app.services.llm_client import call_groq, call_bedrock, GROQ_MODELS, BEDROCK_MODELS

logger = logging.getLogger(__name__)


class StoryAnalysisError(Exception):
    pass


# ---------------------------------------------------------------------------
# Extraction fallback des acteurs depuis la description
# ---------------------------------------------------------------------------

_ACTOR_PATTERNS = [
    # "[En tant que] qu'utilisateur RH..." or "[En tant que] utilisateur RH..."
    re.compile(r"\[en\s+tant\s+que\]\s*(?:qu['\u2019])?\s*(.+?)(?:\n|\[|,\s*\[)", re.IGNORECASE),
    # "En tant que collaborateur..."
    re.compile(r"en\s+tant\s+que\s+(.+?)(?:\n|\[|,\s*\[|,?\s*je\s+)", re.IGNORECASE),
]


def _extract_actors_from_description(story: Dict[str, Any]) -> List[str]:
    """
    Fallback: extracts actors from description when the LLM fails to do so.
    Looks for 'En tant que ...' or '[En tant que] ...' patterns.
    """
    description = story.get("description_clean", "") or story.get("description", "") or ""
    if not description:
        return []

    for pattern in _ACTOR_PATTERNS:
        match = pattern.search(description)
        if match:
            raw = match.group(1).strip().rstrip(",.")
            # Split on " et " to handle multiple actors
            actors = [a.strip() for a in re.split(r"\s+et\s+", raw) if a.strip()]
            # Capitalize first letter
            actors = [a[0].upper() + a[1:] if a else a for a in actors]
            return actors

    return []


# ---------------------------------------------------------------------------
# Détection et résolution des descriptions "référence seule"
# ---------------------------------------------------------------------------

# Regex pour extraire des clés de ticket Jira (ex: YOU-13730, NUXEPM-2289)
_TICKET_KEY_RE = re.compile(r"\b([A-Z][A-Z0-9_]+-\d+)\b")

# Patterns qui indiquent une description "référence seule" (pas de contenu fonctionnel)
_REFERENCE_ONLY_PATTERNS = [
    # "Continuer YOU-13730", "Terminer YOU-13438", "Suite de YOU-XXXX"
    re.compile(
        r"^\s*(continuer|terminer|suite\s+de|finir|completer|compléter|voir|cf\.?|ref\.?|see)\s+",
        re.IGNORECASE,
    ),
    # "emphasized textTerminer YOU-XXXX" (artefact Jira)
    re.compile(r"^\s*emphasized\s*text", re.IGNORECASE),
]


def _is_reference_only_description(description: str) -> bool:
    """
    Returns True if the description contains only ticket references
    and no real functional content.
    """
    if not description or not description.strip():
        return True

    text = description.strip()

    # Remove URLs (Jira links)
    text_no_urls = re.sub(r"https?://\S+", "", text).strip()

    # Remove ticket keys
    text_no_keys = _TICKET_KEY_RE.sub("", text_no_urls).strip()

    # Remove reference verbs and connectors
    text_clean = re.sub(
        r"\b(continuer|terminer|suite\s+de|finir|completer|compléter|voir|cf\.?|ref\.?|see|et|emphasized\s*text)\b",
        "",
        text_no_keys,
        flags=re.IGNORECASE,
    ).strip()

    # Remove residual punctuation and whitespace
    text_clean = re.sub(r"[^\w]", "", text_clean).strip()

    # If nothing meaningful remains after stripping references, it's reference-only
    return len(text_clean) < 10


def _extract_ticket_keys(description: str) -> List[str]:
    """Extract all Jira ticket keys from a description string."""
    # From text
    keys = set(_TICKET_KEY_RE.findall(description))

    # From URLs (e.g. https://jira.example.com/browse/YOU-13724)
    url_keys = re.findall(r"/browse/([A-Z][A-Z0-9_]+-\d+)", description)
    keys.update(url_keys)

    return list(keys)


def _fetch_referenced_stories(ticket_keys: List[str]) -> List[Dict[str, Any]]:
    """
    Fetch referenced tickets from Jira.
    Returns list of {key, summary, description} dicts for successfully fetched tickets.
    """
    from app.services.jira_service import get_story_byID
    from app.utils.cleaning import clean_text

    results = []
    for key in ticket_keys:
        try:
            resp = get_story_byID(key)
            if resp.get("status") == 200 and resp.get("data"):
                fields = resp["data"].get("fields", {})
                raw_desc = fields.get("description") or ""
                results.append({
                    "key": key,
                    "summary": fields.get("summary", ""),
                    "description": clean_text(raw_desc) if raw_desc else "",
                })
                logger.info(f"Résolution automatique : ticket {key} récupéré depuis Jira")
            else:
                logger.warning(f"Ticket {key} non trouvé dans Jira (status={resp.get('status')})")
        except Exception as e:
            logger.warning(f"Impossible de récupérer le ticket {key} depuis Jira : {e}")

    return results


def _enrich_story_with_references(
    story: Dict[str, Any], referenced_stories: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Create an enriched copy of the story with the referenced tickets' content
    injected into the context.
    """
    enriched = dict(story)  # shallow copy

    ref_sections = []
    for ref in referenced_stories:
        section = f"--- Contenu du ticket référencé {ref['key']} ---\n"
        section += f"Summary : {ref['summary']}\n"
        if ref["description"]:
            section += f"Description :\n{ref['description']}\n"
        else:
            section += "Description : (vide)\n"
        ref_sections.append(section)

    if ref_sections:
        original_context = enriched.get("story_context_llm") or ""
        ref_block = (
            "\n\n=== CONTENU DES TICKETS RÉFÉRENCÉS (résolution automatique) ===\n"
            "La description originale de cette story ne contient qu'une référence à d'autres tickets.\n"
            "Le contenu ci-dessous a été récupéré automatiquement depuis Jira pour permettre l'analyse.\n"
            "Analyse ce contenu comme s'il faisait partie de la description de la story.\n\n"
            + "\n".join(ref_sections)
        )
        enriched["story_context_llm"] = original_context + ref_block

    return enriched


def extract_json_object(text: str) -> Dict[str, Any]:
    """
    Extract the first JSON object from a raw LLM response.
    Handles extra text, markdown fences, and DeepSeek <think> blocks.
    """
    text = text.strip()

    # Remove DeepSeek-R1 <think>...</think> blocks
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    # Remove markdown code fences
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    text = text.strip()

    # first try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # fallback: extract first {...}
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise StoryAnalysisError(f"No JSON object found in LLM response. Raw: {text[:500]}")

    json_candidate = match.group(0)

    try:
        return json.loads(json_candidate)
    except json.JSONDecodeError as e:
        raise StoryAnalysisError(f"Invalid JSON returned by LLM: {e}")


def merge_story_analysis(
    classification: StoryClassificationResult,
    analysis: Optional[StoryAnalysisResult],
    story: Optional[Dict[str, Any]] = None,
) -> StoryAnalysisResult:
    """Merge classification output and extraction output while preserving the public JSON contract."""
    story = story or {}
    story_id = getattr(classification, "story_id", None) or story.get("id", "") or ""
    story_title = (
        getattr(classification, "story_title", None)
        or story.get("summary")
        or story.get("title")
        or ""
    )

    classification_reasons = [
        str(item).strip()
        for item in (getattr(classification, "analysis_reason", None) or [])
        if str(item).strip()
    ]

    if classification.story_type != "functional":
        return StoryAnalysisResult(
            story_id=story_id,
            story_title=story_title,
            story_type=classification.story_type,
            actors=[],
            actions=[],
            business_rules=[],
            technical_scope=[],
            testable_points=[],
            user_flows=[],
            acceptance_criteria_explicit=[],
            acceptance_criteria_inferred=[],
            clarification_questions=[],
            analysis_reason=classification_reasons,
            resolved_from_references=[],
        )

    if analysis is None:
        return StoryAnalysisResult(
            story_id=story_id,
            story_title=story_title,
            story_type="functional",
            actors=[],
            actions=[],
            business_rules=[],
            technical_scope=[],
            testable_points=[],
            user_flows=[],
            acceptance_criteria_explicit=[],
            acceptance_criteria_inferred=[],
            clarification_questions=[],
            analysis_reason=classification_reasons,
            resolved_from_references=[],
        )

    return StoryAnalysisResult(
        story_id=story_id,
        story_title=story_title,
        story_type=classification.story_type,
        actors=list(getattr(analysis, "actors", []) or []),
        actions=list(getattr(analysis, "actions", []) or []),
        business_rules=list(getattr(analysis, "business_rules", []) or []),
        technical_scope=list(getattr(analysis, "technical_scope", []) or []),
        testable_points=list(getattr(analysis, "testable_points", []) or []),
        user_flows=list(getattr(analysis, "user_flows", []) or []),
        acceptance_criteria_explicit=list(getattr(analysis, "acceptance_criteria_explicit", []) or []),
        acceptance_criteria_inferred=list(getattr(analysis, "acceptance_criteria_inferred", []) or []),
        clarification_questions=list(getattr(analysis, "clarification_questions", []) or []),
        analysis_reason=classification_reasons or [
            str(item).strip()
            for item in (getattr(analysis, "analysis_reason", None) or [])
            if str(item).strip()
        ],
        resolved_from_references=list(getattr(analysis, "resolved_from_references", []) or []),
    )


def classify_story_with_llm(
    story: Dict[str, Any],
    llm_callable: Callable[[str, str], str],
    rag_context: list = None,
    story_attachments: list = None,
) -> StoryClassificationResult:
    """Classify a story into functional/technical/invalid_or_too_weak."""
    description = (
        story.get("description_clean")
        or story.get("description")
        or ""
    ).strip()

    if not description:
        return StoryClassificationResult(
            story_id=story.get("id", ""),
            story_title=story.get("summary") or story.get("title") or "",
            story_type="invalid_or_too_weak",
            analysis_reason=[
                "La story ne contient pas de description exploitable.",
                "Aucun comportement testable ne peut être identifié.",
            ],
        )

    enriched_story = story
    if _is_reference_only_description(description):
        ticket_keys = _extract_ticket_keys(description)
        if ticket_keys:
            logger.info(
                f"Story {story.get('id', '?')} : description = référence seule. "
                f"Résolution automatique des tickets : {ticket_keys}"
            )
            referenced = _fetch_referenced_stories(ticket_keys)
            if referenced and any(r["description"] for r in referenced):
                enriched_story = _enrich_story_with_references(story, referenced)
            else:
                logger.warning(
                    f"Story {story.get('id', '?')} : impossible de résoudre les tickets "
                    f"référencés {ticket_keys}. Classification invalid_or_too_weak."
                )
                return StoryClassificationResult(
                    story_id=story.get("id", ""),
                    story_title=story.get("summary") or story.get("title") or "",
                    story_type="invalid_or_too_weak",
                    analysis_reason=[
                        f"La description ne contient qu'une référence aux tickets {ticket_keys}.",
                        "Le contenu de ces tickets n'a pas pu être récupéré depuis Jira.",
                    ],
                )
        else:
            return StoryClassificationResult(
                story_id=story.get("id", ""),
                story_title=story.get("summary") or story.get("title") or "",
                story_type="invalid_or_too_weak",
                analysis_reason=[
                    "La description est trop vague pour identifier un comportement utilisateur.",
                    f"Description reçue : \"{description[:100]}\"",
                ],
            )


    # Use the analysis prompt as the single canonical prompt for story understanding.
    # The analysis prompt contains story_type and analysis_reason fields which we use
    # to derive the classification result.
    system_prompt = build_story_analysis_system_prompt()
    user_prompt = build_story_analysis_user_prompt(
        enriched_story,
        rag_context=rag_context,
        story_attachments=story_attachments,
    )

    raw_response = llm_callable(system_prompt, user_prompt)
    data = extract_json_object(raw_response)

    if not data.get("story_id"):
        data["story_id"] = story.get("id", "")
    if not data.get("story_title"):
        data["story_title"] = story.get("summary") or story.get("title") or ""
    # If the analysis prompt did not provide a story_type, conservatively mark as invalid/too weak
    if not data.get("story_type"):
        data["story_type"] = "invalid_or_too_weak"
    if not data.get("analysis_reason"):
        data["analysis_reason"] = [
            f"Story classée '{data.get('story_type')}' sans justification détaillée."
        ]

    # The analysis prompt may return many keys; only keep the ones
    # required by StoryClassificationResult to avoid pydantic extra-field errors.
    classification_data = {
        "story_id": data.get("story_id", story.get("id", "")),
        "story_title": data.get("story_title", story.get("summary") or story.get("title") or ""),
        "story_type": data.get("story_type", "invalid_or_too_weak"),
        "analysis_reason": data.get("analysis_reason") or [
            f"Story classée '{data.get('story_type','invalid_or_too_weak')}' sans justification détaillée."
        ],
    }

    try:
        return StoryClassificationResult(**classification_data)
    except ValidationError as e:
        raise StoryAnalysisError(f"Classification LLM output does not match expected schema: {e}")


def extract_story_analysis_with_llm(
    story: Dict[str, Any],
    llm_callable: Callable[[str, str], str],
    rag_context: list = None,
    story_attachments: list = None,
) -> StoryAnalysisResult:
    """Extract analysis fields for a functional story without re-running classification."""
    description = (
        story.get("description_clean")
        or story.get("description")
        or ""
    ).strip()

    enriched_story = story
    resolved_refs: list[str] = []
    if _is_reference_only_description(description):
        ticket_keys = _extract_ticket_keys(description)
        if ticket_keys:
            logger.info(
                f"Story {story.get('id', '?')} : description = référence seule. "
                f"Résolution automatique des tickets : {ticket_keys}"
            )
            referenced = _fetch_referenced_stories(ticket_keys)
            if referenced and any(r["description"] for r in referenced):
                enriched_story = _enrich_story_with_references(story, referenced)
                resolved_refs = [r["key"] for r in referenced]

    system_prompt = build_story_analysis_system_prompt()
    user_prompt = build_story_analysis_user_prompt(
        enriched_story,
        rag_context=rag_context,
        story_attachments=story_attachments,
    )

    raw_response = llm_callable(system_prompt, user_prompt)
    data = extract_json_object(raw_response)

    if not data.get("actors"):
        data["actors"] = _extract_actors_from_description(story)

    if not data.get("story_id"):
        data["story_id"] = story.get("id", "")
    if not data.get("story_title"):
        data["story_title"] = story.get("summary") or story.get("title") or ""

    if not data.get("story_type"):
        data["story_type"] = "functional"

    raw_flows = data.get("user_flows", [])
    if raw_flows and isinstance(raw_flows, list):
        flat = []
        for item in raw_flows:
            if isinstance(item, list):
                flat.extend(str(s) for s in item)
            else:
                flat.append(str(item))
        data["user_flows"] = flat

    try:
        validated = StoryAnalysisResult(**data)
    except ValidationError as e:
        raise StoryAnalysisError(f"LLM output does not match expected schema: {e}")

    if resolved_refs:
        validated.resolved_from_references = resolved_refs

    return validated


def analyze_story_with_llm(
    story: Dict[str, Any],
    llm_callable: Callable[[str, str], str],
    rag_context: list = None,
    story_attachments: list = None,
) -> StoryAnalysisResult:
    """
    Generic analyzer that first classifies the story, then only extracts for functional stories.
    """
    classification = classify_story_with_llm(
        story=story,
        llm_callable=llm_callable,
        rag_context=rag_context,
        story_attachments=story_attachments,
    )

    if classification.story_type != "functional":
        return merge_story_analysis(classification=classification, analysis=None, story=story)

    analysis = extract_story_analysis_with_llm(
        story=story,
        llm_callable=llm_callable,
        rag_context=rag_context,
        story_attachments=story_attachments,
    )

    return merge_story_analysis(
        classification=classification,
        analysis=analysis,
        story=story,
    )


def analyze_story_with_groq(
    story: Dict[str, Any],
    model_alias: str = "llama33",
    rag_context: list = None,
    story_attachments: list = None,
) -> StoryAnalysisResult:
    """
    Legacy helper (now redirects to adaptive LLM selection).
    
    This function now supports both Groq and Bedrock models:
    - Groq models: qwen3, llama4, gptoss, gptoss120b, qwen3.6
    - Bedrock models: nova-lite-2 (Amazon Nova)
    
    Example with Nova-2-lite:
        analysis = analyze_story_with_groq(story, model_alias="nova-lite-2")
    """
    return analyze_story_with_adaptive_llm(
        story=story,
        model_alias=model_alias,
        rag_context=rag_context,
        story_attachments=story_attachments,
    )


def classify_story_with_adaptive_llm(
    story: Dict[str, Any],
    model_alias: str = "llama4",
    rag_context: list = None,
    story_attachments: list = None,
) -> StoryClassificationResult:
    """Classification-only helper using the same provider selection as the analysis service."""
    if model_alias in BEDROCK_MODELS:
        def _bedrock_callable(system_prompt: str, user_prompt: str) -> str:
            return call_bedrock(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model_alias=model_alias,
                temperature=0.0,
                max_tokens=2000,
            )

        return classify_story_with_llm(
            story=story,
            llm_callable=_bedrock_callable,
            rag_context=rag_context,
            story_attachments=story_attachments,
        )

    def _groq_callable(system_prompt: str, user_prompt: str) -> str:
        return call_groq(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model_alias=model_alias,
            temperature=0.0,
            max_tokens=2000,
        )

    return classify_story_with_llm(
        story=story,
        llm_callable=_groq_callable,
        rag_context=rag_context,
        story_attachments=story_attachments,
    )


def extract_story_analysis_with_adaptive_llm(
    story: Dict[str, Any],
    model_alias: str = "llama4",
    rag_context: list = None,
    story_attachments: list = None,
) -> StoryAnalysisResult:
    """Extraction-only helper using the same provider selection as the analysis service."""
    if model_alias in BEDROCK_MODELS:
        def _bedrock_callable(system_prompt: str, user_prompt: str) -> str:
            return call_bedrock(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model_alias=model_alias,
                temperature=0.0,
                max_tokens=2000,
            )

        return extract_story_analysis_with_llm(
            story=story,
            llm_callable=_bedrock_callable,
            rag_context=rag_context,
            story_attachments=story_attachments,
        )

    def _groq_callable(system_prompt: str, user_prompt: str) -> str:
        return call_groq(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model_alias=model_alias,
            temperature=0.0,
            max_tokens=2000,
        )

    return extract_story_analysis_with_llm(
        story=story,
        llm_callable=_groq_callable,
        rag_context=rag_context,
        story_attachments=story_attachments,
    )


def analyze_story_with_adaptive_llm(
    story: Dict[str, Any],
    model_alias: str = "llama4",
    rag_context: list = None,
    story_attachments: list = None,
) -> StoryAnalysisResult:
    """
    Smart helper that auto-detects whether to use Groq or Bedrock based on model_alias.
    
    Supports:
    - Groq models: qwen3, llama4, gptoss, gptoss120b, qwen3.6
    - Bedrock models: nova-lite-2 (Amazon Nova)
    
    Example:
        analysis = analyze_story_with_adaptive_llm(story, model_alias="nova-lite-2")
    """
    
    # Detect provider based on model_alias
    if model_alias in BEDROCK_MODELS:
        # Use Bedrock (Nova)
        def _bedrock_callable(system_prompt: str, user_prompt: str) -> str:
            return call_bedrock(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model_alias=model_alias,
                temperature=0.0,
                max_tokens=2000,
            )
        
        return analyze_story_with_llm(
            story=story,
            llm_callable=_bedrock_callable,
            rag_context=rag_context,
            story_attachments=story_attachments,
        )
    
    elif model_alias in GROQ_MODELS or model_alias not in BEDROCK_MODELS:
        # Use Groq (default fallback)
        def _groq_callable(system_prompt: str, user_prompt: str) -> str:
            return call_groq(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model_alias=model_alias,
                temperature=0.0,
                max_tokens=2000,
            )
        
        return analyze_story_with_llm(
            story=story,
            llm_callable=_groq_callable,
            rag_context=rag_context,
            story_attachments=story_attachments,
        )