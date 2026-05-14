# app/services/story_analysis_service.py
import json
import re
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

from pydantic import ValidationError

from app.models.analysis import StoryAnalysisResult
from app.prompts.story_analysis_prompt import (
    build_story_analysis_system_prompt,
    build_story_analysis_user_prompt,
)
from app.services.llm_client import call_groq

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


def analyze_story_with_llm(
    story: Dict[str, Any],
    llm_callable: Callable[[str, str], str],
    rag_context: list = None,
) -> StoryAnalysisResult:
    """
    Generic analyzer using any llm_callable(system_prompt, user_prompt) -> str
    """
    # Court-circuit : description vide → pas d'appel LLM
    description = (
        story.get("description_clean")
        or story.get("description")
        or ""
    ).strip()

    if not description:
        return StoryAnalysisResult(
        story_id=story.get("id", ""),
        story_title=story.get("summary") or story.get("title") or "",

        story_type="invalid_or_too_weak",
        recommended_test_type="manual",

        actors=[],
        actions=[],
        business_rules=[],
        technical_scope=[],
        testable_points=[],
        user_flows=[],
        acceptance_criteria_explicit=[],
        acceptance_criteria_inferred=[],

        analysis_reason=[
            "La story ne contient pas de description exploitable.",
            "Aucun comportement testable ne peut être identifié.",
            "Action requise : contacter le Product Owner pour enrichir la story."
        ],
        clarification_questions=[
            "Pouvez-vous compléter la description de la story ?",
            "Pouvez-vous ajouter des critères d’acceptation clairs ?"
        ]
    )

    # ── Résolution automatique des descriptions "référence seule" ──
    # Si la description ne contient que des références à d'autres tickets
    # (ex: "Continuer YOU-13730"), on tente de récupérer le contenu depuis Jira.
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
                # On a récupéré du contenu exploitable → enrichir la story
                enriched_story = _enrich_story_with_references(story, referenced)
                logger.info(
                    f"Story {story.get('id', '?')} : enrichie avec le contenu de "
                    f"{[r['key'] for r in referenced]}"
                )
            else:
                # Jira inaccessible ou tickets sans description → invalid_or_too_weak
                logger.warning(
                    f"Story {story.get('id', '?')} : impossible de résoudre les tickets "
                    f"référencés {ticket_keys}. Classification invalid_or_too_weak."
                )
                return StoryAnalysisResult(
                    story_id=story.get("id", ""),
                    story_title=story.get("summary") or story.get("title") or "",
                    story_type="invalid_or_too_weak",
                    recommended_test_type="manual",
                    actors=[],
                    actions=[],
                    business_rules=[],
                    technical_scope=[],
                    testable_points=[],
                    user_flows=[],
                    acceptance_criteria_explicit=[],
                    acceptance_criteria_inferred=[],
                    analysis_reason=[
                        f"La description ne contient qu'une référence aux tickets {ticket_keys}.",
                        "Le contenu de ces tickets n'a pas pu être récupéré depuis Jira.",
                        "Aucun comportement testable ne peut être identifié.",
                    ],
                    clarification_questions=[
                        f"La description fait référence à {', '.join(ticket_keys)}. "
                        "Veuillez fournir le contenu fonctionnel détaillé de ces tickets."
                    ],
                )
        else:
            # Description vague sans référence ticket identifiable
            return StoryAnalysisResult(
                story_id=story.get("id", ""),
                story_title=story.get("summary") or story.get("title") or "",
                story_type="invalid_or_too_weak",
                recommended_test_type="manual",
                actors=[],
                actions=[],
                business_rules=[],
                technical_scope=[],
                testable_points=[],
                user_flows=[],
                acceptance_criteria_explicit=[],
                acceptance_criteria_inferred=[],
                analysis_reason=[
                    "La description est trop vague pour identifier un comportement utilisateur.",
                    f"Description reçue : \"{description[:100]}\"",
                ],
                clarification_questions=[
                    "La description ne fournit aucun détail fonctionnel exploitable. "
                    "Veuillez préciser les actions attendues, les écrans concernés "
                    "et les résultats observables."
                ],
            )

    system_prompt = build_story_analysis_system_prompt()
    user_prompt = build_story_analysis_user_prompt(enriched_story, rag_context=rag_context)

    raw_response = llm_callable(system_prompt, user_prompt)
    data = extract_json_object(raw_response)

    # Fallback: extract actors from description if LLM returned empty actors
    if not data.get("actors"):
        data["actors"] = _extract_actors_from_description(story)

    if not data.get("story_id"):
        data["story_id"] = story.get("id", "")
    if not data.get("story_title"):
        data["story_title"] = story.get("summary") or story.get("title") or ""

    # Fix empty required fields with safe defaults
    if not data.get("story_type"):
        data["story_type"] = "invalid_or_too_weak"
    if not data.get("recommended_test_type"):
        data["recommended_test_type"] = "manual"

    # Normaliser les variantes courantes renvoyées par le LLM
    _test_type_map = {
        "manuel": "manual",
        "manuelle": "manual",
        "automatise": "automated",
        "automatisee": "automated",
        "automatisée": "automated",
        "automatisé": "automated",
        "automated": "automated",
        "automatic": "automated",
        "needs_refinement": "manual",
        "a affiner": "manual",
        "à affiner": "manual",
    }
    raw_type = (data.get("recommended_test_type") or "").strip().lower()
    data["recommended_test_type"] = _test_type_map.get(raw_type, data["recommended_test_type"])

    # Aplatir user_flows si le LLM renvoie des sous-listes
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

    return validated


def analyze_story_with_groq(
    story: Dict[str, Any],
    model_alias: str = "llama33",
    rag_context: list = None,
) -> StoryAnalysisResult:
    """
    Groq-specific helper.
    """

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
    )