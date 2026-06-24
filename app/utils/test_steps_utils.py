"""Utilitaires partagés pour la structure étapes / steps des tests manuels."""
from __future__ import annotations

import copy
import re
from typing import Any, Dict, List

_ACTOR_PREFIX_RE = re.compile(r"^\s*\[[^\]]+\]\s*")
_TECHNICAL_TEST_NAME_RE = re.compile(
    r"^(?:[A-Z][A-Z0-9]*-\d+-(?:NOM|ALT|EXC)-\d+\s+)",
    re.IGNORECASE,
)


def _as_dict(obj: Any) -> Dict[str, Any]:
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return {}


def strip_actor_prefix(text: str) -> str:
    """Retire un préfixe [Acteur] en début de texte."""
    return _ACTOR_PREFIX_RE.sub("", (text or "").strip()).strip()


def display_test_name(name: str) -> str:
    """Nom affiché sans préfixe technique STORY-NOM-001."""
    cleaned = _TECHNICAL_TEST_NAME_RE.sub("", (name or "").strip()).strip()
    return cleaned or (name or "").strip() or "—"


def normalize_test_display_name(name: str) -> str:
    """Normalise le nom de test pour stockage/affichage (sans préfixe technique)."""
    return display_test_name(name) if name else ""


def get_etape_actor(etape: Dict[str, Any]) -> str:
    """Retourne l'acteur associé à une étape (jamais depuis les sous-étapes)."""
    ed = _as_dict(etape)
    actor = (ed.get("actor") or "").strip()
    if actor:
        return actor
    for step in ed.get("steps") or []:
        sd = _as_dict(step)
        actor = (sd.get("actor") or "").strip()
        if actor:
            return actor
        actor = _extract_actor_from_data(sd.get("data") or "")
        if actor:
            return actor
    return ""


def format_etape_title(titre: str, actor: str = "") -> str:
    """Format d'affichage d'une étape : [Acteur] titre."""
    titre = (titre or "").strip()
    actor = (actor or "").strip()
    if not titre:
        return f"[{actor}]" if actor else ""
    if actor:
        return f"[{actor}] {titre}"
    return titre


def format_substep_action(step: Dict[str, Any]) -> str:
    """Action d'une sous-étape sans acteur (acteur porté par l'étape parente)."""
    action = strip_actor_prefix((step.get("action") or "").strip())
    return action or "—"


def apply_etape_level_actors(test: Dict[str, Any]) -> Dict[str, Any]:
    """Assure que les acteurs restent au niveau étape, pas sur les sous-étapes."""
    test = copy.deepcopy(test)
    normalized: List[Dict[str, Any]] = []
    for etape in test.get("étapes") or []:
        ed = _as_dict(etape)
        actor = get_etape_actor(ed)
        ed["actor"] = actor
        cleaned_steps: List[Dict[str, Any]] = []
        for step in ed.get("steps") or []:
            sd = _as_dict(step)
            sd = normalize_step_fields(sd, index=int(sd.get("index") or 1))
            sd["actor"] = ""
            sd["action"] = strip_actor_prefix(sd.get("action") or "")
            cleaned_steps.append(sd)
        ed["steps"] = cleaned_steps
        normalized.append(ed)
    test["étapes"] = normalized
    return test


def ensure_etapes_structure(test: Dict[str, Any]) -> Dict[str, Any]:
    """Convertit steps plats en étapes si nécessaire pour l'édition."""
    test = copy.deepcopy(test)
    if test.get("étapes"):
        return test
    steps = test.get("steps") or []
    if not steps:
        test["étapes"] = []
        return test
    etapes: List[Dict[str, Any]] = []
    for idx, step in enumerate(steps, 1):
        sd = _as_dict(step)
        actor = (sd.get("actor") or "").strip() or _extract_actor_from_data(sd.get("data") or "")
        action = strip_actor_prefix(sd.get("action") or "")
        titre = action[:80] if action else f"Étape {idx}"
        etapes.append({
            "titre": titre,
            "actor": actor,
            "steps": [{
                "index": 1,
                "action": action,
                "data": sd.get("data") or "",
                "actor": "",
                "expected_result": sd.get("expected_result") or "",
                "revision_po": sd.get("revision_po") or "",
            }],
        })
    test["étapes"] = etapes
    return test


def finalize_edited_test(test: Dict[str, Any]) -> Dict[str, Any]:
    """Normalise un test après édition manuelle ou IA."""
    test = ensure_etapes_structure(test)
    test = normalize_test_etapes_and_steps(test)
    test = apply_etape_level_actors(test)
    test["steps"] = flatten_test_steps(test)
    test["description"] = build_xray_description(test)
    return test


