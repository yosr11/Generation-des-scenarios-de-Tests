"""
Helpers pour enrichir la réponse pipeline (export JSON / deepEval).

Expose :
  - images liées à la story (description OCR+VLM + URL proxy)
  - agent2_input : tests legacy RAG injectés en few-shot à Agent 2
  - evaluation_export : payload structuré (Agent 1.5 → Agent 2, inputs, images)
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")


def _is_image_filename(filename: str) -> bool:
    return (filename or "").lower().endswith(_IMAGE_EXTS)


def _extract_vlm_description(full_text: str) -> str:
    """Extrait la partie analyse VLM d'un bloc [Image jointe : …]."""
    if not full_text:
        return ""
    marker = "── Analyse visuelle (VLM) ──"
    if marker in full_text:
        return full_text.split(marker, 1)[1].strip()
    header = re.match(r"^\[Image jointe[^\]]*\]\s*", full_text)
    if header:
        return full_text[header.end() :].strip()
    return full_text.strip()


def collect_story_images(story_id: str) -> List[Dict[str, Any]]:
    """
    Retourne les images directement attachées à la story avec leur description texte.
    """
    from app.services.document_collector import (
        _get_attachments,
        collect_story_attachments_only,
    )

    sid = (story_id or "").strip().upper()
    if not sid:
        return []

    try:
        docs = collect_story_attachments_only(sid)
    except Exception:
        docs = []

    attachments = _get_attachments(sid)
    att_by_name = {a.get("filename"): a for a in attachments if a.get("filename")}

    images: List[Dict[str, Any]] = []
    seen_filenames: set[str] = set()

    for doc in docs:
        # Compare origin_key case-insensitively to avoid missing matches
        origin = (doc.get("origin_key") or "").strip().upper()
        if doc.get("source") != "attachment" or origin != sid:
            continue
        filename = doc.get("filename") or ""
        if not _is_image_filename(filename) or filename in seen_filenames:
            continue
        seen_filenames.add(filename)

        full_text = doc.get("text") or ""
        att = att_by_name.get(filename) or {}
        att_id = att.get("id")

        images.append(
            {
                "filename": filename,
                "caption": filename,
                "description": _extract_vlm_description(full_text),
                "description_full": full_text,
                "attachment_id": att_id,
                "url": f"/documents/attachment/{sid}/{att_id}" if att_id else None,
                "source": sid,
            }
        )

    return images


def format_legacy_example_input(example: Dict[str, Any]) -> Dict[str, Any]:
    """Forme compacte d'un test legacy pour l'input Agent 2 / deepEval."""
    pivot = example.get("pivot") or {}
    steps = pivot.get("steps") or []
    return {
        "test_id": example.get("test_id") or pivot.get("test_id"),
        "title": example.get("title") or pivot.get("title"),
        "score": example.get("score"),
        "project": example.get("project"),
        "module_root": example.get("module_root"),
        "description": pivot.get("description"),
        "preconditions": pivot.get("preconditions") or [],
        "steps": steps,
        "steps_count": len(steps),
    }


def build_agent2_input(
    legacy_examples: Optional[List[Dict[str, Any]]] = None,
    rag_context: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    """Input réellement injecté à Agent 2 (few-shot legacy + contexte RAG epic)."""
    examples = legacy_examples or []
    return {
        "legacy_rag_examples": [format_legacy_example_input(e) for e in examples],
        "legacy_examples_count": len(examples),
        "rag_context": rag_context or [],
        "rag_chunks_count": len(rag_context or []),
    }


def build_evaluation_export(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Payload JSON structuré pour l'évaluation (deepEval).

    Ordre : story → images → agent2_input → agent 1.5 → agent 2 → reste.
    """
    return {
        "story_id": result.get("story_id"),
        "story": result.get("story"),
        "images": result.get("images") or [],
        "agent2_input": result.get("agent2_input"),
        "agent15_business_model": result.get("agent15_business_model"),
        "agent2_tests": result.get("agent2_tests"),
        "agent2_golden_rule_warnings": result.get("agent2_golden_rule_warnings"),
        "agent2_message": result.get("agent2_message"),
        "agent1_analysis": result.get("agent1_analysis"),
        "agent3_validation": result.get("agent3_validation"),
        "agent5_report": result.get("agent5_report"),
        "legacy_examples": result.get("legacy_examples"),
        "rag_context": result.get("rag_context"),
        "status": result.get("status"),
        "tests_count": result.get("tests_count"),
        "coverage_rate": result.get("coverage_rate"),
        "validation_status": result.get("validation_status"),
        "correction_iterations": result.get("correction_iterations"),
        "report_status": result.get("report_status"),
        "duration_ms": result.get("duration_ms"),
        "errors": result.get("errors"),
        "token_usage": result.get("token_usage"),
    }
