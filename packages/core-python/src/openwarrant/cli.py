"""CLI entry point for OpenWarrant."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from openwarrant.engine import WarrantEngine
from openwarrant.models import WarrantRequest


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="openwarrant",
        description="OpenWarrant — governance checks for AI agents",
    )
    subparsers = parser.add_subparsers(dest="command")

    # check subcommand
    check_parser = subparsers.add_parser(
        "check", help="Check a warrant request"
    )
    check_parser.add_argument(
        "--action", required=True, help="Action to check"
    )
    check_parser.add_argument(
        "--role", required=True, help="Role of the requester"
    )
    check_parser.add_argument(
        "--data-type", required=True, help="Data type classification"
    )
    check_parser.add_argument(
        "--warrant-dir",
        required=True,
        help="Directory containing warrant YAML files",
    )
    check_parser.add_argument(
        "--agent-id", default="cli-agent", help="Agent identifier"
    )
    check_parser.add_argument(
        "--context",
        default="{}",
        help='JSON context string (e.g. \'{"patient_consent": true}\')',
    )
    check_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "check":
        _handle_check(args)


def _handle_check(args: argparse.Namespace) -> None:
    warrant_dir = Path(args.warrant_dir)
    if not warrant_dir.exists():
        print(f"Error: Warrant directory not found: {warrant_dir}", file=sys.stderr)
        sys.exit(1)

    try:
        context = json.loads(args.context)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON context: {e}", file=sys.stderr)
        sys.exit(1)

    engine = WarrantEngine(warrant_store=warrant_dir)

    request = WarrantRequest(
        agent_id=args.agent_id,
        action=args.action,
        role=args.role,
        data_type=args.data_type,
        context=context,
    )

    response = engine.check(request)

    if args.format == "json":
        output = {
            "decision": response.decision.value,
            "warrant_id": response.warrant_id,
            "audit_hash": response.audit_hash,
            "conditions": [
                {
                    "condition": c.condition,
                    "met": c.met,
                    "detail": c.detail,
                }
                for c in response.conditions_evaluated
            ],
        }
        if response.authority:
            output["authority"] = {
                "issuer": response.authority.issuer,
                "type": response.authority.type,
                "issued": response.authority.issued,
                "expires": response.authority.expires,
                "scope": response.authority.scope,
            }
        print(json.dumps(output, indent=2))
    else:
        print(f"Decision: {response.decision.value}")
        if response.warrant_id:
            print(f"Warrant:  {response.warrant_id}")
        if response.authority:
            print(f"Issuer:   {response.authority.issuer}")
        if response.conditions_evaluated:
            print("Conditions:")
            for c in response.conditions_evaluated:
                status = "MET" if c.met else "NOT MET"
                print(f"  [{status}] {c.condition}: {c.detail}")
        print(f"Audit:    {response.audit_hash}")


if __name__ == "__main__":
    main()
