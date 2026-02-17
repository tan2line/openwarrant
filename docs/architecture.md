# OpenWarrant: Architecture Specification v0.1

## An Open-Source Governance Runtime for AI Agents

**Author:** Andrew D. Plummer, MD, MPH  
**Date:** February 2026  
**Status:** Draft / Pre-Release  
**License:** Apache 2.0 (proposed)

---

## Executive Summary

OpenWarrant is an open-source, runtime-agnostic governance library that any AI agent can use. It does for agent governance what OpenClaw did for agent execution — makes it executable, composable, and free.

The core insight: **governance should not be an external constraint on agent skills. Governance should BE agent skills.** Warrant verification, credential checking, authority boundary enforcement, and audit logging are competencies, not restrictions. An agent with more governance skills is a more capable agent — one that can handle more sensitive tasks because it has the skills to handle them properly.

OpenWarrant provides the core library, schemas, CLI, and optional framework adapters that make this architectural pattern real. It has **zero opinions about your agent runtime** — it works from the command line, as a Python/TypeScript import, over HTTP, or inside any agent framework through thin adapters.

---

## Problem Statement

The AI agent ecosystem is exploding. OpenClaw reached 196,000 GitHub stars in twelve weeks. The agent market is projected at $180B by 2033. Every major tech company is building agent platforms.

But the entire regulated economy — healthcare, finance, insurance, government, critical infrastructure — is gated behind a trust problem that no current agent framework solves:

**How does an agent prove it had authority to act?**

Not just that it acted correctly. That it was *authorized* to act. That the authorization was valid at the time of execution. That the entire chain is auditable after the fact.

Current approaches fail in predictable ways:

| Approach | Failure Mode |
|----------|-------------|
| No governance (OpenClaw model) | Fast execution, no authorization checks, breaches are unreconstructable |
| External policy engine (bolt-on model) | Latency, scope gaps, bypassable in multi-step workflows, separate audit trails |
| Hardcoded rules (embedded model) | Brittle, not portable across institutions, can't adapt to context |

OpenWarrant proposes a fourth approach: **governance as native agent skills** — warrant-skills that are upstream dependencies in the agent's execution graph, externally authored but internally executed.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    AGENT RUNTIME                             │
│  (OpenClaw, LangChain, CrewAI, AutoGen, custom, etc.)       │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              SKILL EXECUTION GRAPH                    │   │
│  │                                                       │   │
│  │  [Warrant Skills] ──→ [Action Skills] ──→ [Output]   │   │
│  │   ↑ Authored        ↑ Existing agent     ↑ Governed  │   │
│  │   externally        capabilities          result      │   │
│  │                                                       │   │
│  └──────────────────────────────────────────────────────┘   │
│         ↑                        ↓                           │
│  ┌──────┴──────┐         ┌──────┴──────┐                    │
│  │  Warrant    │         │  Audit      │                    │
│  │  Store      │         │  Chain      │                    │
│  │  (local)    │         │  (local)    │                    │
│  └─────────────┘         └─────────────┘                    │
│         ↑                        ↓                           │
└─────────┼────────────────────────┼───────────────────────────┘
          │                        │
    ┌─────┴─────┐           ┌──────┴──────┐
    │ Warrant   │           │ Audit       │
    │ Authority │           │ Consumers   │
    │ (issuer)  │           │ (compliance)│
    └───────────┘           └─────────────┘
