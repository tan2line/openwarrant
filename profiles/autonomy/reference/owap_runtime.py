#!/usr/bin/env python3
"""Minimal dependency-free OWAP v0.1 reference evaluator.

Demonstrates runtime interpretation of a machine-readable autonomy warrant and
returns OpenWarrant decisions: AUTHORIZED, DENIED, ESCALATE, NO_WARRANT, EXPIRED.

Production implementations MUST additionally verify issuer trust,
cryptographic signatures, revocation freshness, authenticated system identity,
and configuration attestation.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class DecisionRecord:
    decision: str
    warrant_id: Optional[str]
    reason: str
    checks: List[Dict[str, Any]]
    timestamp: str
    evidence_hash: str = ""

    def finalize(self) -> "DecisionRecord":
        payload = asdict(self)
        payload["evidence_hash"] = ""
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        self.evidence_hash = "sha256:" + hashlib.sha256(canonical).hexdigest()
        return self


def _parse_time(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _condition_met(actual: Any, operator: str, expected: Any) -> bool:
    if operator == "present":
        return actual is not None
    if operator == "eq":
        return actual == expected
    if operator == "neq":
        return actual != expected
    if operator == "lt":
        return actual is not None and actual < expected
    if operator == "lte":
        return actual is not None and actual <= expected
    if operator == "gt":
        return actual is not None and actual > expected
    if operator == "gte":
        return actual is not None and actual >= expected
    if operator == "in":
        return actual in expected
    if operator == "not_in":
        return actual not in expected
    raise ValueError(f"Unsupported operator: {operator}")


def evaluate(warrant: Dict[str, Any], request: Dict[str, Any]) -> DecisionRecord:
    checks: List[Dict[str, Any]] = []
    now = _parse_time(request["timestamp"])
    wid = warrant.get("warrant_id")

    def record(name: str, met: bool, detail: str) -> None:
        checks.append({"check": name, "met": met, "detail": detail})

    def finish(decision: str, reason: str) -> DecisionRecord:
        return DecisionRecord(decision, wid, reason, checks, request["timestamp"]).finalize()

    if warrant.get("profile") != "autonomy":
        return finish("NO_WARRANT", "Warrant is not an autonomy profile.")

    if warrant.get("revocation", {}).get("status") != "active":
        return finish("DENIED", "Warrant is suspended or revoked.")

    if request.get("system_id") != warrant.get("subject", {}).get("system_id"):
        return finish("NO_WARRANT", "Warrant does not apply to this system identity.")
    record("system_identity", True, "System identity matches warrant subject.")

    temporal = warrant["operating_envelope"]["temporal"]
    if now < _parse_time(temporal["valid_from"]) or now > _parse_time(temporal["valid_until"]):
        return finish("EXPIRED", "Request falls outside the warrant validity window.")
    record("temporal_validity", True, "Request is inside the warrant validity window.")

    action = request.get("action")
    authority = warrant["authority"]
    if action in authority.get("prohibited_actions", []):
        return finish("DENIED", f"Action '{action}' is explicitly prohibited.")
    if action not in authority.get("permitted_actions", []):
        return finish("DENIED", f"Action '{action}' is outside the permitted action set.")
    record("action_scope", True, f"Action '{action}' is permitted.")

    context = request.get("context", {})
    geography = warrant["operating_envelope"]["geography"]
    zone = context.get("zone")
    if zone in geography.get("denied_zones", []):
        return finish("DENIED", f"Zone '{zone}' is explicitly denied.")
    if zone not in geography.get("allowed_zones", []):
        return finish("DENIED", f"Zone '{zone}' is outside the authorized geography.")
    record("geography", True, f"Zone '{zone}' is authorized.")

    altitude = context.get("altitude_m")
    limits = warrant["operating_envelope"].get("altitude_m")
    if limits and altitude is not None:
        if altitude < limits.get("min", float("-inf")) or altitude > limits.get("max", float("inf")):
            return finish("DENIED", "Requested altitude is outside the operating envelope.")
        record("altitude", True, "Altitude is inside the operating envelope.")

    speed = context.get("speed_mps")
    speed_limits = warrant["operating_envelope"].get("speed_mps")
    if speed_limits and speed is not None:
        if speed > speed_limits.get("max", float("inf")):
            return finish("DENIED", "Requested speed is outside the operating envelope.")
        record("speed", True, "Speed is inside the operating envelope.")

    expected_version = warrant["subject"].get("software_version")
    actual_version = context.get("software_version")
    if actual_version != expected_version:
        return finish("DENIED", "Software version does not match the authorized configuration.")
    record("software_version", True, "Software version matches the warrant.")

    for condition in warrant.get("preconditions", []):
        field = condition["field"]
        actual = context.get(field)
        met = _condition_met(actual, condition["operator"], condition.get("value"))
        record(condition["id"], met, f"{field}={actual!r}")
        if not met:
            return finish(condition["on_failure"], f"Precondition '{condition['id']}' failed.")

    return finish("AUTHORIZED", "All applicable warrant checks passed.")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate an OWAP v0.1 request")
    parser.add_argument("warrant", help="Path to OWAP warrant JSON")
    parser.add_argument("request", help="Path to request JSON")
    args = parser.parse_args()

    with open(args.warrant, "r", encoding="utf-8") as f:
        warrant = json.load(f)
    with open(args.request, "r", encoding="utf-8") as f:
        request = json.load(f)

    print(json.dumps(asdict(evaluate(warrant, request)), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
