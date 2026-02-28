"""WarrantEngine — the core authorization engine for OpenWarrant."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

from openwarrant.action_matcher import action_matches
from openwarrant.audit import AuditChain
from openwarrant.conditions import evaluate_constraint
from openwarrant.loader import load_warrant_dir, load_warrant_file
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


class WarrantEngine:
    """Pattern-matching governance engine.

    Loads warrants from a directory or list, and checks incoming requests
    against them. Returns one of five decision types:
    AUTHORIZED, DENIED, ESCALATE, NO_WARRANT, EXPIRED.

    Every decision is appended to an internal audit chain.
    """

    def __init__(
        self,
        warrant_store: str | Path | None = None,
        warrants: list[Warrant] | None = None,
        on_authorized: Optional[Callable[[WarrantResponse], None]] = None,
        on_denied: Optional[Callable[[WarrantResponse], None]] = None,
        on_escalate: Optional[Callable[[WarrantResponse], None]] = None,
        webhook_url: Optional[str] = None,
        on_decision: Optional[Callable[[WarrantResponse], None]] = None,
    ) -> None:
        self._warrants: list[Warrant] = []
        self._audit = AuditChain()
        self._on_authorized = on_authorized
        self._on_denied = on_denied
        self._on_escalate = on_escalate
        self._webhook_url = webhook_url
        self._on_decision = on_decision
        self._execution_count: int = 0

        if warrants:
            self._warrants = list(warrants)
        elif warrant_store:
            path = Path(warrant_store)
            if path.is_dir():
                self._warrants = load_warrant_dir(path)
            elif path.is_file():
                self._warrants = [load_warrant_file(path)]

    @property
    def warrants(self) -> list[Warrant]:
        """Return loaded warrants."""
        return list(self._warrants)

    @property
    def audit(self) -> AuditChain:
        """Return the audit chain."""
        return self._audit

    def _evaluate_conditions(
        self, warrant: Warrant, request: WarrantRequest
    ) -> list[ConditionResult]:
        """Evaluate warrant conditions against the request context.

        Uses structured ``context_constraints`` if populated, otherwise
        falls back to legacy dict-based ``conditions``.
        """
        # Structured constraint path (new)
        if warrant.context_constraints:
            results: list[ConditionResult] = []
            for c in warrant.context_constraints:
                met = evaluate_constraint(c, request.context)
                results.append(
                    ConditionResult(
                        condition=c.field,
                        met=met,
                        detail=f"{c.operator} {c.value}",
                    )
                )
            return results

        # Legacy dict-based condition path (unchanged)
        results = []
        ctx = request.context

        for cond in warrant.conditions:
            for key, value in cond.items():
                if key == "escalation_threshold" or key == "single_trade_limit":
                    amount = ctx.get("amount", ctx.get("trade_amount", 0))
                    threshold = int(value) if isinstance(value, (int, float, str)) else 0
                    if isinstance(amount, (int, float)) and amount > threshold:
                        results.append(
                            ConditionResult(
                                condition=key,
                                met=False,
                                detail=f"Amount {amount} exceeds threshold {threshold} — escalation required",
                            )
                        )
                    else:
                        results.append(
                            ConditionResult(
                                condition=key,
                                met=True,
                                detail=f"Within threshold ({threshold})",
                            )
                        )
                elif key == "payout_within_authority":
                    if isinstance(value, dict):
                        limit = value.get(request.role, 0)
                        amount = ctx.get("amount", ctx.get("payout_amount", 0))
                        if isinstance(amount, (int, float)) and isinstance(
                            limit, (int, float)
                        ):
                            if amount > limit:
                                results.append(
                                    ConditionResult(
                                        condition=key,
                                        met=False,
                                        detail=f"Amount {amount} exceeds {request.role} limit of {limit}",
                                    )
                                )
                            else:
                                results.append(
                                    ConditionResult(
                                        condition=key,
                                        met=True,
                                        detail=f"Within {request.role} limit ({limit})",
                                    )
                                )
                        else:
                            results.append(
                                ConditionResult(
                                    condition=key, met=True, detail="No amount to check"
                                )
                            )
                    else:
                        results.append(
                            ConditionResult(condition=key, met=True, detail="Checked")
                        )
                elif value == "required" or value is True:
                    ctx_val = ctx.get(key, False)
                    met = bool(ctx_val)
                    results.append(
                        ConditionResult(
                            condition=key,
                            met=met,
                            detail=f"{'Present' if met else 'Missing or false'} in context",
                        )
                    )
                elif isinstance(value, list):
                    ctx_val = ctx.get(key, "")
                    met = ctx_val in value
                    results.append(
                        ConditionResult(
                            condition=key,
                            met=met,
                            detail=f"Value '{ctx_val}' {'in' if met else 'not in'} allowed: {value}",
                        )
                    )
                elif isinstance(value, str):
                    ctx_val = ctx.get(key, "")
                    met = str(ctx_val) == str(value)
                    results.append(
                        ConditionResult(
                            condition=key,
                            met=met,
                            detail=f"Expected '{value}', got '{ctx_val}'",
                        )
                    )
                else:
                    results.append(
                        ConditionResult(
                            condition=key, met=True, detail="Condition accepted"
                        )
                    )

        return results

    def _has_escalation_trigger(
        self, conditions: list[ConditionResult], warrant: Warrant
    ) -> bool:
        """Check if any condition triggered an escalation."""
        for c in conditions:
            if not c.met and "escalation" in c.detail.lower():
                return True
            if not c.met and "threshold" in c.detail.lower():
                return True
            if not c.met and "exceeds" in c.detail.lower():
                return True
        return False

    def check(self, request: WarrantRequest) -> WarrantResponse:
        """Check a warrant request and return a decision.

        Iterates ALL warrants, checking each fully:
        status → temporal → action (with wildcards) → role/data_type →
        structured constraints → capability allowlist.

        First warrant to pass all checks → AUTHORIZED.
        If none pass → DENIED with collected deny reasons.
        """
        now = request.timestamp or datetime.utcnow()
        now_naive = now.replace(tzinfo=None) if now.tzinfo else now
        deny_reasons: list[str] = []
        last_expired_warrant: Warrant | None = None
        last_failed_warrant: Warrant | None = None
        last_failed_conditions: list[ConditionResult] = []

        for w in self._warrants:
            # --- Warrant status check ---
            if w.status is not None:
                if w.status == WarrantStatus.REVOKED:
                    deny_reasons.append(f"warrant:{w.id}:revoked")
                    continue
                if w.status == WarrantStatus.SUSPENDED:
                    deny_reasons.append(f"warrant:{w.id}:suspended")
                    continue

            # --- Action matching (with wildcards) ---
            action_match = any(
                action_matches(pattern, request.action)
                for pattern in w.actions
            )
            if not action_match:
                continue

            # --- Role matching (optional — skip when empty) ---
            role_match = (
                (not request.role)
                or (request.role in w.roles)
                or (not w.roles)
            )
            if not role_match:
                continue

            # --- Data type matching (optional — skip when empty) ---
            data_match = (
                (not request.data_type)
                or (request.data_type in w.data_types)
                or (not w.data_types)
            )
            if not data_match:
                continue

            # --- Temporal validity ---
            valid_from = w.valid_from.replace(tzinfo=None) if w.valid_from.tzinfo else w.valid_from
            valid_until = w.valid_until.replace(tzinfo=None) if w.valid_until.tzinfo else w.valid_until

            if now_naive > valid_until or now_naive < valid_from:
                last_expired_warrant = w
                deny_reasons.append(f"warrant:{w.id}:expired")
                continue

            # --- Structured constraint evaluation ---
            conditions = self._evaluate_conditions(w, request)
            failed = [c for c in conditions if not c.met]

            if failed:
                # Check for escalation triggers
                if self._has_escalation_trigger(conditions, w):
                    authority = WarrantAuthority(
                        issuer=w.issuer,
                        type=w.id,
                        issued=w.valid_from.isoformat(),
                        expires=w.valid_until.isoformat(),
                        scope=w.actions,
                    )
                    response = WarrantResponse(
                        decision=Decision.ESCALATE,
                        warrant_id=w.id,
                        authority=authority,
                        conditions_evaluated=conditions,
                        deny_reasons=deny_reasons,
                    )
                    self._record_and_notify(response, request)
                    return response
                last_failed_warrant = w
                last_failed_conditions = conditions
                deny_reasons.append(f"warrant:{w.id}:conditions_failed")
                continue

            # --- Capability allowlist check ---
            if w.allowed_capabilities:
                cap_ctx = request.context.get("__capability")
                if cap_ctx and isinstance(cap_ctx, dict):
                    cap_allowed = any(
                        cap.get("name") == cap_ctx.get("name")
                        and cap.get("version") == cap_ctx.get("version")
                        for cap in w.allowed_capabilities
                    )
                    if not cap_allowed:
                        deny_reasons.append(f"warrant:{w.id}:capability_not_allowed")
                        continue

            # --- ALL checks passed → AUTHORIZED ---
            authority = WarrantAuthority(
                issuer=w.issuer,
                type=w.id,
                issued=w.valid_from.isoformat(),
                expires=w.valid_until.isoformat(),
                scope=w.actions,
            )

            self._execution_count += 1
            trust_elevation = None
            if self._execution_count >= 10:
                trust_elevation = TrustElevation(eligible=True, new_level=1)
            if self._execution_count >= 50:
                trust_elevation = TrustElevation(eligible=True, new_level=2)

            response = WarrantResponse(
                decision=Decision.AUTHORIZED,
                warrant_id=w.id,
                authority=authority,
                conditions_evaluated=conditions,
                trust_elevation=trust_elevation,
            )
            self._record_and_notify(response, request)
            return response

        # --- No warrant matched ---

        # If the only reason we failed was expiry, return EXPIRED
        if last_expired_warrant and all("expired" in r for r in deny_reasons):
            w = last_expired_warrant
            response = WarrantResponse(
                decision=Decision.EXPIRED,
                warrant_id=w.id,
                authority=WarrantAuthority(
                    issuer=w.issuer,
                    type=w.id,
                    issued=w.valid_from.isoformat(),
                    expires=w.valid_until.isoformat(),
                    scope=w.actions,
                ),
                deny_reasons=deny_reasons,
            )
            self._record_and_notify(response, request)
            return response

        # Default: NO_WARRANT / DENIED
        decision = Decision.DENIED if deny_reasons else Decision.NO_WARRANT

        # Include the last matched-but-failed warrant info for richer deny context
        warrant_id = None
        authority = None
        conditions_evaluated: list[ConditionResult] = []
        if last_failed_warrant:
            lw = last_failed_warrant
            warrant_id = lw.id
            authority = WarrantAuthority(
                issuer=lw.issuer,
                type=lw.id,
                issued=lw.valid_from.isoformat(),
                expires=lw.valid_until.isoformat(),
                scope=lw.actions,
            )
            conditions_evaluated = last_failed_conditions

        response = WarrantResponse(
            decision=decision,
            warrant_id=warrant_id,
            authority=authority,
            conditions_evaluated=conditions_evaluated,
            deny_reasons=deny_reasons,
        )
        self._record_and_notify(response, request)
        return response

    def _record_and_notify(
        self, response: WarrantResponse, request: WarrantRequest
    ) -> None:
        """Record the decision in the audit chain and fire callbacks."""
        record = self._audit.record(
            response=response,
            agent_id=request.agent_id,
            action=request.action,
            correlation_id=request.correlation_id,
        )
        response.audit_hash = record.record_hash
        response.previous_hash = record.previous_hash

        # Fire event hooks
        if self._on_decision:
            self._on_decision(response)
        if response.decision == Decision.AUTHORIZED and self._on_authorized:
            self._on_authorized(response)
        elif response.decision == Decision.DENIED and self._on_denied:
            self._on_denied(response)
        elif response.decision == Decision.ESCALATE and self._on_escalate:
            self._on_escalate(response)
