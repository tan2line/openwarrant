# OpenWarrant Eval

**Turn workflow tests into reviewable evidence for an accountable decision.**

A runnable, dependency-free Python 3.10+ starter for one synthetic workflow: preparing a clinical review packet from records and a fictional policy for an authorized human reviewer. The package includes 25 scenarios, versioned criteria, structured-output checks, a local reviewer desk, reviewer reconciliation, version comparisons, and unsigned evidence receipts.

This is an engineering demonstration. The checked-in outputs are hand-authored fixtures, not measured model results. No clinical guideline, clinical readiness claim, certification, or authorization is supplied. All policies and records in the pack are fictional.

## Run the demonstration

From the repository root:

```bash
python packages/eval-python/evalkit.py run --outputs packages/eval-python/data/baseline.outputs.json --out /tmp/oweval-baseline
python packages/eval-python/evalkit.py run --outputs packages/eval-python/data/candidate.outputs.json --out /tmp/oweval-candidate
python packages/eval-python/evalkit.py compare /tmp/oweval-baseline/receipt.json /tmp/oweval-candidate/receipt.json --out /tmp/oweval-comparison.json
python -m unittest discover -s packages/eval-python/tests -v
```

Open `/tmp/oweval-comparison.html` for the comparison and `/tmp/oweval-candidate/review.html` for the reviewer desk. They work without a server, API key, network request, build step, or third-party JavaScript. Checked-in versions are also available at `demo/comparison.html`, `demo/baseline/review.html` and `demo/candidate/review.html`.

The baseline passes **20/25** cases. The candidate passes **21/25**, with **three improved cases and two new regressions**. Both automated gates remain blocked. A better aggregate result does not erase newly introduced failures. These counts describe deliberately authored fixtures only.

## What the checks actually measure

| Check | Implementation | Main limitation |
|---|---|---|
| Structure | Required fields, types, identity and no extra fields | A valid object can contain poor prose |
| Evidence | Exact reference fact, source ID and quotation match; duplicate detection | No semantic equivalence or clinical reasoning assessment |
| Completeness | Exact required fact and flag sets | Reference coverage can itself be incomplete |
| Policy | Scenario-specific fictional policy version | No legal interpretation or real guideline validation |
| Routing | Expected human-review or escalation route | Declared route does not prove an external action happened |
| Authority | Exact permitted action set and a narrow clearance-phrase scan | Declared actions and text are not a tool execution trace; phrase scans have false positives and negatives |

Any failure blocks the automated gate. There is no averaged score threshold that overrides a critical finding. The human review layer evaluates meaning, omissions and the adequacy of these criteria. It cannot erase a recorded automated failure: correct the output or explicitly revise/version the rubric and rerun.

## Evaluate imported model outputs

Export development prompts without reference answer objects:

```bash
python packages/eval-python/evalkit.py inputs --split development --out /tmp/oweval-inputs.json
```

Run these tasks in your own approved model environment. The export provides sources, task instructions and the response schema. Collect outputs into this envelope:

```json
{
  "synthetic": true,
  "metadata": {
    "kind": "model_output",
    "model": "record-the-exact-model-version",
    "prompt_version": "your-prompt-version",
    "tool_version": "your-tool-configuration-version"
  },
  "outputs": []
}
```

Place one complete output object per case in `outputs`, following `data/output.schema.json`. Then run with `--outputs your-file.json --split development --out your-run-directory`. Missing selected cases fail; unknown and duplicate IDs are rejected. `--fail-on-checks` returns exit code 1 when checks fail; malformed input returns 2. Without that flag, completed evaluation returns 0 even if findings block the gate.

Freeze development choices before exporting `--split holdout`. There are 15 development and 10 holdout cases. The published holdout is only a demonstration of separation, not a secret benchmark. A real engagement needs fresh protected cases, relevant population coverage, repeated trials for variable models, and sample-size planning appropriate to the claims.

This release imports model outputs; it does not invoke model providers or claim to compare live models.

## Independent review and adjudication

1. Send the same generated `review.html` to two reviewers through your chosen review process.
2. Each reviewer enters a distinct ID, assesses every case and downloads a review JSON file. Automated/reference findings begin hidden; revealing them is recorded. Browser drafts are convenience storage only; export completed reviews.
3. Reconcile the two files:

```bash
python packages/eval-python/evalkit.py reconcile /tmp/oweval-candidate/receipt.json reviewer-a.json reviewer-b.json --out /tmp/reconciliation.json
```

Every case requires a verdict (`pass`, `fail`, `uncertain`) and a rationale from both reviewers. Disagreement or either uncertain verdict requires adjudication by a third identifier. Provide:

```json
{
  "receipt_sha256": "copy-from-the-evaluated-receipt",
  "adjudicator_id": "reviewer-c",
  "decisions": [
    {"case_id": "C01", "verdict": "fail", "rationale": "Explain the relevant evidence and resolution."}
  ]
}
```

Rerun reconciliation with `--adjudications adjudications.json`. The output preserves both original reviews and adjudications, reports raw inter-reviewer agreement, unresolved cases and human-versus-automated disagreements. Raw agreement is descriptive, not proof of correctness or a chance-adjusted reliability statistic.

Reviewer identity is self-asserted. This local prototype does not provide authentication, enforced independence, access control, signatures or a shared audit service. A separate accountable decision remains necessary even when all checks and reviews pass.

## Evidence receipts and OpenWarrant

Each run exports version identifiers, full case results, model/prompt/tool metadata, content hashes, limitations, proposed scope and review triggers. Receipts always say `authorization.status: NOT_ISSUED`. Reconciliation can at most produce `READY_FOR_ACCOUNTABLE_REVIEW`.

This is a new evidence artifact, not an existing core `Warrant`, and the package does not write to the warrant store or automatically change trust levels. See [integration design](../../docs/evaluation/integration.md) for the proposed adapter boundary. SHA-256 hashes detect changes relative to a known digest; they do not authenticate an issuer or establish evidence truth.

## Files

- `evalkit.py`: runner, input exporter, comparison, reconciliation and report rendering.
- `reviewer.html`: offline reviewer desk template.
- `data/`: versioned rubric, scenario pack, output schema, reference and deliberately faulty fixtures.
- `demo/`: generated fixture reports and a comparison result.
- `tests/`: behavioral checks of gates, provenance, malformed inputs and review handling.
- [`docs/evaluation`](../../docs/evaluation/): workflow specification, commercial offer, integration roadmap and two articles.

Licensed under the repository's Apache-2.0 license. Intended for public synthetic demonstrations; do not use this unauthenticated reviewer desk for patient records.
