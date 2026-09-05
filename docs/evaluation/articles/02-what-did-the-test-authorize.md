# Your AI Passed the Test. What Did That Authorize?

Andrew Plummer, MD, MPH · Draft

“The AI passed evaluation.”

An encouraging sentence. It still leaves an essential question unanswered:

**What, precisely, does the evidence support allowing the system to do?**

Consider a fictional clinical workflow.

An AI assistant reads records and policy documents, identifies missing information, and prepares a review packet. An authorized clinician makes the final determination.

During testing, the assistant extracts the relevant facts, cites the correct policy, and produces a clear summary.

Then it adds: “Cleared to proceed.”

The answer may look polished. The underlying facts may be correct. But the assistant has moved from preparing evidence to issuing a determination.

An evaluation focused on extraction accuracy could miss that boundary crossing entirely.

This is why an evaluation needs to begin with a clear description of the system’s intended role. The criteria should address the actions it may take, the decisions reserved for people, and the conditions requiring it to stop or escalate.

A useful evaluation record should help a decision-maker answer:

- What task and operating conditions were tested?
- Which model, instructions, tools, and source documents were used?
- Which consequential failures were tested, and which remain uncertain?
- What restrictions or human review requirements does the evidence support?
- What changes would require a new assessment?

NIST’s guidance connects measurement to intended use, deployment context, acceptable performance limits, and continued assessment. These are the details that give a test result operational meaning. [1]

The distinction becomes especially important after a system changes.

A new model arrives. A policy document is revised. Another tool becomes available. Someone expands the workflow to a different population. A human review step is removed because the system “has been performing well.”

Each change raises a question about whether the earlier evidence still applies.

That is the problem behind a thesis I keep returning to: **your AI approval has a half-life.**

The approval may remain recorded while the assumptions supporting it gradually—or suddenly—lose their relevance.

I believe organizations need a practical record connecting evaluation evidence to an accountable decision. In the OpenWarrant concept, that record would identify the permitted use, supporting evidence, limitations, decision owner, and review triggers.

Creating the record would not itself grant permission. The authorized decision-maker would determine whether the evidence is sufficient and which conditions apply.

The benefit is traceability: when something changes, the organization can identify which decisions need another look.

For the fictional assistant, the supported scope might be narrow and useful: prepare a cited review packet, identify missing information, preserve uncertainty, and route the packet to the clinician.

**The practical unit of AI governance is a use, a dependency, an evidence requirement, an accountable decision, and a review trigger.**

A passing score becomes useful when we can explain what decision it supports—and where that support ends.

## Source

1. [NIST AI RMF Playbook: Measure](https://airc.nist.gov/airmf-resources/playbook/measure/). Inspected September 5, 2026. The fictional scenario and OpenWarrant proposal are the author's illustrations.
