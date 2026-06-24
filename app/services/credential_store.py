"""Stockage en mémoire des credentials Jira des testeurs (liés au session_id JWT)."""

from dataclasses import dataclass
from threading import Lock
from typing import Dict, Optional


@dataclass
class JiraCredentials:
    username: str
    password: str


_store: Dict[str, JiraCredentials] = {}
_lock = Lock()


def store_credentials(session_id: str, username: str, password: str) -> None:
    with _lock:
        _store[session_id] = JiraCredentials(username=username, password=password)


def get_credentials(session_id: str) -> Optional[JiraCredentials]:
    with _lock:
        return _store.get(session_id)


def remove_credentials(session_id: str) -> None:
    with _lock:
        _store.pop(session_id, None)
