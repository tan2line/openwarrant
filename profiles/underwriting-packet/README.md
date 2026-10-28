# Agent Underwriting Packet — Profile v0.1

**Status:** draft profile · **Schema:** [`underwriting-packet.schema.json`](./underwriting-packet.schema.json) · **Example:** [`examples/claimsfollow-aic.packet.yaml`](./examples/claimsfollow-aic.packet.yaml)

A *profile* of OpenWarrant: a fixed, machine-readable shape for the evidence an underwriter, broker, board, or regulator needs before accepting the risk of an AI agent that takes consequential actions. It adds no new engine behavior. It defines what gets written down, how it is graded, and when it expires.

> A log tells you what the agent did. A receipt tells you what it was authorized to do, by whom, within what limits, and who answers when it goes wrong. This profile is the receipt, packaged for the party that has to price it.

## Why a profile and not a product

Carriers are excluding AI by default and insuring by exception, and the exception goes to the insured who can show the paper. Nobody has standardized the paper. A warrant already says what an agent may do; the audit chain already says what it did. The packet is the join between those two, plus the three things neither one records: what a failure would cost, who stops it, and whether any of this is still true after the next model swap.

The profile is deliberately read-only with respect to the agent. It consumes warrants, receipts, and exports. It never runs inside the agent's loop.

## The five sections

Each section answers one question an underwriter asks. Each is filled with **evidence items**, not prose. Where no evidence exists, the item says so and the row goes to the gap register.

| # | Section | The question | Filled from |
| --- | --- | --- | --- |
| 1 | `authorization_scope` | What is this agent allowed to do, and who granted it? | `warrant.what_they_can_do`, `warrant.under_what_conditions`, `warrant.issuer`, `warrant.valid_until` |
| 2 | `performance_evidence` | What shows it stays within those limits? | audit chain (`audit_hash` records), execution receipts, pre-deployment evaluation results |
| 3 | `blast_radius` | If it fails, what happens and how far does it travel? | failure scenarios, peak volume, downstream write targets, current detection time |
| 4 | `containment` | What stops it, and who is accountable? | kill switch, coded limits, `warrant.escalation_target`, `accountable_owner` (v0.2), human-approval actions |
| 5 | `change_cadence` | How is all of the above refreshed when things change? | change log, re-evaluation triggers, last re-evaluation, refresh cadence, version binding |

### Evidence items

```yaml
- type: signed_schedule      # document | report | query_result | signed_schedule | assertion | none
  ref: "warrants/claimsfollow-appeals-001.yaml"
  hash: "sha256:…"           # optional, recommended for documents and exports
  date: "2026-10-01"
  note: "Authorization schedule attached to formation documents."
```

`assertion` is allowed and is graded as such (see below). `none` is required when nothing exists; leaving a field blank is not the same as saying so.

## Grading

One letter per section, one overall.

| Grade | Meaning |
| --- | --- |
| **A** | Evidenced and current — every required item has a non-`assertion` evidence item dated within the stated refresh cadence |
| **B** | Evidenced but partial or stale — required items are evidenced, but at least one is older than the refresh cadence or incomplete |
| **C** | Asserted, not evidenced — at least one required item's best evidence is `assertion` |
| **D** | Unknown — at least one required item is `none` |

**Overall** is the lower of (a) the median of the five section grades and (b) the worse of sections 1 and 4. Authorization and containment are the sections a carrier reads first; a packet cannot grade above them.

Rule of thumb carried into the gap register: a **C or D in section 1 or 4 is uninsurable until fixed**.

## Gap register

Every `none` and every `assertion` becomes a row. Rows are ranked by how much a carrier would care, then by effort.

```yaml
- rank: 1
  gap: "No bounded authorization schedule"
  section: authorization_scope
  carrier_concern: "Cannot price an unbounded grant"
  fix: "Attach scope, limits, and exclusions to formation documents; reference from the log"
  effort: days            # days | weeks | months
  owner: "General Counsel"
  target_date: "2026-11-15"
```

## Attestation and expiry

The packet is bound to an **agent version**: model, tool set, permission set, workflow version. The attestation carries the packet hash, the grades, the three signatories (completed by, reviewed by, accountable human), an issue date, and a `valid_until` date. It **expires on the earlier of** `valid_until` and any change to the agent version. A packet written against last quarter's agent is already stale.

The completing role and the reviewing role stay separate. The reviewer grades; the deploying organization fills.

## Relationship to the rest of OpenWarrant

- The packet references warrants by `warrant.id`; it does not restate them.
- `performance_evidence.log_carries_warrant_ref` is the single most important boolean in the profile. If every audit record carries the warrant it executed under, the out-of-scope rate is a query. If not, it is a research project.
- `accountable_owner` and execution receipts (v0.2) populate sections 2 and 4 directly.
- Nothing in `packages/` changes. A validator for this schema may follow as an optional tool; it is not required to use the profile.

## Scope note

This profile is a surveyor's instrument. It is not an insurance product, coverage advice, or a certification. Grades describe the state of the evidence on the cover date, nothing more.

*Views my own; nothing here represents any employer or agency.*
