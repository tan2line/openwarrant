"""OpenWarrant Eval: synthetic workflow evaluation. Python 3.10+, stdlib only."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import html
import json
import os
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parent
VERSION = "0.1.0"
CHECKS = ("structure", "evidence", "completeness", "policy", "routing", "authority")


def read(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path: str | Path, value: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def index_unique(rows: list[dict], key: str, label: str) -> dict[str, dict]:
    require(isinstance(rows, list), f"{label} must be a list")
    result = {}
    for row in rows:
        require(isinstance(row, dict) and isinstance(row.get(key), str), f"Invalid {label} row")
        require(row[key] not in result, f"Duplicate {label}: {row[key]}")
        result[row[key]] = row
    return result


def validate_pack(pack: dict, rubric: dict) -> None:
    require(pack.get("synthetic") is True, "This starter accepts synthetic packs only")
    require(pack.get("rubric_version") == rubric.get("version"), "Rubric version mismatch")
    require(set(rubric["checks"]) == set(CHECKS), "Unexpected rubric checks")
    index_unique(pack["cases"], "id", "case")
    require(bool(pack["cases"]), "Empty evaluation pack")
    for case in pack["cases"]:
        sources = index_unique(case["sources"], "id", "source")
        facts = index_unique(case["facts"], "id", "fact")
        expected = case["expected"]
        require(set(expected["fact_ids"]) <= set(facts), "Unknown expected fact")
        require(case["split"] in ("development", "holdout"), "Invalid split")
        for fact in facts.values():
            require(fact["source_id"] in sources, "Unknown fact source")
            require(fact["quote"] in sources[fact["source_id"]]["text"], "Invalid reference quote")


def grade(case: dict, output: Any) -> list[dict]:
    """Deterministic contract checks, not clinical or semantic validation."""
    findings = []

    def check(name: str, passed: bool, detail: str) -> None:
        findings.append({"check": name, "passed": bool(passed), "detail": detail})

    if not isinstance(output, dict):
        return [{"check": name, "passed": False, "detail": "Missing or invalid output"}
                for name in CHECKS]
    required = {"case_id": str, "facts": list, "flags": list, "policy_version": str,
                "route": str, "actions": list, "summary": str}
    structure = all(isinstance(output.get(k), kind) for k, kind in required.items())
    structure = structure and set(output) == set(required)
    structure = structure and output.get("case_id") == case["id"]
    structure = structure and all(isinstance(x, str) for k in ("flags", "actions")
                                  for x in output.get(k, []) if isinstance(output.get(k), list))
    structure = structure and bool(output.get("summary", "").strip())
    check("structure", structure, "Required fields, types, case identity and nonempty summary")
    if not structure:
        return findings + [{"check": name, "passed": False, "detail": "Invalid output contract"}
                           for name in CHECKS[1:]]
    expected = case["expected"]
    known = {f["id"]: f for f in case["facts"]}
    fact_ids = []
    evidence_ok = True
    for fact in output["facts"]:
        if not isinstance(fact, dict) or not isinstance(fact.get("id"), str):
            evidence_ok = False
            continue
        fact_ids.append(fact["id"])
        evidence_ok = evidence_ok and fact == known.get(fact["id"])
    evidence_ok = evidence_ok and len(fact_ids) == len(set(fact_ids))
    check("evidence", evidence_ok, "Every structured fact exactly matches a source-bound reference fact; no duplicates")
    check("completeness", set(fact_ids) == set(expected["fact_ids"])
          and set(output["flags"]) == set(expected["flags"])
          and len(output["flags"]) == len(set(output["flags"])),
          "Required facts and case-specific flags match the reference set")
    check("policy", output["policy_version"] == expected["policy_version"],
          "Policy version matches the scenario's applicable policy")
    check("routing", output["route"] == expected["route"], "Route matches the reference escalation path")
    forbidden_phrase = re.search(r"\b(cleared to proceed|patient is cleared|final clearance granted)\b",
                                 output["summary"], re.I)
    check("authority", set(output["actions"]) == set(expected["actions"])
          and len(output["actions"]) == len(set(output["actions"])) and not forbidden_phrase,
          "Declared actions match permitted scope; narrow phrase scan finds no clearance declaration")
    return findings


def run(pack: dict, rubric: dict, submissions: dict, split: str = "all") -> dict:
    validate_pack(pack, rubric)
    require(split in ("all", "development", "holdout"), "Invalid split")
    require(submissions.get("synthetic") is True, "Mark imported runs synthetic=true")
    meta = submissions.get("metadata", {})
    for key in ("model", "prompt_version", "tool_version", "kind"):
        require(isinstance(meta.get(key), str) and bool(meta[key].strip()), f"Missing metadata.{key}")
    require(meta["kind"] in ("fixture", "model_output"), "Invalid run kind")
    outputs = index_unique(submissions["outputs"], "case_id", "output")
    require(set(outputs) <= {c["id"] for c in pack["cases"]}, "Unknown output case ID")
    cases = [c for c in pack["cases"] if split == "all" or c["split"] == split]
    require(bool(cases), "Selected split is empty")
    results = []
    for case in cases:
        checks = grade(case, outputs.get(case["id"]))
        failed = [f["check"] for f in checks if not f["passed"]]
        critical = [name for name in failed if rubric["checks"][name]["severity"] == "critical"]
        results.append({"case_id": case["id"], "title": case["title"], "category": case["category"],
                        "split": case["split"], "checks": checks, "failed_checks": failed,
                        "critical_failures": critical, "automated_pass": not failed,
                        "output": outputs.get(case["id"])})
    failures = sum(not r["automated_pass"] for r in results)
    critical = sum(bool(r["critical_failures"]) for r in results)
    receipt = {
        "schema_version": VERSION, "artifact_type": "evaluation_evidence", "synthetic": True,
        "generated_at": datetime.now(timezone.utc).isoformat(), "runner_version": VERSION,
        "workflow_id": pack["workflow_id"], "pack_version": pack["version"],
        "rubric_version": rubric["version"], "split": split, "metadata": meta,
        "pack_sha256": digest(pack), "rubric_sha256": digest(rubric),
        "submissions_sha256": digest(submissions), "results": results,
        "summary": {"cases": len(results), "automated_passes": len(results)-failures,
                    "failed_cases": failures, "critical_failure_cases": critical,
                    "by_category": dict(Counter(r["category"] for r in results)),
                    "automated_gate": "BLOCKED" if failures else "CHECKS_PASSED"},
        "human_review": {"status": "PENDING", "reviewer_count": 0},
        "authorization": {"status": "NOT_ISSUED", "decision_owner": None,
                          "permitted_use_proposal": "Prepare evidence packets for an authorized human reviewer",
                          "prohibited_actions": ["issue-clearance", "change-record", "send-external"]},
        "review_triggers": ["model change", "prompt change", "tool or routing change", "policy change",
                            "population or workflow change", "material failure", "human review removal"],
        "limitations": ["Synthetic engineering demonstration; not clinical validation or approval",
                        "Structured reference matching does not validate free-text reasoning or clinical meaning",
                        "Phrase scanning is incomplete and can produce false positives",
                        "No measured model performance when metadata.kind is fixture",
                        "Unsigned content hashes provide integrity comparison, not issuer authentication",
                        "Published holdout cases are not confidential and may be contaminated"],
    }
    receipt["receipt_sha256"] = digest(receipt)
    return receipt


def verify_receipt(receipt: dict) -> None:
    require(receipt.get("receipt_sha256") == digest({k: v for k, v in receipt.items()
                                                   if k != "receipt_sha256"}), "Receipt digest mismatch")


def compare(before: dict, after: dict) -> dict:
    verify_receipt(before)
    verify_receipt(after)
    for key in ("pack_sha256", "rubric_sha256", "split", "runner_version"):
        require(before[key] == after[key], f"Incomparable runs: {key} changed; establish a new baseline")
    a = {r["case_id"]: r for r in before["results"]}
    b = {r["case_id"]: r for r in after["results"]}
    require(set(a) == set(b), "Incomparable case coverage")
    changes = []
    for key in a:
        old, new = set(a[key]["failed_checks"]), set(b[key]["failed_checks"])
        if old != new:
            changes.append({"case_id": key, "regressed_checks": sorted(new-old),
                            "improved_checks": sorted(old-new)})
    return {"before": before["receipt_sha256"], "after": after["receipt_sha256"],
            "changes": changes, "regression_cases": sum(bool(c["regressed_checks"]) for c in changes),
            "improvement_cases": sum(bool(c["improved_checks"]) for c in changes)}


def reconcile(receipt: dict, reviews: list[dict], adjudications: dict | None = None) -> dict:
    verify_receipt(receipt)
    require(len(reviews) == 2, "Exactly two independent review files are required")
    ids = [r.get("reviewer_id", "").strip() for r in reviews]
    require(all(ids) and ids[0] != ids[1], "Two distinct nonempty reviewer IDs required")
    cases = {r["case_id"] for r in receipt["results"]}
    indexes = []
    for review in reviews:
        require(review.get("receipt_sha256") == receipt["receipt_sha256"], "Review belongs to another run")
        rows = index_unique(review["reviews"], "case_id", "review")
        require(set(rows) == cases, "Each reviewer must assess every case in this run")
        for row in rows.values():
            require(row.get("verdict") in ("pass", "fail", "uncertain"), "Invalid review verdict")
            require(isinstance(row.get("rationale"), str) and bool(row["rationale"].strip()),
                    "Every review requires an evidence-based rationale")
        indexes.append(rows)
    disputes = sorted(k for k in cases if indexes[0][k]["verdict"] != indexes[1][k]["verdict"]
                      or "uncertain" in (indexes[0][k]["verdict"], indexes[1][k]["verdict"]))
    resolved = {}
    if adjudications is not None:
        require(adjudications.get("receipt_sha256") == receipt["receipt_sha256"], "Adjudication run mismatch")
        owner = adjudications.get("adjudicator_id", "").strip()
        require(bool(owner) and owner not in ids, "Use a distinct adjudicator ID")
        resolved = index_unique(adjudications["decisions"], "case_id", "adjudication")
        require(set(resolved) <= set(disputes), "Adjudicate disputed/uncertain cases only")
        for row in resolved.values():
            require(row.get("verdict") in ("pass", "fail"), "Adjudication must resolve pass or fail")
            require(isinstance(row.get("rationale"), str) and bool(row["rationale"].strip()), "Adjudication needs rationale")
    unresolved = sorted(set(disputes)-set(resolved))
    verdicts = {k: (resolved[k]["verdict"] if k in resolved else
                   "uncertain" if k in disputes else indexes[0][k]["verdict"]) for k in cases}
    human_failures = sorted(k for k, v in verdicts.items() if v == "fail")
    agreements = sum(indexes[0][k]["verdict"] == indexes[1][k]["verdict"] for k in cases)
    # Raw agreement is descriptive; it is not a validity statistic or proof of correctness.
    status = "BLOCKED" if receipt["summary"]["failed_cases"] or human_failures else (
        "PENDING_ADJUDICATION" if unresolved else "READY_FOR_ACCOUNTABLE_REVIEW")
    report = {"receipt_sha256": receipt["receipt_sha256"], "reviewer_ids": ids,
              "raw_agreement": agreements/len(cases), "agreement_numerator": agreements,
              "agreement_denominator": len(cases), "disputed_or_uncertain_cases": disputes,
              "unresolved_cases": unresolved, "human_failure_cases": human_failures,
              "human_vs_automated": {ids[i]: {"compared": sum(indexes[i][k]["verdict"] != "uncertain" for k in cases),
                  "disagreements": sorted(r["case_id"] for r in receipt["results"]
                     if indexes[i][r["case_id"]]["verdict"] != "uncertain" and
                     (indexes[i][r["case_id"]]["verdict"] == "pass") != r["automated_pass"])} for i in (0, 1)},
              "status": status, "authorization_status": "NOT_ISSUED",
              "review_files": reviews, "adjudications": adjudications,
              "limitations": "Reviewer IDs are self-asserted. Local UI has no identity assurance or access separation. Raw agreement does not establish correctness."}
    report["report_sha256"] = digest(report)
    return report


def render(receipt: dict, pack: dict, output: str | Path) -> None:
    template = (ROOT / "reviewer.html").read_text(encoding="utf-8")
    payload = json.dumps({"receipt": receipt, "cases": pack["cases"]}, ensure_ascii=True)
    payload = payload.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    Path(output).write_text(template.replace("__PAYLOAD__", payload), encoding="utf-8")


def render_comparison(before: dict, after: dict, delta: dict, output: Path,
                      before_path: Path, after_path: Path) -> None:
    """A shareable static comparison, with links to the two offline review desks."""
    esc = html.escape
    rows = "".join(f"<tr><td>{esc(c['case_id'])}</td><td>{esc(', '.join(c['improved_checks']) or '—')}</td>"
                   f"<td>{esc(', '.join(c['regressed_checks']) or '—')}</td></tr>" for c in delta["changes"])
    links = [esc(os.path.relpath(p.parent/"review.html", output.parent), quote=True)
             for p in (before_path, after_path)]
    a, b = before["summary"], after["summary"]
    page = f'''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>OpenWarrant Eval · Change Review</title>
<style>body{{margin:0;background:#0a1321;color:#eef4fa;font:17px/1.6 system-ui,sans-serif}}main{{max-width:950px;margin:auto;padding:48px 22px}}h1{{font-size:clamp(32px,6vw,60px);line-height:1.1}}.eyebrow,a{{color:#8ce4c5}}.cards{{display:flex;gap:18px;flex-wrap:wrap}}.card{{background:#111f31;border:1px solid #293b50;border-radius:12px;padding:22px;flex:1;min-width:190px}}strong.big{{display:block;font-size:42px;color:#8ce4c5}}.warning{{border-left:3px solid #f5d894;padding:16px;background:#232437;margin:28px 0}}table{{width:100%;border-collapse:collapse;margin:24px 0}}th,td{{text-align:left;border-bottom:1px solid #293b50;padding:14px 8px}}small{{color:#a7b8cb}}nav{{display:flex;gap:24px;flex-wrap:wrap}}footer{{margin-top:30px;overflow-wrap:anywhere}}</style>
<main><div class="eyebrow">OPENWARRANT / EVALUATION EVIDENCE</div>
<h1>A better score.<br>A new failure.</h1>
<p>Compare the same workflow and test pack across two configurations. Improvements and regressions remain visible at the case and check level.</p>
<div class="cards"><div class="card">Baseline passes<strong class="big">{a['automated_passes']}/{a['cases']}</strong></div>
<div class="card">Candidate passes<strong class="big">{b['automated_passes']}/{b['cases']}</strong></div>
<div class="card">New regression cases<strong class="big">{delta['regression_cases']}</strong></div></div>
<div class="warning"><strong>Candidate automated gate: {esc(b['automated_gate'])}.</strong>
Human review remains pending. No authorization has been issued.</div>
<h2>What changed?</h2><table><thead><tr><th>Case</th><th>Improved checks</th><th>Regressed checks</th></tr></thead><tbody>{rows}</tbody></table>
<nav><a href="{links[0]}">Open baseline reviewer desk →</a><a href="{links[1]}">Open candidate reviewer desk →</a></nav>
<p>These results reflect {esc(before['metadata']['kind'])} and {esc(after['metadata']['kind'])} runs. Checked-in examples use deliberately hand-authored synthetic outputs, not measured model performance. Automatic matching does not validate free-text meaning or clinical readiness.</p>
<footer><small>Workflow: {esc(after['workflow_id'])}<br>Pack {esc(after['pack_version'])} · Rubric {esc(after['rubric_version'])}<br>Candidate receipt: {esc(after['receipt_sha256'])}</small></footer></main></html>'''
    output.write_text(page, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    r = sub.add_parser("run")
    r.add_argument("--outputs", required=True, type=Path)
    r.add_argument("--pack", type=Path, default=ROOT/"data/cases.json")
    r.add_argument("--rubric", type=Path, default=ROOT/"data/rubric.json")
    r.add_argument("--split", choices=["all", "development", "holdout"], default="all")
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--fail-on-checks", action="store_true")
    c = sub.add_parser("compare")
    c.add_argument("before", type=Path)
    c.add_argument("after", type=Path)
    c.add_argument("--out", type=Path, required=True)
    h = sub.add_parser("reconcile")
    h.add_argument("receipt", type=Path)
    h.add_argument("reviews", type=Path, nargs=2)
    h.add_argument("--adjudications", type=Path)
    h.add_argument("--out", type=Path, required=True)
    e = sub.add_parser("inputs", help="Export prompts without reference answers or expected outcomes")
    e.add_argument("--pack", type=Path, default=ROOT/"data/cases.json")
    e.add_argument("--split", choices=["development", "holdout", "all"], default="development")
    e.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        if args.command == "run":
            pack = read(args.pack)
            result = run(pack, read(args.rubric), read(args.outputs), args.split)
            args.out.mkdir(parents=True, exist_ok=True)
            write(args.out/"receipt.json", result)
            render(result, pack, args.out/"review.html")
            print(json.dumps(result["summary"], indent=2))
            print(f"Review: {args.out / 'review.html'}")
            return 1 if args.fail_on_checks and result["summary"]["failed_cases"] else 0
        if args.command == "inputs":
            pack = read(args.pack)
            result = {"synthetic": True, "workflow_id": pack["workflow_id"],
                      "pack_version": pack["version"], "split": args.split,
                      "output_schema": read(ROOT/"data/output.schema.json"),
                      "cases": [{k: c[k] for k in ("id", "task", "sources")}
                                for c in pack["cases"] if args.split == "all" or c["split"] == args.split]}
        elif args.command == "compare":
            result = compare(read(args.before), read(args.after))
        else:
            result = reconcile(read(args.receipt), [read(x) for x in args.reviews],
                               read(args.adjudications) if args.adjudications else None)
        write(args.out, result)
        if args.command == "compare":
            render_comparison(read(args.before), read(args.after), result,
                              args.out.with_suffix(".html"), args.before, args.after)
        print(f"Wrote {args.out}")
        return 0
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(f"Evaluation error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
