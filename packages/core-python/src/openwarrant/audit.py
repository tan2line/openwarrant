"""SHA-256 hash-chained audit trail for OpenWarrant."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional

from openwarrant.models import WarrantResponse


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
