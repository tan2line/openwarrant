# OpenWarrant Eval integration and implementation roadmap

## Existing repository boundary

The inspected core exposes `Warrant`, `WarrantRequest`, `WarrantResponse`, `WarrantEngine`, structured constraints and lifecycle status. OpenWarrant Eval is an independent stdlib package in this repository. It does not modify the Python or TypeScript decision engines. Its evidence receipts are not accepted as runtime warrants.

## Implemented in this starter

1. Synthetic input export with response schema and development/holdout selection.
2. Imported-output evaluation against versioned structured expectations.
3. Offline review desk with rationale capture and JSON export.
4. Two-reviewer reconciliation, adjudication and descriptive agreement.
5. Per-check regressions and improvements for comparable runs.
6. Unsigned evidence receipts with content hashes, scope proposal, limitations and triggers.

## Proposed evidence-to-decision adapter

Store an evaluation receipt separately from an authority record. Link the authority decision to the receipt's digest, immutable location, workflow and dependency versions. Have the accountable human specify allowed actions, conditions and a review date. Only an authenticated issuer process may create or update a runtime warrant. Preserve evaluation failures and supersession history.

| Evaluation field | Proposed downstream use |
|---|---|
| `workflow_id` | Identify the specific task being considered |
| `receipt_sha256` and artifact location | Reference the evaluation evidence; not issuer authentication |
| model/prompt/tool metadata and pack/rubric hashes | Bind the decision to tested dependencies and criteria |
| critical failures and unresolved reviews | Prevent an automatic readiness claim; require resolution |
| permitted-use proposal and prohibited actions | Inputs for the human's scope decision |
| review triggers | Events that reopen the supporting decision |
| accountable decision record | Separate future record; never inferred from a score |

No compatibility with an OpenWarrant Studio database or API is claimed. Inspect that private repository and agree a shared schema before building an adapter.

## Next engineering milestones

**Live-model adapter:** import actual execution traces as well as outputs; retain exact model version, generation settings, retrieval configuration, prompt digest, timestamps, repeated trials, latency and cost. Credentials remain in the approved execution environment. This starter has no provider calls.

**Review service:** add authentication, independent assignment, server-side persistence, immutable review history, evidence access controls, adjudication roles and export verification. Browser storage is insufficient for an institutional review process.

**Expert-validated pack:** replace toy records and fictional policy with authorized, appropriately governed evidence. Validate clinical expectations and test population/subgroup coverage. Preserve a protected holdout and avoid reusing adjudicated development examples as validation evidence.

**Decision integration:** add an explicit versioned adapter to OpenWarrant Studio. Implement review triggers and authenticated issuance in the appropriate authority service. Test that passing evals never creates authorization implicitly.

## Acceptance for this milestone

One command produces reviewable results; a known regression survives an improved aggregate score; missing outputs fail; changed evidence is detectable; review files are bound to a specific receipt; uncertain/disputed cases cannot silently pass; no execution path issues authorization. The checked-in demo is explicitly labeled as hand-authored fixtures.
