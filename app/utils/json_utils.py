import json
import re
from typing import Dict, Any


def _strip_llm_wrappers(text: str) -> str:
    text = text.strip()
    text = re.sub(r" międzynarodow\s*json\s*", "", text, flags=re.DOTALL).strip()
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    return text.strip()


def _extract_balanced_json_object(text: str) -> str:
    start = text.find("{")
    if start == -1:
        raise ValueError("Aucun JSON trouvé dans la réponse du modèle.")

    depth = 0
    in_string = False
    escape = False

    for index in range(start, len(text)):
        char = text[index]

        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]

    return text[start:]


def _close_unterminated_json(raw_json: str) -> str:
    stack: list[str] = []
    in_string = False
    escape = False

    for char in raw_json:
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char in "[{":
            stack.append("}" if char == "{" else "]")
        elif char in "]}":
            if stack and stack[-1] == char:
                stack.pop()

    fixed = raw_json.rstrip()
    if in_string:
        fixed += '"'

    while stack:
        fixed += stack.pop()

    return fixed


def _fix_trailing_commas(text: str) -> str:
    """Remove trailing commas before } or ] (common LLM mistake)."""
    text = re.sub(r",\s*}", "}", text)
    text = re.sub(r",\s*]", "]", text)
    return text


def extract_json_from_llm_response(text: str) -> Dict[str, Any]:
    """
    Extrait le premier bloc JSON trouvé dans une réponse texte.
    """
    if not text:
        raise ValueError("Réponse vide du modèle.")

    cleaned_text = _strip_llm_wrappers(text)

    try:
        return json.loads(cleaned_text)
    except json.JSONDecodeError:
        pass

    # Try fixing trailing commas on full text
    fixed_text = _fix_trailing_commas(cleaned_text)
    try:
        return json.loads(fixed_text)
    except json.JSONDecodeError:
        pass

    raw_json = _extract_balanced_json_object(cleaned_text)

    try:
        return json.loads(raw_json)
    except json.JSONDecodeError:
        pass

    # Fix trailing commas + close unterminated structures
    repaired_json = _fix_trailing_commas(_close_unterminated_json(raw_json))
    try:
        return json.loads(repaired_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON invalide renvoyé par le modèle: {exc}") from exc


def load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)