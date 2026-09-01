# OpenWarrant Capability Warrant Profile v0.1

> **Status:** Draft for implementation and design-partner feedback  
> **Profile ID:** `openwarrant.capability/0.1`  
> **Extends:** OpenWarrant warrant schema v0.1  
> **Intent:** Bind execution authority to demonstrated capability, supporting evidence, a specific governed configuration, and an operating envelope.

## 1. Purpose

OpenWarrant answers a runtime question:

> **What authority does this system have right now, for this action, in this context?**

The Capability Warrant Profile extends that question upstream:

> **What evidence justifies that authority for this specific capability and configuration, and does that evidence still apply now?**

A Capability Warrant is a machine-readable OpenWarrant authorization that binds:

1. a **governed system configuration**,
2. one or more **capability claims**,
3. the **capability evidence** supporting those claims,
4. an **operating envelope** within which the claims were evaluated,
5. the base OpenWarrant **execution authority**, and
6. **change and reauthorization rules** that determine when authority must be reviewed, constrained, suspended, or renewed.

The profile is designed for dynamic systems whose effective capability can change because of model updates, tool or MCP additions, firmware, hardware, autonomy level, skill acquisition, policy changes, runtime changes, or operating-environment changes.

The core principle is:

> **Dynamic capability requires dynamic, evidence-backed authority.**

A useful mental model is:

- **CAN DO** — the system's technical capability envelope.
- **EVIDENCE SUPPORTS** — the portion of that envelope supported by evaluation evidence.
- **AUTHORIZED TO DO** — the portion currently permitted by a warrant.

A conformant implementation SHOULD make differences among these three states visible and auditable.

---

## 2. Relationship to Base OpenWarrant

This profile is **additive**. It does not replace the existing OpenWarrant warrant model or decision semantics.

The base warrant remains authoritative for:

- issuer and issuer role,
- identity / role scope,
- permitted actions and data types,
- validity window,
- context constraints,
- trust level,
- escalation target,
- signature,
- audit requirements, and
- runtime `AUTHORIZED`, `DENIED`, `ESCALATE`, `NO_WARRANT`, and `EXPIRED` decisions.

A Capability Warrant adds a `profiles` declaration and a `capability_assurance` object.

Existing warrants without this profile MUST continue to evaluate exactly as they do today.

A runtime that does not understand this profile MUST NOT silently treat a profile-bearing warrant as an ordinary warrant when the requested action depends on capability assurance. Such a runtime SHOULD fail closed or route to an explicitly configured compatibility policy.

---

## 3. Terminology

### 3.1 Capability
A capability is an action or class of actions a system can technically perform, such as `email.send`, `robot.pick`, `trade.execute`, `cds.recommend.medication`, or `vehicle.navigate`.

### 3.2 Capability Claim
A capability claim is a bounded assertion that a specific governed configuration can perform a capability under stated conditions.

Example:

> Configuration `CFG-A184` can perform `email.draft` using approved enterprise data sources with no external transmission.

A claim is not authority by itself.

### 3.3 Capability Evidence
Capability evidence supports a claim about what a system can reliably or acceptably do. Examples include:

- benchmark results,
- simulation results,
- red-team evaluations,
- hardware-in-the-loop tests,
- field trials,
- clinical validation,
- safety testing,
- human-performance evaluation,
- formal verification,
- conformance tests, or
- signed evaluator attestations.

Capability evidence exists **before or independently of** an authorization decision.

### 3.4 Authorization Evidence
Authorization evidence records what OpenWarrant decided at runtime: who requested an action, which warrant applied, which conditions were evaluated, whether the request was allowed, and the resulting evidence/receipt chain.

**Capability evidence answers:** *Why do we believe the system can do this within these bounds?*  
**Authorization evidence answers:** *Why was this specific action allowed or denied at this moment?*

These evidence classes MUST remain distinguishable.

### 3.5 Governed Configuration
The governed configuration is the subset of system configuration considered material to capability assurance and authorization.

It MAY include:

- model/provider/version,
- system prompt or policy bundle,
- tools,
- MCP servers,
- skills,
- retrieval/data sources,
- runtime and agent framework,
- autonomy level,
- hardware or embodiment,
- firmware,
- sensors,
- safety controller,
- deployment target,
- environment assumptions, and
- other domain-specific components.

The governed configuration is not required to contain every implementation detail. It MUST contain every component declared material by the warrant issuer or referenced capability evidence.

### 3.6 Configuration Fingerprint
A configuration fingerprint is a cryptographic digest of the governed configuration manifest. It allows a runtime to determine whether the system requesting authority is the configuration that was evaluated and warranted.

