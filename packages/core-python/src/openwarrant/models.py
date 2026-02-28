"""Core data models for OpenWarrant."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


class Decision(enum.Enum):
    """Warrant check decision types."""

    AUTHORIZED = "AUTHORIZED"
    DENIED = "DENIED"
    ESCALATE = "ESCALATE"
    NO_WARRANT = "NO_WARRANT"
    EXPIRED = "EXPIRED"


class WarrantStatus(enum.Enum):
    """Warrant lifecycle status."""

    ACTIVE = "active"
    REVOKED = "revoked"
    SUSPENDED = "suspended"


@dataclass
class Constraint:
    """A structured constraint for context evaluation."""

    field: str
    operator: str  # eq|ne|in|not_in|gt|gte|lt|lte|contains|required
    value: Any


@dataclass
class Warrant:
    """A warrant definition loaded from YAML."""

    id: str
    issuer: str
    signature: str
    roles: list[str]
    actions: list[str]
    data_types: list[str]
    conditions: list[dict[str, Any]]
    valid_from: datetime
    valid_until: datetime
    trust_level_required: int = 0
    audit_required: bool = True
    escalation_target: str = ""
    notes: str = ""
    context_constraints: list[Constraint] = field(default_factory=list)
    allowed_capabilities: list[dict[str, str]] = field(default_factory=list)
    status: Optional[WarrantStatus] = None


@dataclass
class WarrantRequest:
    """A request to check authorization."""

    agent_id: str
    action: str
    role: str
    data_type: str
    context: dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[datetime] = None
    correlation_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class ConditionResult:
    """Result of evaluating a single condition."""

    condition: str
    met: bool
    detail: str = ""


@dataclass
class WarrantAuthority:
    """Authority information from the matching warrant."""

    issuer: str
    type: str
    issued: str
    expires: str
    scope: list[str]


@dataclass
class TrustElevation:
    """Trust elevation information."""

    eligible: bool
    new_level: Optional[int] = None


@dataclass
class WarrantResponse:
    """Response from a warrant check."""

    decision: Decision
    warrant_id: Optional[str] = None
    authority: Optional[WarrantAuthority] = None
    conditions_evaluated: list[ConditionResult] = field(default_factory=list)
    audit_hash: str = ""
    previous_hash: str = ""
    trust_elevation: Optional[TrustElevation] = None
    deny_reasons: list[str] = field(default_factory=list)
