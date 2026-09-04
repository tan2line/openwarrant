"""SHA-256 hash-chained audit trail for OpenWarrant."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable, Optional

from openwarrant.models import WarrantResponse

if TYPE_CHECKING:  # avoid import cycle at runtime
    from openwarrant.receipts import ExecutionReceipt, ReconciliationResult


@dataclass
class AuditRecord:
    """A single tamper-evident audit record."""

    record_id: str
    timestamp: str
    agent_id: str
    warrant_id: Optional[str]
    action: str
    decision: str
    conditions_evaluated: list[dict[str, Any]]
    correlation_id: Optional[str]
    previous_hash: str
    record_hash: str
    # v0.2 — record_type distinguishes authorization decisions from
    # execution receipts and reconciliations. All share one hash chain.
    record_type: str = "decision"
    payload: Optional[dict[str, Any]] = None


class AuditChain:
    """SHA-256 hash-chained audit trail.

    Every warrant decision is appended to the chain with a hash
    linking to the previous entry, providing tamper evidence.
    """

    GENESIS_HASH = "sha256:" + "0" * 64

    def __init__(
        self,
        on_record: Optional[Callable[[AuditRecord], None]] = None,
    ) -> None:
        self._chain: list[AuditRecord] = []
        self._previous_hash: str = self.GENESIS_HASH
        self._on_record = on_record

    @property
    def chain(self) -> list[AuditRecord]:
        """Return a copy of the audit chain."""
        return list(self._chain)

    @property
    def last_hash(self) -> str:
        """Return the hash of the most recent record."""
        return self._previous_hash

    def _compute_hash(self, content: str, previous_hash: str) -> str:
        """Compute SHA-256 hash: H(content + previous_hash)."""
        raw = content + previous_hash
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return f"sha256:{digest}"

    def record(
        self,
        response: WarrantResponse,
        agent_id: str,
        action: str,
        correlation_id: Optional[str] = None,
    ) -> AuditRecord:
        """Append a decision to the audit chain."""
        conditions = [
            {"condition": c.condition, "met": c.met, "detail": c.detail}
            for c in response.conditions_evaluated
        ]

        content = json.dumps(
            {
                "agent_id": agent_id,
                "warrant_id": response.warrant_id,
                "action": action,
                "decision": response.decision.value,
                "conditions": conditions,
                "correlation_id": correlation_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            },
            sort_keys=True,
        )

        record_hash = self._compute_hash(content, self._previous_hash)

        record = AuditRecord(
            record_id=f"aud-{uuid.uuid4().hex[:12]}",
            timestamp=datetime.utcnow().isoformat() + "Z",
            agent_id=agent_id,
            warrant_id=response.warrant_id,
            action=action,
            decision=response.decision.value,
            conditions_evaluated=conditions,
            correlation_id=correlation_id,
            previous_hash=self._previous_hash,
            record_hash=record_hash,
        )

        self._chain.append(record)
        self._previous_hash = record_hash

        if self._on_record:
            self._on_record(record)

        return record

    def _append(
        self,
        record_type: str,
        agent_id: str,
        warrant_id: Optional[str],
        action: str,
        decision: str,
        conditions: list[dict[str, Any]],
        correlation_id: Optional[str],
        payload: Optional[dict[str, Any]],
    ) -> AuditRecord:
        """Append an arbitrary typed record to the chain."""
        timestamp = datetime.utcnow().isoformat() + "Z"
        content = json.dumps(
            {
                "record_type": record_type,
                "agent_id": agent_id,
                "warrant_id": warrant_id,
                "action": action,
                "decision": decision,
                "conditions": conditions,
                "correlation_id": correlation_id,
                "payload": payload,
                "timestamp": timestamp,
            },
            sort_keys=True,
            default=str,
        )
        record_hash = self._compute_hash(content, self._previous_hash)
        record = AuditRecord(
            record_id=f"aud-{uuid.uuid4().hex[:12]}",
            timestamp=timestamp,
            agent_id=agent_id,
            warrant_id=warrant_id,
            action=action,
            decision=decision,
            conditions_evaluated=conditions,
            correlation_id=correlation_id,
            previous_hash=self._previous_hash,
            record_hash=record_hash,
            record_type=record_type,
            payload=payload,
        )
        self._chain.append(record)
        self._previous_hash = record_hash
        if self._on_record:
            self._on_record(record)
        return record

    def record_execution(self, receipt: "ExecutionReceipt") -> AuditRecord:
        """Append an execution receipt (what was read, skipped, produced)."""
        return self._append(
            record_type="execution_receipt",
            agent_id=receipt.agent_id,
            warrant_id=receipt.warrant_id,
            action=receipt.action,
            decision="EXECUTED",
            conditions=[],
            correlation_id=receipt.correlation_id,
            payload=receipt.to_dict(),
        )

    def record_reconciliation(
        self, result: "ReconciliationResult", agent_id: str = "reconciler"
    ) -> AuditRecord:
        """Append a reconciliation outcome across two or more receipts."""
        record = self._append(
            record_type="reconciliation",
            agent_id=agent_id,
            warrant_id=None,
            action=result.action,
            decision=result.decision.value,
            conditions=[],
            correlation_id=None,
            payload=result.to_dict(),
        )
        result.audit_hash = record.record_hash
        result.previous_hash = record.previous_hash
        return record

    def verify_chain(self) -> bool:
        """Verify the integrity of the entire audit chain.

        Returns True if the chain is intact (no tampered records).
        """
        if not self._chain:
            return True

        expected_prev = self.GENESIS_HASH
        for record in self._chain:
            if record.previous_hash != expected_prev:
                return False
            expected_prev = record.record_hash

        return True

    def __len__(self) -> int:
        return len(self._chain)