### 3.7 Operating Envelope
The operating envelope defines the conditions under which capability evidence and authority apply. Examples include geography, clinical setting, patient population, terrain, network state, environmental ranges, maximum transaction size, autonomy mode, data classification, or required human supervision.

### 3.8 Capability Warrant
A Capability Warrant is a base OpenWarrant warrant carrying the `openwarrant.capability/0.1` profile and a valid `capability_assurance` object.

---

## 4. Profile Activation

A warrant activates this profile by including:

```yaml
profiles:
  - openwarrant.capability/0.1
```

and:

```yaml
capability_assurance:
  ...
```

If `openwarrant.capability/0.1` is declared, `capability_assurance` MUST be present.

---

## 5. Capability Assurance Object

The v0.1 object has seven primary sections:

```yaml
capability_assurance:
  configuration: {}
  claims: []
  evidence: []
  operating_envelope: {}
  change_triggers: []
  reauthorization: {}
  telemetry_requirements: []
```

### 5.1 `configuration`

Required fields:

- `fingerprint_algorithm` — MUST be `sha256` in v0.1.
- `fingerprint` — lowercase hexadecimal SHA-256 digest of the canonical governed manifest.
- `manifest` — governance-relevant configuration object used to compute the fingerprint.

Recommended manifest fields:

```yaml
configuration:
  fingerprint_algorithm: sha256
  fingerprint: "<64 lowercase hex characters>"
  manifest:
    model:
      provider: openai
      name: example-model
      version: "2026-09-01"
    tools:
      - search.enterprise
      - email.draft
    mcp_servers: []
    autonomy_level: L1
    runtime:
      name: custom-agent
      version: "1.4.2"
```

Implementations MAY add domain-specific manifest keys.

### 5.2 `claims`

`claims` MUST contain at least one capability claim.

Each claim contains:

- `id` — unique claim identifier within the warrant.
- `capability` — canonical action/capability name.
- `statement` — human-readable bounded assertion.
- `evidence_refs` — one or more capability evidence IDs.
- `conditions` — optional claim-specific conditions.
- `valid_until` — optional evidence/claim expiry independent of warrant expiry.

Example:

```yaml
claims:
  - id: claim-email-draft-001
    capability: email.draft
    statement: "May draft internal email using approved enterprise sources."
    evidence_refs:
      - EVC-20260901-agent-eval-01
    conditions:
      external_send: false
```

A claim MUST NOT be interpreted as authority unless the base warrant also permits the requested action.

### 5.3 `evidence`

The warrant MAY embed compact evidence metadata or reference an external evidence registry.

Each evidence entry SHOULD contain:

- `id` — stable evidence identifier.
- `type` — evidence category.
- `source` — evaluator, lab, harness, authority, or system that produced it.
- `artifact_uri` — optional locator for the underlying artifact.
- `artifact_hash` — digest of the underlying evidence artifact when available.
- `evaluated_at` — timestamp.
- `valid_until` — optional expiry.
- `configuration_fingerprint` — configuration against which the evidence was generated.
- `result` — `pass`, `conditional`, or `fail`.
- `summary` — concise human-readable result.

Example:

```yaml
evidence:
  - id: EVC-20260901-agent-eval-01
    type: agent_tool_evaluation
    source: OpenWarrant Studio Evaluation Harness
    artifact_uri: "ow://evidence/EVC-20260901-agent-eval-01"
    artifact_hash: "sha256:<digest>"
    evaluated_at: "2026-09-01T12:00:00Z"
    configuration_fingerprint: "<same fingerprint as configuration>"
    result: pass
    summary: "Draft tool allowed; external send unavailable during evaluated configuration."
```

A `fail` evidence item MUST NOT satisfy a claim.

### 5.4 `operating_envelope`

The operating envelope is a map of bounded conditions under which the capability claims are considered applicable.

Examples:

```yaml
operating_envelope:
  network: enterprise
  data_classification:
    - internal
  human_supervision: required
  geography:
    - US
```

or for a physical system:

```yaml
operating_envelope:
  terrain:
    - indoor_flat
  temperature_c:
    min: 5
    max: 35
  payload_kg:
    max: 12
  autonomy_level:
    - L1
    - L2
```

The runtime or domain adapter MUST be able to evaluate each field used for authorization. Unknown required envelope conditions MUST fail closed.

### 5.5 `change_triggers`

Change triggers declare configuration or environment changes that affect evidence applicability or authority.

Each trigger contains:

- `path` — dotted path into the governed configuration or context.
- `materiality` — `critical`, `review`, or `informational`.
- `effect` — one of `suspend_affected_authority`, `require_review`, `record_only`.
- `reason` — human-readable explanation.

Example:

