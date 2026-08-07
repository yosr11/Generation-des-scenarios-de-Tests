"""
app/utils/cleaning.py
─────────────────────────────────────────────────────────────────────
Nettoyage des données brutes Jira / XRAY — Sopra HR Software.

Objectifs :
  - conserver le texte brut
  - produire une version lisible humain
  - produire une version optimisée pour le LLM
  - extraire les références utiles (URLs, tickets, story ids, JDD ids, environnements, test users)
  - calculer quelques flags QA utiles avant appel LLM
  - nettoyer aussi les autres champs utiles d'une story :
      * summary / title
      * labels
      * components
      * issuelinks
      * fixVersions
      * requirement_status

Problèmes réels identifiés sur les tickets Jira :
  - HTML Jira  : <p>, <span class="error">, <b>, &#91;, &amp;...
  - Wiki markup: *gras*, +souligné+, h4., {color:#xxx}, {{code}},
                 {test-param}xxx{test-param}, [texte|url]
  - liens utiles dans la description
  - références ticket/story/JDD importantes
  - descriptions incomplètes, ".....", finissant par "et", etc.
"""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional

# ══════════════════════════════════════════════════════════════
#  1. STRIP HTML (avec préservation des sauts de ligne)
# ══════════════════════════════════════════════════════════════

_BLOCK_TAGS = {"p", "li", "br", "div", "h1", "h2", "h3", "h4", "h5", "h6", "tr"}


class _HTMLStripper(HTMLParser):
    def __init__(self):
        # convert_charrefs=False: handle entities ourselves and avoid the
        # HTMLParser bug where a stray '&' (e.g. "R&D") silently swallows
        # trailing data when the input ends mid-entity.
        super().__init__(convert_charrefs=False)
        self._parts: List[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() in _BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag):
        if tag.lower() in _BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data: str):
        self._parts.append(data)

    def handle_entityref(self, name):
        decoded = html.unescape(f"&{name};")
        # If unescape returned the literal "&name;" it means the entity is
        # unknown (e.g. "R&D" -> handle_entityref("D")). Emit the source form
        # without the synthetic ';' to avoid corrupting plain text.
        if decoded == f"&{name};":
            self._parts.append(f"&{name}")
        else:
            self._parts.append(decoded)

    def handle_charref(self, name):
        self._parts.append(html.unescape(f"&#{name};"))

    def get_text(self) -> str:
        return "".join(self._parts)


def strip_html(text: str) -> str:
    if not text:
        return ""
    stripper = _HTMLStripper()
    stripper.feed(text)
    stripper.close()
    return stripper.get_text()


# ══════════════════════════════════════════════════════════════
#  2. STRIP JIRA WIKI MARKUP
# ══════════════════════════════════════════════════════════════

_WIKI_RULES: List[tuple[re.Pattern, str]] = [
    # !image.png|width=x,height=y!  →  [capture d'écran]
    (
        re.compile(
            r"![^\s!]+\.(png|jpg|jpeg|gif|svg|PNG|JPG|JPEG)[^!]*!", re.IGNORECASE
        ),
        "[capture d'écran]",
    ),
    # {color:#xxx}texte{color}  →  texte
    (re.compile(r"\{color[^}]*\}(.*?)\{color\}", re.DOTALL), r"\1"),
    # {test-param}xxx{test-param}  →  [xxx]
    (re.compile(r"\{test-param\}(.*?)\{test-param\}", re.DOTALL), r"[\1]"),
    # {{code}}  →  code
    (re.compile(r"\{\{(.*?)\}\}", re.DOTALL), r"\1"),
    # {balises génériques} → rien
    (re.compile(r"\{[^}]+\}"), ""),
    # +texte+ → texte
    (re.compile(r"\+(.*?)\+", re.DOTALL), r"\1"),
    # *texte* → texte (gras inline, pas les bullets)
    (re.compile(r"(?<!\n)\*([^*\n]+)\*"), r"\1"),
    # _texte_ → texte
    (re.compile(r"_([^_\n]+)_"), r"\1"),
    # [texte|url] → texte (url)
    (re.compile(r"\[([^\]|]+)\|(https?://[^\]]+)\]"), r"\1 (\2)"),
    # [url seule] → url
    (re.compile(r"\[(https?://[^\]]+)\]"), r"\1"),
    # h1. / h2. / ...
    (re.compile(r"(?im)^\s*h[1-6]\.\s*"), ""),
    # séparateurs ----
    (re.compile(r"(?m)^\s*-{4,}\s*$"), ""),
    # * bullet début de ligne
    (re.compile(r"(?m)^\s*\*+\s*"), ""),
    # # numérotation wiki
    (re.compile(r"(?m)^\s*#+\s*"), ""),
    # étoiles résiduelles isolées
    (re.compile(r"\*+"), ""),
    # espaces multiples
    (re.compile(r"[ \t]{2,}"), " "),
]


