# Changelog

## 0.2.0 — 2026-09-03

**Execution receipts and reconciliation.** Governance for read-only executions.

Added
- `ExecutionReceipt`: content-level provenance for a warranted execution — `inputs_read`, `inputs_unavailable`, `inputs_omitted`, `coverage_window`, `source_refs`, `output_hash`, `accountable_owner`, `receipt_hash`.
- `reconcile()` and `WarrantEngine.reconcile()`: the disagreement protocol. Compares receipts on one target; returns `CONSISTENT | DIVERGENT | INCOMPARABLE | INSUFFICIENT`; `DIVERGENT` resolves per `reconciliation_policy` (`escalate` default, `deny`, `log`) and fires the escalate hook.
- `WarrantEngine.attest()`: records a receipt on the audit chain.
- `AuditRecord.record_type` (`decision | execution_receipt | reconciliation`) and `AuditRecord.payload`. One hash chain for all three.
- Warrant fields `accountable_owner` and `reconciliation_policy` (loader + model).
- Example warrant `examples/warrants/healthcare-chart-summarizer.yaml` applying the four credentialing moves.
- Spec: `docs/warrant-schema.yaml` receipt + reconciliation schemas; `docs/architecture.md` §4b.
- Tests: `tests/test_receipts.py` (10 tests; suite now 65).

Unchanged
- All v0.1 decision semantics, warrant fields, and audit hashing for `decision` records. Existing warrants load without modification.

Not yet
- TypeScript parity for receipts/reconciliation (Python only in this release).
- Signed receipts (Ed25519 over `receipt_hash`) — planned alongside warrant signature verification.

## 0.1.0 — 2026-02-16

Initial release. Architecture spec, warrant schema, working Python + TypeScript engine with passing tests. DOI 10.5281/zenodo.18666989.