```yaml
change_triggers:
  - path: manifest.model.version
    materiality: critical
    effect: suspend_affected_authority
    reason: "Model version was part of the evaluated configuration."

  - path: manifest.tools
    materiality: critical
    effect: suspend_affected_authority
    reason: "Tool additions can expand the action surface."

  - path: context.request_volume
    materiality: informational
    effect: record_only
    reason: "Volume changes are monitored but do not invalidate evidence in v0.1."
```

If no explicit trigger matches but the configuration fingerprint changes, the default reauthorization policy applies.

### 5.6 `reauthorization`

Required fields:

- `on_fingerprint_change`
- `on_evidence_expiry`
- `allow_unaffected_claims`

Allowed actions in v0.1:

- `suspend_affected_authority`
- `require_review`
- `deny`

Example:

```yaml
reauthorization:
  on_fingerprint_change: suspend_affected_authority
  on_evidence_expiry: suspend_affected_authority
  allow_unaffected_claims: true
  review_target: "ai-assurance-board"
```

### 5.7 `telemetry_requirements`

Optional list of post-authorization monitoring requirements.

Example:

```yaml
telemetry_requirements:
  - metric: unauthorized_tool_attempts
    condition: "> 0"
    effect: require_review
  - metric: tool_error_rate
    condition: "> 0.05 over 100 actions"
    effect: require_review
```

Telemetry may trigger reassessment but MUST NOT automatically expand authority.

---

## 6. Canonical Configuration Fingerprint

For v0.1, the fingerprint MUST be computed as follows:

1. Select the `configuration.manifest` object.
2. Serialize using canonical JSON:
   - UTF-8,
   - object keys sorted lexicographically,
   - no insignificant whitespace,
   - JSON primitive values preserved,
   - arrays preserved in declared order unless a field-specific canonicalization rule states otherwise.
3. Compute SHA-256 over the resulting bytes.
4. Encode as lowercase hexadecimal.

The resulting digest is `configuration.fingerprint`.

The issuer SHOULD define stable ordering rules for semantically unordered arrays such as tool sets. A future profile version may normatively adopt a standard JSON canonicalization scheme.

A runtime MUST recompute or independently verify the current governed configuration fingerprint before relying on fingerprint-bound capability evidence.

---

## 7. Extended Runtime Evaluation Algorithm

When evaluating a Capability Warrant, a conformant runtime performs the existing OpenWarrant evaluation and the following profile checks.

Recommended order:

1. **Base warrant checks** — identity, status, validity, action, role, data type, context, trust level, signature, and other existing constraints.
2. **Profile support** — runtime recognizes `openwarrant.capability/0.1`.
3. **Current configuration present** — the requester provides or the runtime can derive the current governed configuration/fingerprint.
4. **Fingerprint match** — current fingerprint matches the warranted configuration unless an explicitly permitted compatibility rule applies.
5. **Capability claim exists** — at least one active claim covers the requested capability/action.
6. **Evidence coverage** — all evidence required by that claim exists, is not failed, is not expired, and was generated for the applicable configuration.
7. **Operating envelope** — current context is inside the evaluated envelope.
8. **Reauthorization state** — affected authority is not suspended or pending required review.
9. **Base authority** — the requested action remains permitted by the warrant.
10. **Decision + evidence** — return the normal OpenWarrant decision and emit authorization evidence containing the applicable capability claim, evidence refs, and configuration fingerprint.

The profile MUST NOT introduce probabilistic authorization decisions. Evaluation remains deterministic given the same warrant, configuration, evidence state, and context.

---

## 8. Profile Reason Codes

Implementations SHOULD add the following reason codes while preserving the base OpenWarrant decision types:

- `capability_profile_unsupported`
- `capability_fingerprint_missing`
- `capability_configuration_mismatch`
- `capability_claim_missing`
- `capability_evidence_missing`
- `capability_evidence_failed`
- `capability_evidence_expired`
- `capability_evidence_configuration_mismatch`
- `operating_envelope_violation`
- `reauthorization_required`
- `capability_authority_suspended`

In v0.1 these reason codes normally map to `DENIED` or `ESCALATE` according to the warrant's reauthorization policy.

---

## 9. Capability Assurance State

Studio/control-plane implementations SHOULD expose a capability assurance state independent of the base warrant lifecycle:

- `PENDING_EVALUATION` — no sufficient evidence yet.
- `VALID` — required evidence applies to the current configuration and envelope.
- `CONDITIONAL` — authority remains available only under explicitly stated conditions.
- `REVIEW_REQUIRED` — a material change or evidence condition requires human/institutional review.
- `SUSPENDED` — affected capability authority is unavailable pending re-evaluation/reauthorization.
- `REVOKED` — capability authority has been affirmatively withdrawn.
- `EXPIRED` — supporting evidence or capability authorization has passed its validity period.

Recommended transition pattern:

