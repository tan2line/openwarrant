"""Wildcard action matching for dot-separated action paths."""

from __future__ import annotations


def action_matches(pattern: str, action: str) -> bool:
    """Check if an action matches a pattern with wildcard support.

    Supports dot-separated paths where ``*`` matches any remaining segments.
    """
    pattern_parts = pattern.split(".")
    action_parts = action.split(".")
    for i, p in enumerate(pattern_parts):
        if p == "*":
            return True
        if i >= len(action_parts):
            return False
        if p != action_parts[i]:
            return False
    return len(pattern_parts) == len(action_parts)
