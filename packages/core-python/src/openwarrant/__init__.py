"""OpenWarrant — a runtime-agnostic governance library for AI agents."""

from openwarrant.action_matcher import action_matches
from openwarrant.audit import AuditChain
from openwarrant.conditions import evaluate_constraint
from openwarrant.engine import WarrantEngine
from openwarrant.models import (
    ConditionResult,
    Constraint,
    Decision,
    TrustElevation,
    Warrant,
    WarrantAuthority,
    WarrantRequest,
    WarrantResponse,
    WarrantStatus,
)

__version__ = "0.1.0"

__all__ = [
    "WarrantEngine",
    "WarrantRequest",
    "WarrantResponse",
    "Warrant",
    "Decision",
    "ConditionResult",
    "WarrantAuthority",
    "TrustElevation",
    "AuditChain",
    "Constraint",
    "WarrantStatus",
    "action_matches",
    "evaluate_constraint",
]
