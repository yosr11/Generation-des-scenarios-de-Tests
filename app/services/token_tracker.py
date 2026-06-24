"""
Suivi de la consommation de tokens des appels LLM, par agent et par pipeline.

Utilisation :
    with track_pipeline() as usage:
        with track_agent("agent1"):
            call_groq(...)        # enregistré automatiquement
        with track_agent("agent2"):
            ...
    print(usage)  # {"agent1": {...}, "agent2": {...}, "_totals": {...}}

Les appels LLM (llm_client + manual_test_generator) appellent record_usage()
après chaque réponse. Si aucun pipeline n'est actif, l'appel est ignoré.
"""

from __future__ import annotations

import contextlib
from contextvars import ContextVar
from typing import Any, Dict, Iterator, Optional

# Accumulateur courant : {agent_name: {model: {...}, _totals: {...}}, _totals: {...}}
_current_usage: ContextVar[Optional[Dict[str, Any]]] = ContextVar(
    "_current_usage", default=None
)
_current_agent: ContextVar[Optional[str]] = ContextVar(
    "_current_agent", default=None
)


def _empty_bucket() -> Dict[str, Any]:
    return {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "calls": 0,
    }


def _add(bucket: Dict[str, Any], prompt: int, completion: int, total: int) -> None:
    bucket["prompt_tokens"] += prompt
    bucket["completion_tokens"] += completion
    bucket["total_tokens"] += total
    bucket["calls"] += 1


@contextlib.contextmanager
def track_pipeline() -> Iterator[Dict[str, Any]]:
    """Crée un accumulateur frais pour la durée du with-block."""
    usage: Dict[str, Any] = {"_totals": _empty_bucket()}
    token = _current_usage.set(usage)
    try:
        yield usage
    finally:
        _current_usage.reset(token)


@contextlib.contextmanager
def track_agent(agent_name: str) -> Iterator[None]:
    """Définit le nom de l'agent actif pour le with-block."""
    token = _current_agent.set(agent_name)
    try:
        yield
    finally:
        _current_agent.reset(token)


def record_usage(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: Optional[int] = None,
) -> None:
    """Enregistre une réponse LLM dans le pipeline actif (sinon no-op)."""
    usage = _current_usage.get()
    if usage is None:
        return

    if total_tokens is None:
        total_tokens = prompt_tokens + completion_tokens

    agent = _current_agent.get() or "unknown"

    agent_bucket = usage.setdefault(agent, {"_totals": _empty_bucket(), "by_model": {}})
    model_bucket = agent_bucket["by_model"].setdefault(model, _empty_bucket())

    _add(agent_bucket["_totals"], prompt_tokens, completion_tokens, total_tokens)
    _add(model_bucket, prompt_tokens, completion_tokens, total_tokens)
    _add(usage["_totals"], prompt_tokens, completion_tokens, total_tokens)


def record_from_response(response: Any, model: str) -> None:
    """Extrait l'usage d'une réponse OpenAI/Groq et l'enregistre."""
    usage_obj = getattr(response, "usage", None)
    if usage_obj is None:
        return
    prompt = getattr(usage_obj, "prompt_tokens", 0) or 0
    completion = getattr(usage_obj, "completion_tokens", 0) or 0
    total = getattr(usage_obj, "total_tokens", None)
    record_usage(model, prompt, completion, total)


def current_usage() -> Optional[Dict[str, Any]]:
    """Retourne le dict d'usage courant (lecture seule)."""
    return _current_usage.get()