```text
PENDING_EVALUATION
      ↓
    VALID
      ↓
  CONDITIONAL
      ↓
REVIEW_REQUIRED
      ↓
  SUSPENDED
      ↓
REAUTHORIZED → VALID
```

A state transition MUST NOT grant broader authority without an institutionally authorized warrant issuance or update.

---

## 10. Required Authorization Evidence Extensions

For a Capability Warrant decision, the authorization evidence event SHOULD additionally record:

- `configuration_fingerprint`
- `capability_claim_id`
- `capability_evidence_refs`
- `capability_assurance_state`
- `operating_envelope_hash` or equivalent bounded context reference
- `change_event_id` when the decision follows a detected material change

Raw capability evidence does not need to be copied into every authorization receipt. Stable references and cryptographic hashes are preferred.

---

## 11. Example: Agent Tool Expansion

Initial governed configuration:

```yaml
manifest:
  model:
    provider: openai
    name: example-model
    version: "1"
  tools:
    - search.enterprise
    - email.draft
  mcp_servers: []
  autonomy_level: L1
```

Capability evidence supports `search.enterprise` and `email.draft`. The base warrant permits both actions but does not permit external email transmission.

A new MCP server is added:

```yaml
mcp_servers:
  - external-messaging
```

The canonical fingerprint changes.

If `manifest.mcp_servers` is a critical change trigger, the runtime/control plane MUST mark affected claims `REVIEW_REQUIRED` or `SUSPENDED` according to policy. The newly exposed capability MUST NOT inherit authority merely because the pre-change agent was authorized.

Expected user-facing result:

```text
CAPABILITY CONFIGURATION CHANGED

Previous fingerprint: CFG-7F92...
Current fingerprint:  CFG-A184...

Evidence coverage: incomplete for current configuration
Affected capability: external messaging
Authority status: SUSPENDED PENDING RE-EVALUATION
Reason: capability_configuration_mismatch
```

This is the reference vertical slice for Capability Warrant Profile v0.1.

---

## 12. Security and Privacy

1. Warrants SHOULD reference capability evidence by stable identifier and digest rather than embedding sensitive raw artifacts.
2. Configuration manifests SHOULD contain only governance-relevant configuration and SHOULD avoid secrets, credentials, raw prompts containing sensitive data, or proprietary weights.
3. Evidence stores SHOULD be append-only or tamper-evident.
4. A system MUST NOT self-issue broader authority as a result of learning, tool acquisition, telemetry, successful operation, or capability expansion.
5. Model-generated assertions about capability MUST NOT count as sufficient capability evidence unless the warrant explicitly identifies that evaluation method as acceptable and an accountable issuer adopts the result.
6. Missing configuration, evidence, or envelope data required by the profile MUST fail closed.

---

## 13. Conformance Requirements

A v0.1 conformant implementation MUST:

1. Parse warrants declaring `openwarrant.capability/0.1`.
2. Validate required `capability_assurance` fields.
3. Deterministically compute or verify the governed configuration fingerprint.
4. Prevent authority from silently carrying across a material fingerprint change.
5. Bind capability claims to capability evidence.
6. Distinguish capability evidence from authorization evidence.
7. Evaluate operating-envelope constraints before execution.
8. Apply reauthorization policy after material change or evidence expiry.
9. Emit profile-specific reason codes on denial/escalation.
10. Preserve all existing OpenWarrant fail-closed, human-anchored, auditable execution guarantees.

Recommended language-agnostic conformance fixtures for the first implementation:

1. allow exact configuration + valid evidence + in-envelope request,
2. deny/hold on configuration fingerprint mismatch,
3. deny missing capability claim,
4. deny missing evidence,
5. deny expired evidence,
6. deny evidence produced against a different configuration,
7. deny operating-envelope violation,
8. allow unaffected claim when `allow_unaffected_claims=true`,
9. suspend affected claim after critical tool/MCP addition,
10. reauthorize after new evidence and updated warrant.

---

## 14. Non-Goals for v0.1

The profile does not yet standardize:

- universal capability taxonomies,
- universal benchmark scoring,
- probabilistic evidence weighting,
- automated policy generation,
- autonomous warrant issuance,
- a global evidence registry,
- cross-organization trust federation,
- semantic equivalence between model versions,
- formal safety cases, or
- sector-specific certification rules.

Those may be layered on later. v0.1 focuses on the smallest useful primitive:

> **Bind authority to a specific demonstrated capability, evidence set, governed configuration, and operating envelope — then detect when that binding no longer holds.**

---

## 15. Design Principle

OpenWarrant SHALL preserve the distinction among three questions:

> **What can the system do?**  
> **What does the evidence support?**  
> **What is the system authorized to do?**

A Capability Warrant exists to keep those answers synchronized as systems change.
