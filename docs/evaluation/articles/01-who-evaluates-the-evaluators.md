# Who Evaluates the Evaluators?

Andrew Plummer, MD, MPH · Draft

A recent job posting for clinical AI reviewers caught my attention. The work included scoring model outputs, identifying safety issues, correcting reasoning, adjudicating disputed cases, and participating in regular reviewer calibration. [1]

That last responsibility deserves more attention.

We talk extensively about whether AI produces reliable answers. We should be equally curious about how reliably we judge those answers.

Consider a fictional case: two qualified clinicians review the same AI-generated summary. One considers it acceptable because every statement is accurate. The other flags it because an important omission could change how the next clinician interprets the record.

Both reviewers may be applying sound judgment. They may also be answering different questions.

Is the summary factually correct? Is it complete enough for its purpose? Does it preserve uncertainty? Does it help the intended user make the next decision safely?

Until we specify the task, “good” remains open to interpretation.

This is where evaluation becomes an organizational capability.

Expertise gives reviewers the ability to recognize consequential problems. A well-designed evaluation process makes their judgments explicit, comparable, and open to challenge.

That process needs a few things:

- **A defined use.** Who will rely on the output, for what task, under what conditions?
- **An evidence-based rubric.** What must be present, what is unacceptable, and which failures carry particular consequences?
- **Independent assessment.** Can reviewers reach their judgments before seeing someone else’s score?
- **Documented adjudication.** When reviewers disagree, what evidence resolves the disagreement—or establishes that uncertainty remains?
- **Reassessment.** How will we detect when the rubric, reviewers, or automated graders stop measuring what matters?

Agreement alone cannot establish correctness. Reviewers can share the same blind spot. An automated judge can consistently reward an answer that sounds persuasive while overlooking a critical omission.

NIST’s AI Risk Management Framework Playbook addresses this broader measurement problem: evaluation should reflect the context of use, examine the effectiveness of the measures themselves, and document risks that remain unmeasured. [2]

For leaders, the practical implication is straightforward. “A human reviewed it” should begin a conversation about the review process.

Who reviewed it? Against which standard? With what evidence? How were disagreements handled? What remains unresolved?

For clinicians and other domain experts, this is also an opportunity: turning professional judgment into reusable evaluation methods, test cases, and learning systems.

My view is that the quality of AI governance will depend substantially on the quality of the judgments it relies upon.

**If an evaluation can influence whether an AI system is trusted, that evaluation deserves scrutiny of its own.**

## Sources

1. [AuraOne Human Data: Regulatory, Privacy & Healthcare Law Reviewer — AI Evaluation](https://www.indeed.com/viewjob?jk=745ef73d22c07336). Posting inspected September 5, 2026. The cited claim concerns advertised duties.
2. [NIST AI RMF Playbook: Measure](https://airc.nist.gov/airmf-resources/playbook/measure/). Inspected September 5, 2026.
