"""Helpers for legacy/experimental modules.

This module centralizes the warning path for older integrations that are still
kept for backward compatibility while the core product moves toward a more
structured architecture.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def warn_legacy_module(module_name: str, reason: str | None = None) -> None:
    """Log a clear warning when a legacy module is used."""
    detail = f"Legacy module '{module_name}' is being used"
    if reason:
        detail = f"{detail}: {reason}"
    logger.warning(detail)