```

---

## Core Components

### 1. Warrant Engine

The lightweight runtime that agents call before executing sensitive actions.

#### Warrant Request Schema

```json
{
  "warrant_request": {
    "agent_id": "agent-uuid-001",
    "action": "send-patient-data",
    "target": "email:dr.chen@hospital.org",
    "context": {
      "patient_id": "pt-uuid-789",
      "data_classification": "PHI",
      "requester": "user-uuid-456",
      "requester_role": "attending_physician",
      "session_id": "sess-uuid-012"
    },
    "timestamp": "2026-02-16T14:30:00Z"
  }
}
```

#### Warrant Response Schema

```json
{
  "warrant_response": {
    "decision": "AUTHORIZED",
    "warrant_id": "wrt-uuid-345",
    "authority": {
      "issuer": "hospital-compliance-office",
      "warrant_type": "clinical-data-disclosure",
      "issued": "2026-01-01T00:00:00Z",
      "expires": "2026-12-31T23:59:59Z",
      "scope": ["PHI-disclosure", "treatment-context"]
    },
    "conditions": [
      {"type": "recipient-must-be-verified", "status": "MET"},
      {"type": "patient-consent-on-file", "status": "MET"},
      {"type": "disclosure-format-compliant", "status": "MET"}
    ],
    "audit_hash": "sha256:a1b2c3d4...",
    "trust_elevation": {
      "current_level": 1,
      "new_level": 2,
      "reason": "successful-governed-execution"
    }
  }
}
```

#### Decision Types

| Decision | Meaning | Agent Behavior |
|----------|---------|----------------|
| `AUTHORIZED` | All conditions met, warrant valid | Proceed with action |
| `DENIED` | Warrant exists but conditions not met | Do not proceed, log reason |
| `ESCALATE` | Requires human-in-the-loop approval | Pause, notify designated authority |
| `NO_WARRANT` | No applicable warrant found | Do not proceed, cannot act |
| `EXPIRED` | Warrant found but expired | Do not proceed, request renewal |

### 2. Warrant Authoring Kit

A schema and toolset for institutions to define warrants.

#### Warrant Definition Schema

```yaml
warrant:
  id: wrt-clinical-disclosure-001
  version: 2.1
  issuer:
    organization: "Memorial Hospital"
    authority: "Chief Compliance Officer"
    signature: "ed25519:base64..."
  
  scope:
    actions:
      - "read-patient-record"
      - "generate-clinical-summary"
      - "send-patient-data"
    data_classifications:
      - "PHI"
      - "clinical-notes"
    contexts:
      - "treatment"
      - "care-coordination"
  
  conditions:
    - type: "requester-role"
      allowed: ["attending_physician", "consulting_physician", "care_coordinator"]
    - type: "patient-consent"
      required: true
      consent_types: ["general-treatment", "specific-disclosure"]
    - type: "recipient-verification"
      required: true
      methods: ["NPI-lookup", "institutional-directory"]
    - type: "disclosure-format"
      required: true
      templates: ["standard-clinical-summary", "referral-brief"]
  
  validity:
    issued: "2026-01-01T00:00:00Z"
    expires: "2026-12-31T23:59:59Z"
    renewable: true
    revocable: true
    revocation_authority: "compliance-office"
  
  audit:
    required: true
    retention_days: 2555  # 7 years per HIPAA
    tamper_evidence: "merkle-tree"
    fields:
      - "requester_id"
      - "patient_id"
      - "action"
      - "decision"
      - "timestamp"
      - "conditions_evaluated"
  
  trust_escalation:
    on_success:
      consecutive_required: 5
      elevation: "+1 trust level"
    on_failure:
      action: "revoke-and-review"
      notification: "compliance-office"
```

#### Domain Templates

OpenWarrant ships with starter warrant templates for common regulated domains:

| Domain | Template | Key Warrants |
|--------|----------|-------------|
| **Healthcare** | `healthcare-hipaa-v1` | PHI disclosure, clinical decision support, medication ordering, referral management |
| **Insurance** | `insurance-claims-v1` | Claimant verification, coverage validation, fraud-flag checks, adjuster authority, policyholder consent |
| **Finance** | `finance-fiduciary-v1` | Trade execution, suitability assessment, AML checks, client data handling |
| **Government** | `govcloud-fedramp-v1` | PII handling, FOIA compliance, records management, inter-agency sharing |
| **General** | `base-v1` | Email sending, file access, API calls, data export |

### 3. Skill Governance Registry

Maps skills to required warrant levels. Community-maintained, open-source.

#### Registry Entry Schema

```yaml
skill_governance:
  skill_id: "send-email"
  skill_name: "Send Email"
  
  warrant_requirements:
    - context: "general"
      warrant_level: "basic"
      required_warrants: ["verify-sender-authority"]
    
    - context: "contains-PHI"
      warrant_level: "clinical"
      required_warrants:
        - "verify-requester-auth"
        - "validate-patient-consent"
        - "confirm-recipient-credentials"
        - "check-disclosure-format"
        - "audit-log-access"
    
    - context: "contains-claims-data"
      warrant_level: "insurance"
      required_warrants:
        - "verify-adjuster-authority"
        - "validate-claimant-identity"
        - "check-coverage-status"
        - "verify-fraud-flags"
        - "audit-claims-chain"
  
  data_classification_triggers:
    PHI: "clinical"
    PII: "privacy"
    claims: "insurance"
    financial: "fiduciary"
    general: "basic"
