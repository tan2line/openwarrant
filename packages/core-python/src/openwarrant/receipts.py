"""Execution receipts and reconciliation for OpenWarrant (v0.2).

A warrant answers *may this agent act?* The audit chain records that
answer. An **execution receipt** answers the next question: *what did the
agent actually look at when it acted, what could it not read, and what did
it leave out?*

Receipts matter most for read-only executions such as chart summarization.
A summary that omits a critical value never wrote to the record, but the
human who trusted it still acted. The receipt makes the omission visible.

**Reconciliation** is the disagreement protocol: when two executions under
warrant produce different outputs for the same target over overlapping
coverage, that is a flag, not a coin toss. The default policy escalates.
"""

from __future__ import annotations

import enum
import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Optional

from openwarrant.models import Decision, Warrant


# ---------------------------------------------------------------------------
# Execution receipt
# ---------------------------------------------------------------------------


@dataclass
class InputGap:
    """A source the execution did not fully use, and why."""

    source: str
    reason: str  # e.g. "unparseable", "outside_coverage_window", "not_authorized", "truncated"


@dataclass
class CoverageWindow:
    """The time window of source data the execution considered."""

    start: str  # ISO 8601
    end: str  # ISO 8601


@dataclass
class ExecutionReceipt:
    """Content-level provenance for a single warranted execution.

    Distinct from the audit record, which captures the *authorization*
    decision. The receipt captures what the execution consumed and produced.
    """

    agent_id: str
    warrant_id: str
    action: str
    target: str  # what the execution operated on (patient_id, account_id, ...)
    inputs_read: list[str] = field(default_factory=list)
    inputs_unavailable: list[InputGap] = field(default_factory=list)
    inputs_omitted: list[InputGap] = field(default_factory=list)
    coverage_window: Optional[CoverageWindow] = None
    source_refs: list[str] = field(default_factory=list)  # pointers back to the record
    output_hash: str = ""  # SHA-256 of the produced artifact
    accountable_owner: str = ""  # named human, populated from the warrant
    produced_at: Optional[str] = None
    correlation_id: Optional[str] = None
    receipt_hash: str = field(default="", init=False)

    def __post_init__(self) -> None:
        if self.produced_at is None:
            self.produced_at = datetime.utcnow().isoformat() + "Z"
        self.receipt_hash = self.compute_hash()

    @property
    def has_gaps(self) -> bool:
        """True if anything the warrant covered was unavailable or omitted."""
        return bool(self.inputs_unavailable or self.inputs_omitted)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d

    def _canonical(self) -> str:
        d = self.to_dict()
        d.pop("receipt_hash", None)
        return json.dumps(d, sort_keys=True)

    def compute_hash(self) -> str:
        digest = hashlib.sha256(self._canonical().encode("utf-8")).hexdigest()
        return f"sha256:{digest}"

    @staticmethod
    def hash_output(output: str | bytes) -> str:
        """Convenience: hash a produced artifact for the output_hash field."""
        raw = output.encode("utf-8") if isinstance(output, str) else output
        return "sha256:" + hashlib.sha256(raw).hexdigest()

    @classmethod
    def for_warrant(
        cls,
        warrant: Warrant,
        agent_id: str,
        action: str,
        target: str,
        **kwargs: Any,
    ) -> "ExecutionReceipt":
        """Build a receipt with the accountable owner taken from the warrant."""
        owner = warrant.accountable_owner or warrant.escalation_target
        return cls(
            agent_id=agent_id,
            warrant_id=warrant.id,
            action=action,
            target=target,
            accountable_owner=owner,
            **kwargs,
        )


# ---------------------------------------------------------------------------
# Reconciliation (disagreement protocol)
# ---------------------------------------------------------------------------


class ReconciliationStatus(enum.Enum):
    CONSISTENT = "CONSISTENT"  # same target, overlapping coverage, same output
    DIVERGENT = "DIVERGENT"  # same target, overlapping coverage, different output
    INCOMPARABLE = "INCOMPARABLE"  # different targets/actions or no overlap
    INSUFFICIENT = "INSUFFICIENT"  # fewer than two receipts


@dataclass
class Divergence:
    """One concrete way two receipts differ."""

    kind: str  # "output" | "inputs_read" | "coverage" | "gaps"
    detail: str
    receipts: list[str]  # receipt hashes involved