def strip_jira_wiki(text: str) -> str:
    if not text:
        return ""
    for pattern, repl in _WIKI_RULES:
        text = pattern.sub(repl, text)
    return text.strip()


# ══════════════════════════════════════════════════════════════
#  3. NETTOYAGE TEXTE DE BASE
# ══════════════════════════════════════════════════════════════


def clean_text(raw: Optional[str]) -> str:
    """
    Nettoyage de base :
      1. decode HTML entities
      2. strip HTML
      3. decode à nouveau
      4. strip wiki markup Jira
      5. normalisation whitespace / lignes
    """
    if not raw:
        return ""

    text = html.unescape(raw)
    text = strip_html(text)
    text = html.unescape(text)
    text = strip_jira_wiki(text)

    # Normalisation sauts de ligne
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Nettoyage ligne à ligne
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line and line != "."]

    text = "\n".join(lines)

    # espaces multiples
    text = re.sub(r"[ \t]{2,}", " ", text)

    return text.strip()


# ══════════════════════════════════════════════════════════════
#  4. HELPERS GÉNÉRAUX
# ══════════════════════════════════════════════════════════════


def _unique_keep_order(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def clean_scalar_text(value: Optional[str]) -> str:
    """
    Nettoyage léger d'un champ texte simple.
    """
    return clean_text(value or "")


def clean_string_list(values: Optional[List[Any]]) -> List[str]:
    """
    Nettoie une liste de chaînes :
      - supprime None / vide
      - applique clean_text
      - enlève les doublons en conservant l'ordre
    """
    if not values:
        return []

    cleaned: List[str] = []
    for value in values:
        if value is None:
            continue
        text = clean_text(str(value))
        if text:
            cleaned.append(text)

    return _unique_keep_order(cleaned)


# ══════════════════════════════════════════════════════════════
#  5. EXTRACTION DES RÉFÉRENCES
# ══════════════════════════════════════════════════════════════

URL_RE = re.compile(r"https?://[^\s)\]>]+", re.IGNORECASE)
ISSUE_KEY_RE = re.compile(r"\b[A-Z][A-Z0-9]+-\d+\b")
ENV_RE = re.compile(r"\bPR\d+\b", re.IGNORECASE)

# Comptes de test type :
# QARECCH8/QAGESCH
# QCOLLYS1/4YOU
# QGESTYS4/4YOU
TEST_USER_RE = re.compile(r"\b[A-Z0-9]+/[A-Z0-9]+\b")


def extract_urls(text: str) -> List[str]:
    if not text:
        return []
    return _unique_keep_order(URL_RE.findall(text))


def extract_issue_keys(text: str) -> List[str]:
    if not text:
        return []
    return _unique_keep_order(ISSUE_KEY_RE.findall(text))


def extract_env_codes(text: str) -> List[str]:
    if not text:
        return []
    return _unique_keep_order([x.upper() for x in ENV_RE.findall(text)])


def extract_test_users(text: str) -> List[str]:
    """
    Extrait les comptes utilisateurs de test du type :
      QARECCH8/QAGESCH
      QCOLLYS1/4YOU
      QGESTYS4/4YOU
    """
    if not text:
        return []
    return _unique_keep_order(TEST_USER_RE.findall(text))


def extract_references(text: str) -> Dict[str, List[str]]:
    """
    Extrait les références utiles depuis le texte nettoyé.
    """
    issue_keys = extract_issue_keys(text)
    env_codes = extract_env_codes(text)
    urls = extract_urls(text)
    test_users = extract_test_users(text)

    story_ids: List[str] = []
    jdd_ids: List[str] = []
    related_ticket_ids: List[str] = []

    lines = text.splitlines()

    for line in lines:
        keys = ISSUE_KEY_RE.findall(line)
        if not keys:
            continue

        lower = line.lower()

        if "story" in lower:
            story_ids.extend(keys)
        elif "jdd" in lower:
            jdd_ids.extend(keys)
        else:
            related_ticket_ids.extend(keys)

    return {
        "urls": _unique_keep_order(urls),
        "issue_keys": _unique_keep_order(issue_keys),
        "story_ids": _unique_keep_order(story_ids),
        "jdd_ids": _unique_keep_order(jdd_ids),
        "related_ticket_ids": _unique_keep_order(related_ticket_ids),
        "env_codes": _unique_keep_order(env_codes),
        "test_users": _unique_keep_order(test_users),
    }


# ══════════════════════════════════════════════════════════════
#  6. FLAGS HEURISTIQUES UTILES POUR LE QA / LLM
# ══════════════════════════════════════════════════════════════

TECH_KEYWORDS = [
    "api",
    "backend",
    "patch",
    "script",
    "sql",
    "migration",
    "assembly",
    "déploiement",
    "deployment",
    "config",
    "configuration",
    "rf80",
    "rg0",
    "dao",
    "batch",
    "job",
    "logs",
    "mapping",
    "endpoint",
    "legacy hra",
    "karaf",
    "pom",
    "maven",
    "release",
    "releasing",
    "devops",
    "cleaning",
]

# volontairement strict pour éviter de marquer à tort comme JDD
JDD_KEYWORDS = [
    "jdd",
    "jeu de données",
    "données de test",
    "manque de jdd",
    "besoin d'un collab",
    "besoin de deux collabs",
    "compteur",
    "solde",
    "soldes congée",
    "soldes congé",
    "email",
    "utilisateurs de test",
]


def build_flags(text: str, labels: Optional[List[str]] = None) -> Dict[str, Any]:
    if not text:
        return {
            "has_url": False,
            "has_issue_key": False,
            "has_env_code": False,
            "has_test_users": False,
            "has_ellipsis": False,
            "ends_with_and": False,
            "too_short": True,
            "contains_jdd_signal": False,
            "contains_technical_signal": False,
        }

    labels = labels or []
    lowered = text.lower().strip()

    has_url = bool(URL_RE.search(text))
    has_issue_key = bool(ISSUE_KEY_RE.search(text))
    has_env_code = bool(ENV_RE.search(text))
    has_test_users = bool(TEST_USER_RE.search(text))
    has_ellipsis = "..." in text or "….." in text
    ends_with_and = lowered.endswith("et") or lowered.endswith("and")
    too_short = len(text) < 15

    labels_lower = [label.lower() for label in labels]

    contains_jdd_signal = (
        any(keyword in lowered for keyword in JDD_KEYWORDS) or "jdd" in labels_lower
    )

    contains_technical_signal = any(keyword in lowered for keyword in TECH_KEYWORDS)

    return {
        "has_url": has_url,
        "has_issue_key": has_issue_key,
        "has_env_code": has_env_code,
        "has_test_users": has_test_users,
        "has_ellipsis": has_ellipsis,
        "ends_with_and": ends_with_and,
        "too_short": too_short,
        "contains_jdd_signal": contains_jdd_signal,
        "contains_technical_signal": contains_technical_signal,
    }


# ══════════════════════════════════════════════════════════════
#  7. DESCRIPTION OPTIMISÉE POUR LE LLM
# ══════════════════════════════════════════════════════════════


def optimize_description_for_llm(text: str) -> str:
    """
    Optimise une description déjà nettoyée pour le LLM :
      - remplace les URLs longues par [URL]
      - normalise certains marqueurs (Ticket:, Story:, RQ:, User:…)
      - retire un peu de bruit sans inventer
    """
    if not text:
        return ""

    # Remplacement des URLs brutes par un marqueur
    text = URL_RE.sub("[URL]", text)

    # Normalisation légère des marqueurs fréquents
    text = re.sub(
        r"(?im)^\s*environnement\s*\[URL\]\s*$",
        "Environnement de test disponible : [URL]",
        text,
    )
    text = re.sub(
        r"(?im)^\s*link\s*:\s*\[URL\]\s*$",
        "Lien vers ressource disponible : [URL]",
        text,
    )
    text = re.sub(
        r"(?im)^\s*ticket\s*:\s*([A-Z][A-Z0-9]+-\d+)\s*$",
        r"Référence ticket liée : \1",
        text,
    )
    text = re.sub(
        r"(?im)^\s*story\s*:\s*([A-Z][A-Z0-9]+-\d+)\s*$",
        r"Référence story liée : \1",
        text,
    )
    text = re.sub(
        r"(?im)^\s*jdd\s*:\s*([A-Z][A-Z0-9]+-\d+)\s*$", r"Référence JDD liée : \1", text
    )
    text = re.sub(r"(?im)^\s*rq\s*:\s*", "Remarque : ", text)
    text = re.sub(r"(?im)^\s*user\s*:\s*", "Compte utilisateur de test : ", text)

    # Normalisation ponctuation / espaces
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Nettoyage ligne à ligne
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]

    # Déduplication légère de lignes identiques
    deduped_lines: List[str] = []
    seen = set()
    for line in lines:
        key = line.lower()
        if key not in seen:
            seen.add(key)
            deduped_lines.append(line)

    return "\n".join(deduped_lines).strip()