```

#### Registry Governance

The Skill Governance Registry itself follows open-source governance:

- **Contributions** via pull request with review by domain experts
- **Domain maintainers** for healthcare, finance, insurance, government
- **Versioned releases** with semantic versioning
- **Backward compatibility** guarantees for minor versions
- **Breaking changes** require major version bump and migration guide

### 4. Audit Chain

Every warrant check produces a tamper-evident record.

#### Audit Record Schema

```json
{
  "audit_record": {
    "record_id": "aud-uuid-678",
    "timestamp": "2026-02-16T14:30:00.123Z",
    "agent_id": "agent-uuid-001",
    "warrant_id": "wrt-uuid-345",
    "action": "send-patient-data",
    "decision": "AUTHORIZED",
    "conditions_evaluated": [
      {"condition": "requester-role", "result": "MET", "detail": "attending_physician"},
      {"condition": "patient-consent", "result": "MET", "detail": "general-treatment, exp:2027-01-15"},
      {"condition": "recipient-verification", "result": "MET", "detail": "NPI:1234567890 verified"},
      {"condition": "disclosure-format", "result": "MET", "detail": "standard-clinical-summary"}
    ],
    "execution_result": "SUCCESS",
    "previous_hash": "sha256:prev_hash...",
    "record_hash": "sha256:this_hash..."
  }
}
```

#### Tamper Evidence

Audit records are hash-chained using Merkle trees:

```
Record N hash = SHA-256(Record N content + Record N-1 hash)
```

This provides:
- **Tamper detection**: Any modification to a historical record breaks the chain
- **Non-repudiation**: The agent can prove what it was authorized to do
- **Reconstructability**: The full decision history can be replayed
- **No blockchain required**: Simple hash chains, stored locally, verifiable by any auditor

### 5. Core Library + Framework Adapters

OpenWarrant's core library has **zero agent framework dependencies.** It works standalone — from the CLI, as a Python/TypeScript import, or over HTTP. Framework adapters are thin, optional wrappers (~50 lines each) that translate OpenWarrant concepts into framework-native idioms.

#### Core Library (standalone, zero dependencies)

```python
from openwarrant import WarrantEngine, AuditChain

# Works without any agent framework
engine = WarrantEngine(warrant_store="./warrants/")
audit = AuditChain(store="./audit/")

# Check a warrant directly
result = engine.check(
    action="send-patient-data",
    requester_role="attending_physician",
    data_type="PHI",
    context={"patient_consent": True, "recipient_npi": "1234567890"}
)

# result.decision → AUTHORIZED | DENIED | ESCALATE | NO_WARRANT | EXPIRED
audit.record(result)
```

```bash
# Or from the command line — no Python required in your agent
openwarrant check \
  --action "send-patient-data" \
  --role "attending_physician" \
  --context '{"patient_consent": true}' \
  --format json
```

#### Adapter Example: LangChain (~50 lines)

```python
from openwarrant import WarrantEngine, AuditChain
from openwarrant.adapters.langchain import WarrantSkill  # Optional adapter

engine = WarrantEngine(warrant_store="./warrants/")
audit = AuditChain(store="./audit/")

# Wraps engine.check() as a LangChain Tool
verify_auth = WarrantSkill(
    name="verify-requester-auth",
    engine=engine,
    audit=audit,
    description="Verify the requesting user has authority for this action"
)