def normalize_step_fields(step: Dict[str, Any], *, index: int, default_actor: str = "") -> Dict[str, Any]:
    """Normalise les champs d'une action atomique."""
    import json

    s = dict(step)
    s["index"] = index
    for key in ("action", "data", "actor", "expected_result", "revision_po"):
        val = s.get(key, "")
        if val is None:
            val = ""
        if not isinstance(val, str):
            val = json.dumps(val, ensure_ascii=False) if val else ""
        s[key] = val.strip() if key != "action" else val

    if not s.get("actor") and default_actor:
        s["actor"] = default_actor
    if not s.get("data") and s.get("actor"):
        s["data"] = f"en tant que {s['actor']}"
    if "revision_po" not in s:
        s["revision_po"] = ""
    return s


def flatten_test_steps(test: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Retourne la liste plate des actions (depuis étapes ou steps)."""
    etapes = test.get("étapes") or []
    if etapes:
        flat: List[Dict[str, Any]] = []
        idx = 1
        for etape in etapes:
            ed = _as_dict(etape)
            etape_actor = (ed.get("actor") or "").strip()
            for step in ed.get("steps") or []:
                if isinstance(step, str):
                    step = {"action": step, "data": "", "actor": "", "expected_result": ""}
                flat.append(normalize_step_fields(_as_dict(step), index=idx, default_actor=etape_actor))
                idx += 1
        return flat
    return [normalize_step_fields(_as_dict(s), index=i, default_actor="") for i, s in enumerate(test.get("steps") or [], 1)]


def normalize_test_etapes_and_steps(test: Dict[str, Any]) -> Dict[str, Any]:
    """Normalise étapes + steps et synchronise les deux structures."""
    etapes = test.get("étapes") or []
    if etapes:
        normalized_etapes: List[Dict[str, Any]] = []
        for etape in etapes:
            ed = _as_dict(etape)
            etape_actor = (ed.get("actor") or "").strip()
            etape_steps: List[Dict[str, Any]] = []
            for s_idx, step in enumerate(ed.get("steps") or [], 1):
                if isinstance(step, str):
                    step = {"action": step, "data": "", "actor": "", "expected_result": ""}
                etape_steps.append(normalize_step_fields(_as_dict(step), index=s_idx, default_actor=etape_actor))
            ed["titre"] = (ed.get("titre") or "").strip()
            ed["actor"] = etape_actor
            ed["steps"] = etape_steps
            normalized_etapes.append(ed)
        test["étapes"] = normalized_etapes
        test["steps"] = flatten_test_steps(test)
    else:
        steps = []
        for s_idx, step in enumerate(test.get("steps") or [], 1):
            if isinstance(step, str):
                step = {"action": step, "data": "", "actor": "", "expected_result": ""}
            steps.append(normalize_step_fields(_as_dict(step), index=s_idx))
        test["steps"] = steps

    if not (test.get("description") or "").strip():
        test["description"] = build_xray_description(test)
    return test


def bold_first_word(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    parts = text.split(None, 1)
    if len(parts) == 2:
        return f"**{parts[0]}** {parts[1]}"
    return f"**{text}**"


def build_xray_description_line(actor: str, titre: str) -> str:
    """Format Jira/Xray : [Acteur] **Verbe** reste du titre."""
    actor = (actor or "").strip()
    titre = (titre or "").strip()
    if not titre:
        return ""
    actor_part = f"[{actor}] " if actor else ""
    return f"{actor_part}{bold_first_word(titre)}"


def build_xray_description(test: Dict[str, Any]) -> str:
    """Construit la description Xray à partir des titres d'étapes."""
    etapes = test.get("étapes") or []
    if etapes:
        lines = []
        for etape in etapes:
            ed = _as_dict(etape)
            titre = (ed.get("titre") or "").strip()
            actor = get_etape_actor(ed)
            line = build_xray_description_line(actor, titre)
            if line:
                lines.append(line)
        if lines:
            return "\n".join(lines)

    steps = test.get("steps") or []
    if steps:
        lines = []
        for step in steps:
            sd = _as_dict(step)
            action = (sd.get("action") or "").strip()
            actor = (sd.get("actor") or "").strip()
            if not actor:
                actor = _extract_actor_from_data(sd.get("data") or "")
            if action:
                actor_part = f"[{actor}] " if actor else ""
                lines.append(f"{actor_part}{bold_first_word(action)}")
        return "\n".join(lines)
    return (test.get("description") or "").strip()


def _extract_actor_from_data(data: str) -> str:
    text = (data or "").strip()
    if not text:
        return ""
    m = re.search(r"en tant que\s+([^,;\.]+?)(?:\s+des?\b|\s+du\b|\s+de\b|\s+pour\b|$)", text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return text


def format_action_with_actor(action: str, actor: str = "", data: str = "", *, include_actor: bool = True) -> str:
    """Formate une action ; par défaut avec acteur, sauf pour les sous-étapes (include_actor=False)."""
    action = strip_actor_prefix((action or "").strip())
    if not include_actor:
        return action or "—"
    actor = (actor or "").strip()
    if not actor:
        actor = _extract_actor_from_data(data)
    if actor and action:
        return f'<span class="step-actor">[{actor}]</span> {action}'
    return action or "—"