# ══════════════════════════════════════════════════════════════
#  8. NETTOYAGE DES STRUCTURES COMPLEXES
# ══════════════════════════════════════════════════════════════


def clean_issuelinks(
    issuelinks: Optional[List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """
    Nettoie les issue links aplatis.
    On suppose une structure du type :
      {
        "type": "...",
        "direction": "...",
        "key": "...",
        "summary": "...",
        "status": "...",
        "description": "..."
      }
    """
    if not issuelinks:
        return []

    cleaned_links: List[Dict[str, Any]] = []

    for link in issuelinks:
        if not isinstance(link, dict):
            continue

        cleaned_links.append(
            {
                "type": clean_scalar_text(link.get("type")),
                "direction": clean_scalar_text(link.get("direction")),
                "key": clean_scalar_text(link.get("key")),
                "summary": clean_scalar_text(link.get("summary")),
                "status": clean_scalar_text(link.get("status")),
                "description": clean_text(link.get("description") or ""),
            }
        )

    return cleaned_links


def clean_requirement_status(
    requirement_status: Optional[List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """
    Nettoie légèrement les champs utiles du requirement_status.
    """
    if not requirement_status:
        return []

    cleaned_items: List[Dict[str, Any]] = []

    for item in requirement_status:
        if not isinstance(item, dict):
            continue

        cleaned_items.append(
            {
                "issueKey": clean_scalar_text(item.get("issueKey")),
                "version": clean_scalar_text(item.get("version")),
                "status": clean_scalar_text(item.get("status")),
                "statusStyle": clean_scalar_text(item.get("statusStyle")),
                "ok": item.get("ok", 0),
                "okPercent": item.get("okPercent", 0),
                "nok": item.get("nok", 0),
                "nokPercent": item.get("nokPercent", 0),
                "notrun": item.get("notrun", 0),
                "notrunPercent": item.get("notrunPercent", 0),
                "unknown": item.get("unknown", 0),
                "unknownPercent": item.get("unknownPercent", 0),
            }
        )

    return cleaned_items


# ══════════════════════════════════════════════════════════════
#  9. NETTOYAGE D'UNE STORY
# ══════════════════════════════════════════════════════════════


def clean_story_dict(story: Dict[str, Any]) -> Dict[str, Any]:
    """
    Nettoyage complet d'une story Jira aplatie.
    Produit une version propre pour stockage / analyse.
    Supporte :
      - "summary" ou "title"
      - description
      - labels
      - components
      - issuelinks
      - fixVersions
      - requirement_status
    """
    desc_raw = story.get("description") or ""
    desc_clean = optimize_description_for_llm(clean_text(desc_raw))

    # Acceptance Criteria (champ personnalisé Jira)
    ac_raw = story.get("acceptance_criteria_raw") or ""
    ac_clean = clean_text(ac_raw)

    # support "summary" ou "title"
    summary_raw = story.get("summary") or story.get("title") or ""
    summary_clean = clean_text(summary_raw)

    labels_clean = clean_string_list(story.get("labels") or [])
    components_clean = clean_string_list(story.get("components") or [])

    issuelinks_clean = clean_issuelinks(story.get("issuelinks") or [])

    return {
        "id": clean_scalar_text(story.get("id", "")),
        "summary": summary_clean,
        "title": summary_clean,  # alias pratique si le reste du pipeline utilise title
        "description_clean": desc_clean,
        "acceptance_criteria_clean": ac_clean,
        "labels": labels_clean,
        "components": components_clean,
        "issuelinks": issuelinks_clean,
        "priority": clean_scalar_text(story.get("priority") or ""),
        "status": clean_scalar_text(story.get("status") or ""),
    }


# ══════════════════════════════════════════════════════════════
#  10. CONTEXTE LIENS / STORY POUR LE LLM
# ══════════════════════════════════════════════════════════════


def build_story_context_for_llm(story: Dict[str, Any]) -> str:
    """
    Construit le contexte à envoyer au LLM :
    summary, description_clean, acceptance_criteria_clean, components, labels.
    """
    parts: List[str] = []

    summary = story.get("summary") or story.get("title") or ""
    if summary:
        parts.append(f"Titre : {summary}")

    description_clean = story.get("description_clean") or ""
    if description_clean:
        parts.append(f"Description :\n{description_clean}")

    ac_clean = story.get("acceptance_criteria_clean") or ""
    if ac_clean:
        parts.append(f"Critères d'acceptation :\n{ac_clean}")

    labels = story.get("labels") or []
    if labels:
        parts.append("Labels : " + ", ".join(labels))

    components = story.get("components") or []
    if components:
        parts.append("Composants : " + ", ".join(components))

    return "\n\n".join(parts).strip()


# ══════════════════════════════════════════════════════════════
#  11. UTILITAIRES JIRA
# ══════════════════════════════════════════════════════════════


def flatten_issuelinks(raw_links: list) -> List[Dict[str, str]]:
    """Transforme les issuelinks Jira (très imbriqués) en liste plate."""
    out: List[Dict[str, str]] = []
    for link in raw_links:
        link_type = (link.get("type") or {}).get("name", "")
        for direction in ("inwardIssue", "outwardIssue"):
            target = link.get(direction)
            if target:
                out.append(
                    {
                        "type": link_type,
                        "direction": direction.replace("Issue", ""),
                        "key": target.get("key", ""),
                        "summary": (target.get("fields") or {}).get("summary", ""),
                        "status": (
                            (target.get("fields") or {}).get("status") or {}
                        ).get("name", ""),
                    }
                )
    return out


# ══════════════════════════════════════════════════════════════
#  12. ENRICHISSEMENT POUR LE LLM
# ══════════════════════════════════════════════════════════════


def enrich_story_for_llm(story: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enrichit une story déjà nettoyée avec :
      - summary/title propre
      - linked_summaries_clean
      - linked_keys_clean
      - story_context_llm
    """

    # 1) Nettoyage / normalisation du résumé
    summary_clean = clean_text(
        story.get("summary") or story.get("title") or story.get("summary_raw") or ""
    )

    # 2) Nettoyage / normalisation de la description
    description_clean = story.get("description_clean") or optimize_description_for_llm(
        clean_text(story.get("description_raw") or story.get("description") or "")
    )

    # 3) Récupération + nettoyage des résumés des tickets liés
    linked_summaries = [
        link.get("summary", "")
        for link in (story.get("issuelinks") or [])
        if isinstance(link, dict) and link.get("summary")
    ]
    linked_summaries_clean = clean_string_list(linked_summaries)

    # 4) Récupération + nettoyage des clés des tickets liés
    linked_keys = [
        clean_text(link.get("key", ""))
        for link in (story.get("issuelinks") or [])
        if isinstance(link, dict) and link.get("key")
    ]
    linked_keys_clean = _unique_keep_order([k for k in linked_keys if k])

    # 5) Story enrichie
    enriched = {
        **story,
        "summary": summary_clean,
        "title": summary_clean,  # alias pratique
        "description_clean": description_clean,
        "linked_summaries_clean": linked_summaries_clean,
        "linked_keys_clean": linked_keys_clean,
    }

    # 6) Contexte final pour le LLM
    enriched["story_context_llm"] = build_story_context_for_llm(enriched)

    return enriched