# Use like any other LangChain tool
agent = initialize_agent(
    tools=[verify_auth, validate_consent, read_labs, summarize, send_email],
    skill_dependencies={
        "read_labs": ["verify_auth", "validate_consent"],
        "send_email": ["verify_auth", "confirm_recipient"]
    }
)
```

#### Adapter Example: TypeScript / OpenClaw (~50 lines)

```typescript
import { WarrantEngine, AuditChain } from '@openwarrant/core';

const engine = new WarrantEngine({ warrantStore: './warrants/' });
const audit = new AuditChain({ store: './audit/' });

// Standalone check — works without OpenClaw
const result = await engine.check({
  action: 'send-patient-data',
  requester: { role: 'attending_physician' },
  target: { dataType: 'PHI' }
});

// Or wrap as an OpenClaw skill via optional adapter
import { toOpenClawSkill } from '@openwarrant/adapter-openclaw';

const verifyAuth = toOpenClawSkill(engine, audit, {
  name: 'verify-requester-auth',
  upstream_of: ['read-labs', 'send-email']
});
```

#### Skill Dependency Graph (core feature)

The core library enforces that governance skills run *before* their dependent action skills:

```
[verify-requester-auth] ──┐
                          ├──→ [read-labs] ──→ [summarize] ──→ [send-email]
[validate-patient-consent]┘          ↑                              ↑
                                     │                              │
                          [check-disclosure-format]    [confirm-recipient-creds]
                                                                    │
                                                        [audit-log-access]
