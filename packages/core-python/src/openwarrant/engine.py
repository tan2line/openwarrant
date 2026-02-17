"""WarrantEngine — the core authorization engine for OpenWarrant."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

from openwarrant.audit import AuditChain
from openwarrant.loader import load_warrant_dir, load_warrant_file
from openwarrant.models import (
    ConditionResult,
    Decision,
    TrustElevation,
    Warrant,
    WarrantAuthority,
    WarrantRequest,
    WarrantResponse,
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

    def _find_matching_warrant(
        self, action: str, role: str, data_type: str
    ) -> Warrant | None:
        """Find the first warrant matching the given action, role, and data_type."""
        for w in self._warrants:
            action_match = action in w.actions
            role_match = role in w.roles
            data_match = data_type in w.data_types
            if action_match and role_match and data_match:
                return w
        return None

    def _evaluate_conditions(
        self, warrant: Warrant, request: WarrantRequest
    ) -> list[ConditionResult]:
        """Evaluate warrant conditions against the request context."""
        results = []
        ctx = request.context

        for cond in warrant.conditions:
            for key, value in cond.items():
                if key == "escalation_threshold" or key == "single_trade_limit":
                    # Numeric threshold — check context for amount
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
                    # Role-based payout limits
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
                    # Boolean condition — check if present and truthy in context
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
                    # Value must be one of allowed values
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
                    # Exact match
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

        Decision logic:
        1. Find matching warrant for action + role + data_type
        2. No match → NO_WARRANT
        3. Match but expired → EXPIRED
        4. Match but conditions not met → DENIED (or ESCALATE if threshold hit)
        5. All conditions met → AUTHORIZED
        """
        # Step 1: Find matching warrant
        warrant = self._find_matching_warrant(
            request.action, request.role, request.data_type
        )

        # Step 2: No match → NO_WARRANT
        if warrant is None:
            response = WarrantResponse(decision=Decision.NO_WARRANT)
            self._record_and_notify(response, request)
            return response

        # Step 3: Check expiry
        now = request.timestamp or datetime.utcnow()
        # Make naive for comparison if needed
        valid_from = warrant.valid_from.replace(tzinfo=None) if warrant.valid_from.tzinfo else warrant.valid_from
        valid_until = warrant.valid_until.replace(tzinfo=None) if warrant.valid_until.tzinfo else warrant.valid_until
        now_naive = now.replace(tzinfo=None) if now.tzinfo else now

        if now_naive > valid_until or now_naive < valid_from:
            response = WarrantResponse(
                decision=Decision.EXPIRED,
                warrant_id=warrant.id,
                authority=WarrantAuthority(
                    issuer=warrant.issuer,
                    type=warrant.id,
                    issued=warrant.valid_from.isoformat(),
                    expires=warrant.valid_until.isoformat(),
                    scope=warrant.actions,
                ),
            )
            self._record_and_notify(response, request)
            return response

        # Step 4: Evaluate conditions
        conditions = self._evaluate_conditions(warrant, request)
        failed = [c for c in conditions if not c.met]

        authority = WarrantAuthority(
            issuer=warrant.issuer,
            type=warrant.id,
            issued=warrant.valid_from.isoformat(),
            expires=warrant.valid_until.isoformat(),
            scope=warrant.actions,
        )

        # Step 5: Check for escalation triggers
        if failed and self._has_escalation_trigger(conditions, warrant):
            response = WarrantResponse(
                decision=Decision.ESCALATE,
                warrant_id=warrant.id,
                authority=authority,
                conditions_evaluated=conditions,
            )
            self._record_and_notify(response, request)
            return response

        # Step 6: Any failed conditions → DENIED
        if failed:
            response = WarrantResponse(
                decision=Decision.DENIED,
                warrant_id=warrant.id,
                authority=authority,
                conditions_evaluated=conditions,
            )
            self._record_and_notify(response, request)
            return response

        # Step 7: All conditions met → AUTHORIZED
        self._execution_count += 1
        trust_elevation = None
        if self._execution_count >= 10:
            trust_elevation = TrustElevation(eligible=True, new_level=1)
        if self._execution_count >= 50:
            trust_elevation = TrustElevation(eligible=True, new_level=2)

        response = WarrantResponse(
            decision=Decision.AUTHORIZED,
            warrant_id=warrant.id,
            authority=authority,
            conditions_evaluated=conditions,
            trust_elevation=trust_elevation,
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
