# Capability Warrant v0.1 Conformance

This directory contains language-agnostic acceptance cases for the first implementation of `openwarrant.capability/0.1`.

The source fixture is:

- `capability-warrant-v0.1-cases.json`

## Required runner behavior

A conformant runner SHOULD:

1. load the `reference_warrant` and `reference_request`,
2. apply each case's `mutations`, `request_context`, or configuration override,
3. recompute the current configuration fingerprint when a manifest is supplied,
4. evaluate the base OpenWarrant warrant plus Capability Warrant profile checks,
5. compare decision, reason codes, assurance state, claim ID, and evidence refs with `expected`, and
6. fail the test if authority is broadened because of missing or ambiguous profile data.

## Safety default

`CW-08` intentionally permits an unaffected claim only when a runtime has explicit claim-dependency analysis that proves the changed component cannot affect that claim. `CW-09` defines the v0.1 safe default: without that proof, a material fingerprint change requires review rather than silent authority inheritance.

This distinction is deliberate. It lets implementations become more selective later without making the first implementation permissive.

## First demo acceptance gate

The Studio vertical slice is ready to demo when at minimum these cases pass end-to-end:

- `CW-01-valid-exact-configuration`
- `CW-02-fingerprint-mismatch-after-mcp-addition`
- `CW-03-new-capability-has-no-claim`
- `CW-09-default-safe-behavior-without-dependency-analysis`
- `CW-10-successful-reauthorization`

That sequence proves the product thesis:

**evaluated configuration → authorized action → capability change → authority does not silently follow → re-evaluation → reauthorization.**
