# Configure le logging structuré avec correlation ID.
# Utile pour le debug + traçabilité pipeline multi-agents.

import logging
import uuid
import contextvars

# Correlation ID pour tracer un pipeline complet (Agent 1 → 2 → 3 → 4)
correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default=""
)


def new_correlation_id() -> str:
    """Génère et enregistre un nouveau correlation ID pour le pipeline courant."""
    cid = uuid.uuid4().hex[:12]
    correlation_id_var.set(cid)
    return cid


def get_correlation_id() -> str:
    """Retourne le correlation ID courant (ou vide)."""
    return correlation_id_var.get("")


class CorrelationFilter(logging.Filter):
    """Injecte le correlation_id dans chaque log record."""

    def filter(self, record):
        record.correlation_id = get_correlation_id() or "-"
        return True


# Configuration du logging structuré
_formatter = logging.Formatter(
    fmt="%(asctime)s [%(levelname)s] [%(correlation_id)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

_handler = logging.StreamHandler()
_handler.setFormatter(_formatter)
_handler.addFilter(CorrelationFilter())

logging.root.handlers.clear()
logging.root.addHandler(_handler)
logging.root.setLevel(logging.INFO)

logger = logging.getLogger("PFE-AGENT-TEST")
