"""Load warrant definitions from YAML files.

Uses only the Python standard library — no external YAML parser required.
Implements a minimal YAML subset parser sufficient for warrant files.
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from openwarrant.models import Warrant


def _parse_yaml_value(value: str) -> Any:
    """Parse a single YAML scalar value."""
    value = value.strip()
    if not value:
        return ""

    # Remove inline comments
    if "  #" in value:
        value = value[: value.index("  #")].strip()

    # Inline lists: [item1, item2, ...]
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_yaml_value(x.strip()) for x in inner.split(",") if x.strip()]

    # Quoted strings
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]

    # Booleans
    if value.lower() in ("true", "yes"):
        return True
    if value.lower() in ("false", "no"):
        return False

    # None
    if value.lower() in ("null", "~", ""):
        return None

    # Numbers
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass

    return value


def _get_indent(line: str) -> int:
    """Get the indentation level of a line."""
    return len(line) - len(line.lstrip())


def parse_yaml(text: str) -> dict[str, Any]:
    """Parse a minimal YAML document into a nested dict.

    Supports: mappings, sequences (- item), scalars, quoted strings.
    Sufficient for warrant YAML files.
    """
    lines = text.split("\n")
    return _parse_block(lines, 0, 0)[0]


def _parse_block(
    lines: list[str], start: int, base_indent: int
) -> tuple[dict[str, Any], int]:
    """Parse a YAML block at a given indentation level."""
    result: dict[str, Any] = {}
    i = start

    while i < len(lines):
        line = lines[i]

        # Skip empty lines, comments, and document markers
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped == "---":
            i += 1
            continue

        indent = _get_indent(line)

        # If we've dedented past our block, we're done
        if indent < base_indent:
            break

        # Skip lines that are deeper than our base (shouldn't happen at top level)
        if indent > base_indent and not result:
            base_indent = indent

        if indent != base_indent:
            if indent < base_indent:
                break
            i += 1
            continue

        # Handle list items at this level
        if stripped.startswith("- "):
            # This is a list — but we handle lists inside key parsing
            i += 1
            continue

        # Parse key: value
        match = re.match(r"^(\s*)([\w_][\w\-_]*)\s*:\s*(.*)", line)
        if not match:
            i += 1
            continue

        key = match.group(2)
        value_str = match.group(3).strip()

        # Remove inline comments from value
        if value_str and "  #" in value_str:
            value_str = value_str[: value_str.index("  #")].strip()

        if value_str:
            # Inline value
            result[key] = _parse_yaml_value(value_str)
            i += 1
        else:
            # Block value — check what's below
            next_i = i + 1
            while next_i < len(lines) and (
                not lines[next_i].strip()
                or lines[next_i].strip().startswith("#")
            ):
                next_i += 1

            if next_i >= len(lines):
                result[key] = None
                i = next_i
                continue

            next_indent = _get_indent(lines[next_i])
            next_stripped = lines[next_i].strip()

            if next_indent <= base_indent:
                result[key] = None
                i = next_i
            elif next_stripped.startswith("- "):
                # Parse list
                items, i = _parse_list(lines, next_i, next_indent)
                result[key] = items
            else:
                # Parse nested mapping
                nested, i = _parse_block(lines, next_i, next_indent)
                result[key] = nested

    return result, i


def _parse_list(
    lines: list[str], start: int, base_indent: int
) -> tuple[list[Any], int]:
    """Parse a YAML list."""
    items: list[Any] = []
    i = start

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            i += 1
            continue

        indent = _get_indent(line)
        if indent < base_indent:
            break

        if indent == base_indent and stripped.startswith("- "):
            item_content = stripped[2:].strip()

            # Check if this is a list item with a key (mapping in list)
            map_match = re.match(r"^([\w_][\w\-_]*)\s*:\s*(.*)", item_content)
            if map_match:
                # This is a mapping entry inside a list
                item_key = map_match.group(1)
                item_val_str = map_match.group(2).strip()

                if item_val_str:
                    if item_val_str and "  #" in item_val_str:
                        item_val_str = item_val_str[
                            : item_val_str.index("  #")
                        ].strip()
                    item_dict = {item_key: _parse_yaml_value(item_val_str)}
                else:
                    # Parse nested block under this list-mapping item
                    next_i = i + 1
                    while next_i < len(lines) and not lines[next_i].strip():
                        next_i += 1
                    if next_i < len(lines):
                        next_indent = _get_indent(lines[next_i])
                        nested, next_i = _parse_block(
                            lines, next_i, next_indent
                        )
                        item_dict = {item_key: nested}
                        i = next_i
                        items.append(item_dict)
                        continue
                    else:
                        item_dict = {item_key: None}

                # Check for more keys at deeper indent
                next_i = i + 1
                content_indent = base_indent + 2
                while next_i < len(lines):
                    nl = lines[next_i]
                    ns = nl.strip()
                    if not ns or ns.startswith("#"):
                        next_i += 1
                        continue
                    ni = _get_indent(nl)
                    if ni < content_indent:
                        break
                    km = re.match(r"^(\s*)([\w_][\w\-_]*)\s*:\s*(.*)", nl)
                    if km and _get_indent(nl) == content_indent:
                        k = km.group(2)
                        v = km.group(3).strip()
                        if v and "  #" in v:
                            v = v[: v.index("  #")].strip()
                        if v:
                            item_dict[k] = _parse_yaml_value(v)
                        else:
                            # Check for nested content
                            check_i = next_i + 1
                            while check_i < len(lines) and not lines[check_i].strip():
                                check_i += 1
                            if check_i < len(lines):
                                ci = _get_indent(lines[check_i])
                                cs = lines[check_i].strip()
                                if ci > content_indent and cs.startswith("- "):
                                    sub_list, check_i = _parse_list(lines, check_i, ci)
                                    item_dict[k] = sub_list
                                    next_i = check_i
                                    continue
                                elif ci > content_indent:
                                    sub_map, check_i = _parse_block(lines, check_i, ci)
                                    item_dict[k] = sub_map
                                    next_i = check_i
                                    continue
                            item_dict[k] = None
                        next_i += 1
                    else:
                        break

                items.append(item_dict)
                i = next_i
            else:
                # Simple list item — could be a list like ["a", "b"]
                if item_content.startswith("[") and item_content.endswith("]"):
                    inner = item_content[1:-1]
                    items.append(
                        [
                            _parse_yaml_value(x.strip())
                            for x in inner.split(",")
                            if x.strip()
                        ]
                    )
                else:
                    items.append(_parse_yaml_value(item_content))
                i += 1
        elif indent > base_indent:
            i += 1
        else:
            break

    return items, i


def _parse_datetime(value: str) -> datetime:
    """Parse an ISO 8601 datetime string."""
    value = value.strip().strip('"').strip("'")
    # Handle Z suffix
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return datetime.fromisoformat(value.replace("T", " "))


def _extract_warrant(data: dict[str, Any]) -> Warrant:
    """Extract a Warrant object from parsed YAML data."""
    w = data.get("warrant", data)

    roles = []
    who = w.get("who_can_act", {})
    if isinstance(who, dict):
        roles = who.get("roles", [])
    if not roles:
        roles = []

    actions = []
    what = w.get("what_they_can_do", {})
    if isinstance(what, dict):
        actions = what.get("actions", [])
    if not actions:
        actions = []

    data_types = []
    if isinstance(what, dict):
        data_types = what.get("data_types", [])
    if not data_types:
        data_types = []

    conditions = []
    raw_conditions = w.get("under_what_conditions", [])
    if isinstance(raw_conditions, list):
        for c in raw_conditions:
            if isinstance(c, dict):
                conditions.append(c)

    valid_from_str = w.get("valid_from", "2026-01-01T00:00:00Z")
    valid_until_str = w.get("valid_until", "2026-12-31T23:59:59Z")

    return Warrant(
        id=str(w.get("id", "")),
        issuer=str(w.get("issuer", "")),
        signature=str(w.get("signature", "")),
        roles=roles,
        actions=actions,
        data_types=data_types,
        conditions=conditions,
        valid_from=_parse_datetime(str(valid_from_str)),
        valid_until=_parse_datetime(str(valid_until_str)),
        trust_level_required=int(w.get("trust_level_required", 0)),
        audit_required=bool(w.get("audit_required", True)),
        escalation_target=str(w.get("escalation_target", "")),
        notes=str(w.get("notes", "")),
    )


def load_warrant_file(path: str | Path) -> Warrant:
    """Load a single warrant from a YAML file."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    data = parse_yaml(text)
    return _extract_warrant(data)


def load_warrant_dir(path: str | Path) -> list[Warrant]:
    """Load all warrants from a directory of YAML files."""
    path = Path(path)
    warrants = []

    if not path.is_dir():
        raise FileNotFoundError(f"Warrant directory not found: {path}")

    for file in sorted(path.iterdir()):
        if file.suffix in (".yaml", ".yml"):
            try:
                warrant = load_warrant_file(file)
                warrants.append(warrant)
            except Exception:
                continue

    return warrants
