# Evaluation content and capability launch kit

Draft assets for Andrew Plummer, MD, MPH. The two articles are approved-in-conversation drafts, not externally published posts. No outreach has been sent.

## The sequence

1. Publish **Who Evaluates the Evaluators?** to establish the evaluation-method problem. Invite readers to describe where reviewers disagree in their own workflows.
2. Share the public synthetic demo: a candidate improves from 20/25 to 21/25 while introducing two regressions. Label those counts as hand-authored fixture results, not model performance.
3. Publish **Your AI Passed the Test. What Did That Authorize?** to connect evaluation to scope, authority and review triggers.
4. Introduce the proposed Workflow Evaluation Sprint through buyer conversations, using one workflow and one decision as the entry point.

## Suggested bridge post

An AI workflow can improve its overall test result and still introduce a consequential new failure.

We built a small OpenWarrant Eval demonstration to make that visible. Its 25 synthetic scenarios test evidence handling, omissions, policy versions, routing and authority boundaries. In the hand-authored example, a candidate improves from 20 passing cases to 21. Three cases improve. Two regress. The evaluation remains blocked.

The package also captures independent reviewer judgments, preserves disagreements, and exports the evidence with its versions and limitations. Passing checks never issues authorization.

This is an engineering starter built with fictional records and policies. The next challenge is validating the protocol with domain experts and relevant workflow evidence.

What would your team need to see before allowing an AI assistant to take its next step?

## Demo talk track: five minutes

- **Minute 1:** Define packet preparation and the human's reserved decision.
- **Minute 2:** Inspect a source-bound output and the rubric; show that correct facts can coexist with an authority violation.
- **Minute 3:** Show baseline/candidate comparison: 20 to 21 passes, two new regressions.
- **Minute 4:** Enter an independent review, reveal findings, and explain adjudication and reviewer agreement limitations.
- **Minute 5:** Open the evidence receipt: versions, findings, proposed scope, triggers, and `NOT_ISSUED` authorization status.

## Publication accuracy checklist

Use the actual branch or merged-repository URL. Distinguish implemented features from the proposed Studio adapter. Call the test data synthetic and the checked-in outputs fixtures. Do not describe a comparison as a live-model benchmark. Do not imply certification, clinical validation, DHA endorsement, a paying customer, or partner agreement that has not been established.

## Sources used in the articles

- [AuraOne clinical reviewer posting on Indeed](https://www.indeed.com/viewjob?jk=745ef73d22c07336), inspected September 5, 2026. Evidence of the advertised responsibilities, not proof of available assignments or actual earnings.
- [AuraOne related evaluator role](https://auraone.ai/public/ai-labs/jobs/clinical-biomedical-pharma-evaluator-aoj-fc01e4c7ac14abdfad), inspected September 5, 2026. Notes placement dependence on program demand and reviewer confirmation.
- [NIST AI RMF Playbook: Measure](https://airc.nist.gov/airmf-resources/playbook/measure/), inspected September 5, 2026. Contextual measurement, limits, documentation and reassessment guidance; voluntary guidance, not a certification.
- [Anthropic: Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents), January 9, 2026. Additional engineering background; not an endorsement of this implementation.
