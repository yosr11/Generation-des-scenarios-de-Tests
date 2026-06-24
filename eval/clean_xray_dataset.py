"""Nettoie le dataset Xray brut et le normalise au format Agent 2.

Entrée  : JSON produit par POST /projects/dataset/enrich
Sortie  : JSON où chaque test linké suit le schéma de l'Agent 2
          (story_id, test_name, objective, execution_context, preconditions,
           scenario_type, priority, labels, steps[{index, action, actor,
           expected_result, revision_po}])

Usage   :
    python eval/clean_xray_dataset.py [input.json] [output.json]

Defaults: input  = eval/dataset_raw.json
          output = eval/dataset_cleaned.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

# --- Regex de nettoyage Jira markup -------------------------------------

_RE_COLOR = re.compile(r"\{color(?::#[0-9a-fA-F]{3,8})?\}(.*?)\{color\}", re.DOTALL)
_RE_COLOR_ORPHAN = re.compile(r"\{color(?::#[0-9a-fA-F]{3,8})?\}|\{color\}")
_RE_TITLE_BOLD = re.compile(r"\+\*(.+?)\*\+")
_RE_BOLD = re.compile(r"(?<!\w)\*([^*\n]+?)\*(?!\w)")
_RE_ITALIC = re.compile(r"(?<![\w_])_([^_\n]+?)_(?![\w_])")
_RE_UNDERLINE = re.compile(r"\+([^+\n]+?)\+")
_RE_LINK = re.compile(r"\[([^\]|]+)\|[^\]]+\]")
_RE_MULTI_SPACE = re.compile(r"[ \t]+")
_RE_MULTI_NEWLINE = re.compile(r"\n{3,}")

_ACTOR_PATTERN = re.compile(r"^\s*\[\s*([^\]\n]{2,40}?)\s*\]")
_PRIORITY_PREFIX = re.compile(r"^P\d+\s*[-:]?\s*", re.IGNORECASE)


def strip_jira_markup(text: str) -> str:
    if not text:
        return ""
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    # Couleurs imbriquées : appliquer plusieurs passes
    for _ in range(3):
        new = _RE_COLOR.sub(r"\1", t)
        if new == t:
            break
        t = new
    # Tags couleurs orphelins (markup Jira cassé : ouverture sans fermeture)
    t = _RE_COLOR_ORPHAN.sub("", t)
    t = _RE_TITLE_BOLD.sub(r"\1", t)
    t = _RE_LINK.sub(r"\1", t)
    t = _RE_UNDERLINE.sub(r"\1", t)
    t = _RE_BOLD.sub(r"\1", t)
    t = _RE_ITALIC.sub(r"\1", t)
    # Nettoyage espaces
    lines = [_RE_MULTI_SPACE.sub(" ", line).rstrip() for line in t.split("\n")]
    t = "\n".join(lines)
    t = _RE_MULTI_NEWLINE.sub("\n\n", t).strip()
    return t


def _split_bullets(text: str) -> list[str]:
    """Découpe un bloc en items en se basant sur les marqueurs - / * en début de ligne."""
    if not text:
        return []
    items: list[str] = []
    current: list[str] = []
    for raw_line in text.split("\n"):
        line = raw_line.rstrip()
        stripped = line.lstrip()
        is_bullet = bool(re.match(r"^[-*]\s+", stripped))
        if is_bullet:
            if current:
                items.append(" ".join(current).strip())
                current = []
            current.append(re.sub(r"^[-*]\s+", "", stripped))
        else:
            if stripped:
                current.append(stripped)
    if current:
        items.append(" ".join(current).strip())
    return [it for it in items if it]


def _extract_actor(text: str) -> tuple[str, str]:
    """Retourne (actor, texte_sans_marqueur_acteur).
    Détecte un préfixe '[Collaborateur]' / '[Gestionnaire]' / etc.
    """
    m = _ACTOR_PATTERN.search(text)
    if not m:
        return "", text
    actor = m.group(1).strip()
    cleaned = text[: m.start()] + text[m.end() :]
    return actor, cleaned.strip()


def parse_action(raw_action: str) -> tuple[str, str]:
    """Parse le champ action brut.
    Retourne (actor, action_text).
    Le bloc 'ETAPE : ...' et 'ACTION(S) :' sont retirés.
    Les bullets sont conservés mais normalisés.
    """
    text = strip_jira_markup(raw_action)
    if not text:
        return "", ""

    # Découpe au bloc ACTION(S)
    parts = re.split(r"ACTION\s*\(?S?\)?\s*[:.]", text, maxsplit=1, flags=re.IGNORECASE)
    if len(parts) == 2:
        header, body = parts[0], parts[1]
    else:
        header, body = text, ""

    # Retire le préfixe "ETAPE :"
    header = re.sub(r"^\s*ETAPE\s*[:.]\s*", "", header, flags=re.IGNORECASE).strip()
    actor, header_clean = _extract_actor(header)

    # Body : bullets nettoyés
    bullets = _split_bullets(body)
    if bullets:
        body_text = "\n".join(f"- {b}" for b in bullets)
    else:
        body_text = body.strip()

    # Compose : description courte (étape) + actions
    if header_clean and body_text:
        action_text = f"{header_clean}\n{body_text}"
    else:
        action_text = header_clean or body_text

    return actor, action_text.strip()


def parse_expected_result(raw: str) -> str:
    text = strip_jira_markup(raw)
    bullets = _split_bullets(text)
    if bullets:
        return "\n".join(f"- {b}" for b in bullets)
    return text.strip()


def normalize_priority(p: str | None) -> str:
    if not p:
        return ""
    cleaned = _PRIORITY_PREFIX.sub("", p).strip()
    return cleaned or p


def clean_description(description: str | None) -> str:
    if not description:
        return ""
    return strip_jira_markup(description)


def derive_test_name(summary: str | None) -> str:
    if not summary:
        return ""
    return re.sub(r"\s+", " ", summary).strip()


def derive_objective(summary: str | None, description: str | None) -> str:
    """Heuristique simple : la partie après le dernier '-' du summary,
    sinon la 1ère ligne nettoyée de la description."""
    if summary:
        s = summary.strip()
        # Le summary commence souvent par CODE_S1_ST2_CT1 - <objectif>
        m = re.match(r"^[A-Z0-9_]+\s*[-:]\s*(.+)$", s)
        if m:
            return m.group(1).strip()
        return s
    if description:
        first = strip_jira_markup(description).split("\n", 1)[0]
        return first.strip()
    return ""


def convert_test(raw_test: dict[str, Any], story_id: str) -> dict[str, Any]:
    steps_out: list[dict[str, Any]] = []
    for step in raw_test.get("steps") or []:
        raw_action = (step.get("action") or {}).get("raw") or ""
        raw_expected = (step.get("expected_result") or {}).get("raw") or ""
        actor, action_text = parse_action(raw_action)
        steps_out.append(
            {
                "index": step.get("index"),
                "action": action_text,
                "actor": actor,
                "expected_result": parse_expected_result(raw_expected),
                "revision_po": "",
            }
        )

    return {
        "story_id": story_id,
        "source_test_key": raw_test.get("key"),
        "test_name": derive_test_name(raw_test.get("summary")),
        "objective": derive_objective(raw_test.get("summary"), raw_test.get("description")),
        "description": clean_description(raw_test.get("description")),
        "execution_context": "",
        "preconditions": [],  # Xray ne sépare pas les préconditions ; champ vide pour parité Agent 2
        "scenario_type": "",  # non fourni par Xray ; à inférer plus tard si besoin
        "priority": normalize_priority(raw_test.get("priority")),
        "labels": raw_test.get("labels") or [],
        "components": raw_test.get("components") or [],
        "steps": steps_out,
        "steps_count": len(steps_out),
        "link_type": raw_test.get("link_type", ""),
    }


def clean_dataset(raw: dict[str, Any]) -> dict[str, Any]:
    stories_out: list[dict[str, Any]] = []
    total_tests = 0
    for story in raw.get("stories") or []:
        story_id = story.get("key", "")
        tests = [convert_test(t, story_id) for t in (story.get("linked_tests") or [])]
        total_tests += len(tests)
        stories_out.append(
            {
                "key": story_id,
                "summary": (story.get("summary") or "").strip(),
                "status": story.get("status", ""),
                "linked_tests_count": len(tests),
                "linked_tests": tests,
            }
        )

    return {
        "project_key": raw.get("project_key"),
        "jql": raw.get("jql"),
        "total_stories": len(stories_out),
        "total_tests": total_tests,
        "stories": stories_out,
    }


def main(argv: list[str]) -> int:
    repo_root = Path(__file__).resolve().parent.parent
    default_in = repo_root / "eval" / "dataset_raw.json"
    default_out = repo_root / "eval" / "dataset_cleaned.json"

    in_path = Path(argv[1]) if len(argv) > 1 else default_in
    out_path = Path(argv[2]) if len(argv) > 2 else default_out

    if not in_path.exists():
        print(f"[ERREUR] Fichier introuvable : {in_path}", file=sys.stderr)
        return 1

    raw = json.loads(in_path.read_text(encoding="utf-8"))
    cleaned = clean_dataset(raw)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(cleaned, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        f"[OK] {cleaned['total_stories']} stories / {cleaned['total_tests']} tests "
        f"nettoyés -> {out_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
