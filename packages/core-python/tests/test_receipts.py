"""Tests for v0.2 execution receipts and reconciliation."""

from pathlib import Path

from openwarrant import (
    CoverageWindow,
    Decision,
    ExecutionReceipt,
    InputGap,
    ReconciliationStatus,
    WarrantEngine,
    reconcile,
)
from openwarrant.loader import load_warrant_file

EXAMPLES = Path(__file__).resolve().parents[3] / "examples" / "warrants"
WINDOW = CoverageWindow(start="2026-03-01T00:00:00Z", end="2026-09-01T00:00:00Z")


def _receipt(agent: str, output: str, inputs=None, gaps=None, target="patient-123"):
    return ExecutionReceipt(
        agent_id=agent,
        warrant_id="chart-summarizer-readonly-001",
        action="generate-interval-change-summary",
        target=target,
        inputs_read=inputs or ["notes/2026-08-14", "labs/2026-08-20", "meds/current"],
        inputs_omitted=gaps or [],
        coverage_window=WINDOW,
        source_refs=["Epic:note:8841", "Epic:lab:K:2026-08-20"],
        output_hash=ExecutionReceipt.hash_output(output),
        accountable_owner="cmio@memorial.org",
    )


# --- receipt basics --------------------------------------------------------


def test_receipt_hash_is_stable_and_changes_with_content():
    a = _receipt("summarizer-A", "K 6.1 on 8/20, new since last visit")
    b = _receipt("summarizer-A", "K 6.1 on 8/20, new since last visit")
    c = _receipt("summarizer-A", "no interval change")
    # same content → same hash, except produced_at timestamps differ; compare canonical fields
    assert a.output_hash == b.output_hash
    assert a.output_hash != c.output_hash
    assert a.receipt_hash.startswith("sha256:")


def test_receipt_reports_gaps():
    r = _receipt(
        "summarizer-A",
        "no interval change",
        gaps=[InputGap(source="labs/2026-08-20", reason="unparseable")],
    )
    assert r.has_gaps
    assert r.to_dict()["inputs_omitted"][0]["source"] == "labs/2026-08-20"


# --- reconciliation ---------------------------------------------------------


def test_consistent_receipts_authorize():
    a = _receipt("summarizer-A", "K 6.1 on 8/20, new since last visit")
    b = _receipt("summarizer-B", "K 6.1 on 8/20, new since last visit")
    res = reconcile([a, b])
    assert res.status is ReconciliationStatus.CONSISTENT
    assert res.decision is Decision.AUTHORIZED
    assert res.accountable_owners == ["cmio@memorial.org"]


def test_divergent_outputs_escalate_by_default():
    a = _receipt("summarizer-A", "K 6.1 on 8/20, new since last visit")
    b = _receipt(
        "summarizer-B",
        "no interval change",
        inputs=["notes/2026-08-14", "meds/current"],  # never read the lab
        gaps=[InputGap(source="labs/2026-08-20", reason="unparseable")],
    )
    res = reconcile([a, b])
    assert res.status is ReconciliationStatus.DIVERGENT
    assert res.decision is Decision.ESCALATE
    kinds = {d.kind for d in res.divergences}
    assert {"output", "inputs_read", "gaps"} <= kinds


def test_reconciliation_policy_deny_and_log():
    a = _receipt("summarizer-A", "x")
    b = _receipt("summarizer-B", "y")
    assert reconcile([a, b], policy="deny").decision is Decision.DENIED
    assert reconcile([a, b], policy="log").decision is Decision.AUTHORIZED


def test_different_targets_are_incomparable():
    a = _receipt("summarizer-A", "x", target="patient-1")
    b = _receipt("summarizer-B", "y", target="patient-2")
    res = reconcile([a, b])
    assert res.status is ReconciliationStatus.INCOMPARABLE


def test_non_overlapping_windows_are_incomparable():
    a = _receipt("summarizer-A", "x")
    b = _receipt("summarizer-B", "y")
    b.coverage_window = CoverageWindow(start="2025-01-01T00:00:00Z", end="2025-06-01T00:00:00Z")
    assert reconcile([a, b]).status is ReconciliationStatus.INCOMPARABLE


def test_single_receipt_is_insufficient():
    res = reconcile([_receipt("summarizer-A", "x")])
    assert res.status is ReconciliationStatus.INSUFFICIENT


# --- warrant fields + engine integration -----------------------------------


def test_loader_reads_owner_and_policy():
    w = load_warrant_file(EXAMPLES / "healthcare-chart-summarizer.yaml")
    assert w.accountable_owner == "cmio@memorial.org"
    assert w.reconciliation_policy == "escalate"
    assert "generate-interval-change-summary" in w.actions


def test_engine_attest_and_reconcile_land_on_one_chain():
    escalations = []
    engine = WarrantEngine(
        warrant_store=str(EXAMPLES),
        on_escalate=lambda r: escalations.append(r),
    )
    w = next(x for x in engine.warrants if x.id == "chart-summarizer-readonly-001")

    a = ExecutionReceipt.for_warrant(
        w, "summarizer-A", "generate-interval-change-summary", "patient-123",
        inputs_read=["labs/2026-08-20"], coverage_window=WINDOW,
        output_hash=ExecutionReceipt.hash_output("K 6.1"),
    )
    b = ExecutionReceipt.for_warrant(
        w, "summarizer-B", "generate-interval-change-summary", "patient-123",
        inputs_read=[], coverage_window=WINDOW,
        inputs_unavailable=[InputGap("labs/2026-08-20", "unparseable")],
        output_hash=ExecutionReceipt.hash_output("no change"),
    )
    assert a.accountable_owner == "cmio@memorial.org"  # pulled from the warrant

    before = len(engine.audit)
    engine.attest(a)
    engine.attest(b)
    res = engine.reconcile([a, b])

    assert res.decision is Decision.ESCALATE
    assert len(escalations) == 1
    assert len(engine.audit) == before + 3
    types = [r.record_type for r in engine.audit.chain[-3:]]
    assert types == ["execution_receipt", "execution_receipt", "reconciliation"]
    assert engine.audit.verify_chain()
    assert res.audit_hash == engine.audit.last_hash
