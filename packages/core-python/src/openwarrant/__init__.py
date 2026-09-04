"""OpenWarrant — a runtime-agnostic governance library for AI agents."""

from openwarrant.action_matcher import action_matches
from openwarrant.audit import AuditChain
from openwarrant.conditions import evaluate_constraint
from openwarrant.engine import WarrantEngine
from openwarrant.receipts import (
    CoverageWindow,
    Divergence,
    ExecutionReceipt,
    InputGap,
    ReconciliationResult,
    ReconciliationStatus,
    reconcile,
)
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

__version__ = "0.2.0"

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
    "ExecutionReceipt",
    "InputGap",
    "CoverageWindow",
    "ReconciliationResult",
    "ReconciliationStatus",
    "Divergence",
    "reconcile",
]
