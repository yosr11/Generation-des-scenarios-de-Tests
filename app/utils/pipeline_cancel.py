"""Annulation coopérative des pipelines (thread-safe)."""

from __future__ import annotations

import threading

_lock = threading.Lock()
_cancelled: set[str] = set()


class PipelineCancelled(Exception):
    """Levée quand l'utilisateur annule un pipeline en cours."""


def _norm(story_id: str) -> str:
    return (story_id or "").strip().upper()


def mark_pipeline_cancelled(story_id: str) -> None:
    with _lock:
        _cancelled.add(_norm(story_id))


def clear_pipeline_cancelled(story_id: str) -> None:
    with _lock:
        _cancelled.discard(_norm(story_id))


def is_pipeline_cancelled(story_id: str) -> bool:
    with _lock:
        return _norm(story_id) in _cancelled


def check_pipeline_cancelled(story_id: str) -> None:
    if is_pipeline_cancelled(story_id):
        raise PipelineCancelled(f"Pipeline {story_id} annulé par l'utilisateur")