```

If a governance skill returns `DENIED` or `NO_WARRANT`, the downstream action skills never execute. The agent doesn't experience this as a block — it experiences it as "I don't have the prerequisite outputs to proceed."

---

## Trust Escalation Model

A key innovation: governed execution *builds trust over time*. Agents that consistently execute governance skills correctly earn elevated trust levels that unlock more sensitive capabilities.

| Trust Level | Capabilities | How Earned |
|-------------|-------------|-----------|
| **Level 0: Unverified** | General tasks only, no sensitive data | Default for new agents |
| **Level 1: Basic** | Can handle PII with standard warrants | 10 consecutive governed executions |
| **Level 2: Clinical/Financial** | Can handle PHI, execute trades | 50 governed executions + 0 incidents |
| **Level 3: Autonomous** | Can execute without human-in-loop for routine governed tasks | 200 governed executions + institutional certification |
| **Level 4: Supervisory** | Can oversee Level 0-2 agents | Institutional grant + audit review |

Trust is:
- **Earned incrementally** through demonstrated governed behavior
- **Revoked instantly** on any governance failure
- **Non-transferable** between agents
- **Auditable** — the full trust history is part of the audit chain

---

## Deployment Model

### Self-Hosted (Primary)

OpenWarrant runs locally alongside the agent. No cloud dependency. No data leaves the device unless explicitly transmitted by an authorized action.

```
User's Device
├── Agent Runtime (any framework, or none)
├── OpenWarrant Core (local library, zero dependencies)
├── Warrant Store (local, signed warrants)
├── Audit Chain (local, hash-linked)
└── Governance Skills (local, registered)
```

### Institutional (Enterprise)

Organizations can run a central warrant authority that issues signed warrants to distributed agents:

```
Institutional Warrant Authority
├── Warrant Authoring & Signing
├── Warrant Distribution (to agent instances)
├── Audit Aggregation (from agent instances)
├── Trust Level Management
└── Revocation Registry
```

### Hybrid

Agents run locally with local warrant stores, but can check a remote revocation registry and receive warrant updates from institutional authorities.

---

## Security Model

### What the Agent CAN Do
- Execute warrant-skills as part of its workflow
- Inspect warrant metadata (issuer, expiry, scope)
- Refuse to act on expired or out-of-scope warrants
- Log all warrant decisions to the audit chain

### What the Agent CANNOT Do
- Author new warrants
- Modify existing warrants
- Tamper with the audit chain
- Elevate its own trust level
- Bypass skill dependencies

### Cryptographic Guarantees
- Warrants are **Ed25519 signed** by issuing authorities
- Audit records are **SHA-256 hash-chained**
- Warrant stores accept only **signed warrants from registered authorities**
- Trust elevations require **countersignature from institutional authority**

---

## Comparison with Existing Approaches

| Feature | No Governance | External Policy Engine | Hardcoded Rules | OpenWarrant |
|---------|--------------|----------------------|----------------|-------------|
| Execution speed | ✅ Fast | ❌ Latency | ✅ Fast | ✅ Fast (local) |
| Audit completeness | ❌ None | ⚠️ Partial | ⚠️ Partial | ✅ Full chain |
| Bypass resistance | ❌ None | ⚠️ Route-around | ✅ Hard to bypass | ✅ Dependency graph |
| Portability | ✅ Any agent | ⚠️ Vendor-specific | ❌ Custom per agent | ✅ Zero-dependency core, optional adapters |
| Institutional control | ❌ None | ✅ Centralized | ⚠️ Developer-controlled | ✅ Signed warrants |
| Trust building | ❌ None | ❌ None | ❌ None | ✅ Escalation model |
| Privacy | ✅ Local | ❌ Cloud dependency | ✅ Local | ✅ Local-first |
| Open source | Varies | ❌ Usually proprietary | N/A | ✅ Apache 2.0 |

---

## Roadmap

### Phase 1: Foundation (Q1 2026)
- [ ] Warrant schema specification (YAML/JSON)
- [ ] Core library — zero dependencies (Python + TypeScript)
- [ ] CLI tool (`openwarrant check`, `openwarrant audit`, `openwarrant init`)
- [ ] Audit chain implementation
- [ ] Healthcare warrant template (HIPAA)
- [ ] Simulation artifact (demonstration)
- [ ] GitHub repository + Apache 2.0 license

### Phase 2: Ecosystem (Q2 2026)
- [ ] First framework adapters (LangChain, OpenClaw — ~50 lines each)
- [ ] CrewAI / AutoGen adapters
- [ ] HTTP sidecar mode (for non-Python/TypeScript agents)
- [ ] Insurance warrant template (claims processing)
- [ ] Finance warrant template (fiduciary)
- [ ] Skill Governance Registry v1
- [ ] Trust escalation engine
- [ ] CLI tools for warrant authoring

### Phase 3: Scale (Q3-Q4 2026)
- [ ] Institutional warrant authority server
- [ ] Warrant distribution protocol
- [ ] Audit aggregation and reporting
- [ ] Compliance report generators (HIPAA, SOC2, FedRAMP)
- [ ] OpenWarrant Foundation governance model
- [ ] Community contributor program
- [ ] Reference implementations for 3 regulated industries

### Phase 4: Platform (2027)
- [ ] Agent-to-agent warrant delegation
- [ ] Multi-agent governance orchestration
- [ ] Real-time governance dashboards
- [ ] Integration with FDA TEMPO, CMS ACCESS
- [ ] Certification program for governed agents
- [ ] Enterprise support tier

---

## Why Open Source

The same logic that made OpenClaw's open-source model its primary competitive advantage applies to governance:

1. **Trust requires transparency.** No institution will trust a proprietary black box to govern its AI agents. Open source means the governance logic is auditable by anyone.

2. **Standards require community.** Governance schemas for healthcare differ from finance differ from insurance. The only way to build comprehensive coverage is community contribution from domain experts.

3. **Adoption requires zero friction.** If governance has a licensing fee, agents will route around it. If it's free and open, it becomes the default.

4. **Strategic value compounds.** OpenClaw's 196,000 stars are worth more than any paid marketing. OpenWarrant's adoption metrics will demonstrate market demand to the same companies racing to build agent platforms.

The code is free. The strategic position is priceless.

---

## Call to Action

OpenWarrant needs:

- **Domain experts** in healthcare, finance, insurance, and government to author warrant templates
- **Agent framework developers** to build adapters for their platforms
- **Security researchers** to audit the cryptographic model
- **Institutional partners** willing to pilot governed agents in regulated environments
- **Open-source contributors** to build the runtime, registry, and tooling

The agent revolution is here. The governance revolution is next.

**Skills are the new UI. Warrants are the new skills.**

---

*OpenWarrant is a project of the Governed Agency initiative. Contact: [TBD]*

*This specification is released under Creative Commons Attribution 4.0 International (CC BY 4.0).*
