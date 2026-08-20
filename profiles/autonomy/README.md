# OpenWarrant Autonomy Profile (OWAP) v0.1

**Status:** Draft profile for public review  
**Parent project:** OpenWarrant  
**Purpose:** Express machine-readable authority for bounded autonomous and cyber-physical systems.

OWAP extends the OpenWarrant warrant primitive from software agents into autonomous systems that operate in physical or cyber-physical environments. It defines a portable authorization envelope binding a specific system identity and configuration to permitted actions, prohibited actions, operating limits, human-control requirements, evidence obligations, validity, revocation, and issuer signature.

> **Core proposition:** Evidence establishes what a system has demonstrated. A warrant states what it may do. A warrant-aware runtime enforces that authority at execution time and emits evidence of the decision.

OWAP is domain-neutral. The included reference example is deliberately non-kinetic: an autonomous drone performing critical-infrastructure inspection.

## Decision contract

A conformant runtime returns one of the standard OpenWarrant decisions:

- `AUTHORIZED` — action is inside the warrant and all conditions are satisfied.
- `DENIED` — a matching warrant exists, but the requested action violates an explicit bound or condition.
- `ESCALATE` — the request requires human review or approval.
- `NO_WARRANT` — no applicable warrant exists for the system/action context.
- `EXPIRED` — the applicable warrant is outside its validity period.

## Design principles

1. Authority is external to the autonomous system; the system MUST NOT self-issue or silently expand its warrant.
2. Authority binds to identity and configuration.
3. Outside the envelope, the default is no authority.
4. Human-control requirements are explicit and machine-readable.
5. Revocation is first-class.
6. Runtime decisions produce auditable evidence.
7. The profile is mission-neutral and can support additional domain-specific profiles.

## Core fields

- `issuer`: institutional authority and authority basis.
- `subject`: system identity, model, software version, and configuration digest.
- `authority`: mission class, permitted/prohibited actions, autonomy mode, and human-control requirements.
- `operating_envelope`: validity, geography, environmental and operational limits.
- `preconditions`: machine-evaluable conditions and their failure behavior.
- `evidence_requirements`: records required for audit and assurance.
- `escalation`: triggers, destination, and safe-state guidance.
- `revocation`: active/suspended/revoked state and optional endpoint.
- `signature`: algorithm, key identifier, and signature value.

## Warrant-aware runtime

A production implementation SHOULD evaluate, in fail-closed order:

1. profile applicability;
2. issuer trust and cryptographic signature;
3. revocation state and freshness;
4. system identity and authorized configuration;
5. warrant validity window;
6. action permission/prohibition;
7. operating-envelope limits;
8. preconditions;
9. human-approval requirements; and
10. evidence/audit obligations.

A system is **warrant-aware** when an applicable OpenWarrant decision is an upstream execution dependency and an unauthorized action cannot bypass that dependency through normal operation.

## Authority–Evidence Loop

```text
TEVV / evaluation evidence
          ↓
 demonstrated operating envelope
          ↓
     issued warrant
          ↓
  runtime authorization
          ↓
 autonomous operation
          ↓
 decision + outcome evidence
          ↓
 reassessment / renewal / restriction / revocation
```

**Evidence supports authority. Authority bounds autonomy. Operation generates additional evidence.**

## Security note

OWAP is an authorization format, not a complete safety, security, or legal architecture. A warrant MUST NOT be interpreted as proof that an autonomous capability is safe, effective, lawful, or fit for a mission. Production deployments must independently establish trusted issuers, signature verification, authenticated system identity, secure configuration attestation, revocation freshness, clock integrity, replay prevention, human-approval authenticity, audit integrity, and appropriate fail-safe behavior.
