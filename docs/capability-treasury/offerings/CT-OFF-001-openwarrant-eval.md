# OpenWarrant Eval
## Workflow Evaluation Sprint

**A Capability Treasury offering under InnerLearn · fCAIGO**

Offering ID: CT-OFF-001 | Version: 0.1.0 | Status: founding offer draft

**Know what your AI workflow can support, where it fails, and what decision the evidence justifies.**

## Who it serves

Healthcare AI program leads, clinical operations leaders and governance teams with one defined AI-assisted workflow approaching a pilot, expansion or material change. The engagement starts with a named decision owner and a practical question about permitted use.

Initial workflow: an assistant prepares a cited clinical review packet from records and policy documents for an authorized human reviewer. Adjacent workflows can be considered after their scope, evidence and review requirements are defined.

## The offer

A proposed ten-business-day engagement, beginning when scope, inputs and reviewer availability are confirmed. We define the workflow boundary and evaluation criteria, compare one baseline and one candidate configuration, document consequential findings and reviewer disagreements, and deliver an evidence packet with a remediation and retest plan.

The customer retains the accountable decision. A passing evaluation does not itself authorize use.

## Included scope

| Included | Boundary |
|---|---|
| One workflow | One intended-user group and one decision question |
| Evaluation protocol | Versioned criteria, critical failures, dependencies and review triggers |
| Initial scenario pack | Up to 25 development/demo scenarios; validation sample size and claims require separate agreement |
| Configuration comparison | One baseline and one candidate; repeated trials scoped for variable outputs |
| Expert review | Two customer-designated qualified reviewers and one designated adjudicator |
| Findings and evidence | Per-case results, regressions, rationale, disagreements, limitations and unsigned receipt |
| Readout and retest | One decision readout and one bounded retest within agreed scope |

## Deliverables

1. Workflow boundary and dependency map.
2. Versioned evaluation protocol and scenario inventory.
3. Baseline/candidate findings and regression comparison.
4. Independent review and adjudication record.
5. Evidence receipt linked to the tested versions and limitations.
6. Decision brief, proposed use restrictions, remediation plan and review triggers.

## Proposed commercial terms

**Founding sprint: $7,500 fixed fee**, with customer-provided reviewers and adjudicator. **Additional bounded retests: from $2,500**, separately scoped; the first in-scope retest is included in the sprint. These are proposed prices to validate, not approved customer terms or market benchmarks.

Expert recruitment, substantial integrations, protected-data infrastructure, formal clinical validation and broader scenario coverage are separately estimated. The current toolkit imports outputs produced in an approved model environment; it does not include a live-model adapter.

## Delivery sequence

| Days | Focus |
|---|---|
| 1-2 | Confirm decision, scope, sources, access and reviewers |
| 3-4 | Build and review scenarios and criteria |
| 5-6 | Evaluate baseline and candidate outputs |
| 7-8 | Independent review, calibration and adjudication |
| 9-10 | Findings readout, evidence packet and retest plan |

## What already exists

The OpenWarrant Eval engineering starter includes 25 synthetic cases, structured checks, an offline review desk, review reconciliation, change comparisons and evidence receipts. The fixture demo improves from 20/25 to 21/25 passes while introducing two regressions; both automatic gates remain blocked. The counts describe hand-authored fixtures, not measured model performance.

Local verification passed 16 evaluation tests, 55 Python core tests and 8 TypeScript core tests. Browser review and export flows were checked on desktop and mobile, and GitHub CI passed for the starter commit.

Expert validation of real workflows, a live-model adapter, institutional reviewer authentication and OpenWarrant Studio integration remain future work.

## Treasury assets supporting this offering

CT-CODE-001 OpenWarrant core; CT-CODE-002 Eval runner; CT-DATA-001 scenario pack; CT-METHOD-001 rubric/protocol; CT-UI-001 reviewer desk; CT-EVID-001 demo receipts; CT-CONTENT-001 and CT-CONTENT-002 articles; CT-PLAYBOOK-001 delivery/launch materials. CT-PLAN-001 describes the proposed Studio integration.

## Opening conversation

What decision is waiting on evidence? Who owns that decision? Which failures would change it? What is the assistant allowed to do? What configuration and evidence can we inspect? Who can review the outputs independently?

## Portfolio statement

Capability Treasury is the user-designated home for the reusable assets behind this offering. InnerLearn · fCAIGO is the portfolio umbrella. OpenWarrant remains the public engineering source. Existing open-source terms are preserved; this portfolio placement does not claim a change in legal ownership or exclusive rights.