@dataclass
class ReconciliationResult:
    status: ReconciliationStatus
    decision: Decision
    target: str
    action: str
    receipt_hashes: list[str]
    divergences: list[Divergence] = field(default_factory=list)
    accountable_owners: list[str] = field(default_factory=list)
    detail: str = ""
    reconciled_at: Optional[str] = None
    audit_hash: str = ""
    previous_hash: str = ""

    def __post_init__(self) -> None:
        if self.reconciled_at is None:
            self.reconciled_at = datetime.utcnow().isoformat() + "Z"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        d["decision"] = self.decision.value
        return d


def _windows_overlap(a: Optional[CoverageWindow], b: Optional[CoverageWindow]) -> bool:
    if a is None or b is None:
        # Unspecified coverage is treated as comparable; the receipt is
        # expected to declare a window, and absence is itself surfaced.
        return True
    return a.start <= b.end and b.start <= a.end


def reconcile(
    receipts: list[ExecutionReceipt],
    policy: str = "escalate",
) -> ReconciliationResult:
    """Compare two or more execution receipts on the same target.

    policy:
        "escalate" (default) — DIVERGENT → Decision.ESCALATE
        "deny"               — DIVERGENT → Decision.DENIED
        "log"                — DIVERGENT → Decision.AUTHORIZED (recorded only)

    Two receipts are DIVERGENT when they cover the same target and action
    over overlapping coverage windows and produce different outputs, or read
    different input sets. Gaps in either receipt are reported as divergences
    of kind "gaps" so the reviewer sees what was skipped.
    """
    hashes = [r.receipt_hash for r in receipts]
    owners = sorted({r.accountable_owner for r in receipts if r.accountable_owner})

    if len(receipts) < 2:
        return ReconciliationResult(
            status=ReconciliationStatus.INSUFFICIENT,
            decision=Decision.AUTHORIZED,
            target=receipts[0].target if receipts else "",
            action=receipts[0].action if receipts else "",
            receipt_hashes=hashes,
            accountable_owners=owners,
            detail="Reconciliation requires at least two receipts.",
        )

    first = receipts[0]
    same_target = all(r.target == first.target for r in receipts)
    same_action = all(r.action == first.action for r in receipts)
    overlapping = all(
        _windows_overlap(first.coverage_window, r.coverage_window) for r in receipts[1:]
    )

    if not (same_target and same_action and overlapping):
        return ReconciliationResult(
            status=ReconciliationStatus.INCOMPARABLE,
            decision=Decision.AUTHORIZED,
            target=first.target,
            action=first.action,
            receipt_hashes=hashes,
            accountable_owners=owners,
            detail="Receipts differ in target, action, or coverage; nothing to reconcile.",
        )

    divergences: list[Divergence] = []

    output_hashes = {r.output_hash for r in receipts}
    if len(output_hashes) > 1:
        divergences.append(
            Divergence(
                kind="output",
                detail=f"{len(output_hashes)} distinct outputs for target {first.target}",
                receipts=hashes,
            )
        )

    input_sets = {frozenset(r.inputs_read) for r in receipts}
    if len(input_sets) > 1:
        union = set().union(*input_sets)
        inter = set.intersection(*(set(s) for s in input_sets))
        divergences.append(
            Divergence(
                kind="inputs_read",
                detail=f"read sets differ; only {len(inter)} of {len(union)} sources common to all",
                receipts=hashes,
            )
        )

    for r in receipts:
        if r.has_gaps:
            skipped = [g.source for g in r.inputs_unavailable + r.inputs_omitted]
            divergences.append(
                Divergence(
                    kind="gaps",
                    detail=f"receipt {r.receipt_hash[:19]} skipped: {', '.join(skipped)}",
                    receipts=[r.receipt_hash],
                )
            )

    material = [d for d in divergences if d.kind in ("output", "inputs_read")]
    if material:
        status = ReconciliationStatus.DIVERGENT
        decision = {
            "escalate": Decision.ESCALATE,
            "deny": Decision.DENIED,
            "log": Decision.AUTHORIZED,
        }.get(policy, Decision.ESCALATE)
        detail = (
            f"{len(receipts)} executions disagree on {first.target}; "
            f"policy={policy} → {decision.value}"
        )
    else:
        status = ReconciliationStatus.CONSISTENT
        decision = Decision.AUTHORIZED
        detail = f"{len(receipts)} executions agree on {first.target}"
        if divergences:
            detail += " (gaps reported)"

    return ReconciliationResult(
        status=status,
        decision=decision,
        target=first.target,
        action=first.action,
        receipt_hashes=hashes,
        divergences=divergences,
        accountable_owners=owners,
        detail=detail,
    )
