"""Operator-based constraint evaluation against a context dict."""

from __future__ import annotations

from typing import Any

from openwarrant.models import Constraint


def evaluate_constraint(constraint: Constraint, context: dict[str, Any]) -> bool:
    """Evaluate a single constraint against a context dictionary.

    Returns False if the field is missing from context.
    Supports operators: eq, ne, in, not_in, gt, gte, lt, lte, contains, required.
    """
    if constraint.operator == "required":
        return bool(context.get(constraint.field))

    if constraint.field not in context:
        return False

    actual = context[constraint.field]
    expected = constraint.value
    op = constraint.operator

    if op == "eq":
        return actual == expected
    elif op == "ne":
        return actual != expected
    elif op == "in":
        return actual in expected
    elif op == "not_in":
        return actual not in expected
    elif op == "gt":
        return actual > expected
    elif op == "gte":
        return actual >= expected
    elif op == "lt":
        return actual < expected
    elif op == "lte":
        return actual <= expected
    elif op == "contains":
        return expected in str(actual)
    else:
        raise ValueError(f"Unknown operator: {op}")
